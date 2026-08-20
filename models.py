# -*- coding: utf-8 -*-
import os
import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
from datetime import datetime

# Obtener la cadena de conexión desde secrets
# Local: en .streamlit/secrets.toml
# Producción: desde variables de configuración en la web
DB_URL = st.secrets["DB_URL"]

# Crear motor SQLAlchemy
engine = create_engine(DB_URL, pool_pre_ping=True)

def init_db():
    with engine.begin() as conn:
        # Crear tablas si no existen
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clientes (
            id SERIAL PRIMARY KEY,
            razon_social TEXT NOT NULL,
            boca INTEGER,
            direccion TEXT,
            localidad TEXT,
            telefono TEXT,
            email TEXT,
            porc_dto REAL,
            vendedor_id INTEGER, 
            fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_mod TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS rubros (
            id SERIAL PRIMARY KEY,
            nombre_rubro TEXT NOT NULL UNIQUE,
            fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_mod TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS articulos (
            id SERIAL PRIMARY KEY,
            nro_articulo TEXT UNIQUE NOT NULL,
            descripcion TEXT NOT NULL,
            costo REAL,
            precio_publico REAL,
            precio_real REAL NOT NULL,
            rubro_id INTEGER,
            fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_mod TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rubro_id) REFERENCES rubros(id)
        );
        """))
        
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS remitos (
            id SERIAL PRIMARY KEY,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            porc_dto REAL,
            fecha_entrega DATE,
            fecha_retiro DATE,
            observaciones TEXT,
            fecha_alta TIMESTAMP NOT NULL,
            fecha_mod TIMESTAMP NOT NULL
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS remito_items (
            id SERIAL PRIMARY KEY,
            remito_id INTEGER NOT NULL REFERENCES remitos(id),
            articulo_id INTEGER NOT NULL REFERENCES articulos(id),
            entregados INTEGER NOT NULL,
            observaciones_item TEXT,
            precio_real_item REAL NOT NULL -- Columna para guardar el precio real en el momento de la venta/consignación
        );
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS vendedores (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            direccion TEXT,
            localidad TEXT,
            telefono TEXT,
            email TEXT,
            comision REAL,
            fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_mod TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """))


        # Insertar datos demo si no existen
        clientes = conn.execute(text("SELECT COUNT(*) FROM clientes")).scalar()
        if clientes == 0:
            conn.execute(text("INSERT INTO clientes (razon_social) VALUES (:n)"),
                         [{"n": "Cliente A"}, {"n": "Cliente B"}, {"n": "Cliente C"}])

        rubros = conn.execute(text("SELECT COUNT(*) FROM rubros")).scalar()
        if rubros == 0:
            demo_rubros = [
                {"n": "GORRAS"},
                {"n": "ANTEOJOS"},
                {"n": "ACCESORIOS"}
            ]
            conn.execute(text("INSERT INTO rubros (nombre_rubro) VALUES (:n)"), demo_rubros)
            
        articulos = conn.execute(text("SELECT COUNT(*) FROM articulos")).scalar()
        if articulos == 0:
            gorras_id = conn.execute(text("SELECT id FROM rubros WHERE nombre_rubro = 'GORRAS'")).scalar()
            anteojos_id = conn.execute(text("SELECT id FROM rubros WHERE nombre_rubro = 'ANTEOJOS'")).scalar()

            demo_articulos = [
                ("ART-001", "Camiseta básica", 15.50, None),
                ("ART-002", "Pantalón deportivo", 30.00, None),
                ("ART-003", "Zapatillas urbanas", 55.00, None),
                ("ART-004", "Gorra con logo", 10.00, gorras_id),
                ("ART-005", "Anteojos de sol", 25.00, anteojos_id),
            ]
            try:
                conn.execute(text("""
                    INSERT INTO articulos (nro_articulo, descripcion, precio_real, rubro_id)
                    VALUES (:nro, :desc, :pr, :rubro_id)
                """), [
                    {"nro": a[0], "desc": a[1], "pr": a[2], "rubro_id": a[3]} for a in demo_articulos
                ])
            except Exception as e:
                pass
            
def get_clients_and_articles():
    with engine.begin() as conn:
        clientes_df = pd.read_sql("SELECT id, razon_social, boca, porc_dto FROM clientes", conn)
        # Se agrega la columna 'precio_real' a la consulta.
        articulos_df = pd.read_sql("SELECT id, nro_articulo, descripcion, precio_publico, precio_real, COALESCE(costo, 0) AS costo FROM articulos", conn)
    return clientes_df, articulos_df

def save_remito(cliente_id, fecha_entrega, fecha_retiro, observaciones_cabecera, porc_dto, items_df):
    fecha_actual = datetime.now()
    
    # Asegurar tipos nativos de Python para evitar errores de adaptación de psycopg2 con tipos de pandas/numpy
    cliente_id = int(cliente_id)
    porc_dto_val = float(porc_dto) if pd.notna(porc_dto) else None
    
    with engine.begin() as conn:
        # Buscar el remito existente por cliente y fechas
        query = text("""
            SELECT id FROM remitos WHERE cliente_id = :cliente_id AND fecha_entrega = :fecha_entrega AND fecha_retiro IS NULL
        """)
        remito_id_result = conn.execute(query, {
            "cliente_id": cliente_id,
            "fecha_entrega": fecha_entrega,
        }).scalar()

        if remito_id_result:
            remito_id = int(remito_id_result)
            conn.execute(text("""
                UPDATE remitos
                SET fecha_mod = :now, porc_dto = :porc_dto, observaciones = :obs
                WHERE id = :rid
            """), {
                "now": fecha_actual,
                "porc_dto": porc_dto_val,
                "obs": observaciones_cabecera,
                "rid": remito_id
            })
            
            # Borrar ítems antiguos para evitar duplicados
            conn.execute(text("""
                DELETE FROM remito_items WHERE remito_id = :rid
            """), {"rid": remito_id})

            # Variable para rastrear si se modificó algún precio
            precios_modificados = False

            # Se itera sobre el DataFrame para guardar cada item y actualizar precios.
            for _, row in items_df.iterrows():
                # Convertir a int/float los tipos de datos
                articulo_id = int(row['id_articulo'])
                precio_real_val = float(row['Precio Real'])
                entregados_val = int(row['Entregados'])
                
                # Obtener el precio_real actual de la base de datos
                current_price_result = conn.execute(text("SELECT precio_real FROM articulos WHERE id = :aid"), 
                                                     {"aid": articulo_id}).scalar()
                
                # Se compara el precio del DataFrame editado con el de la base de datos.
                if current_price_result != precio_real_val:
                    # Si el precio es diferente, se actualiza en la tabla de articulos.
                    conn.execute(text("""
                        UPDATE articulos
                        SET precio_real = :new_price, fecha_mod = :now
                        WHERE id = :aid
                    """), {
                        "new_price": precio_real_val,
                        "now": fecha_actual,
                        "aid": articulo_id
                    })
                    precios_modificados = True # Se marca que hubo una modificación.

                # Insertar el nuevo item, incluyendo el precio real de ese item
                conn.execute(text("""
                    INSERT INTO remito_items (remito_id, articulo_id, entregados, observaciones_item, precio_real_item)
                    VALUES (:remito_id, :articulo_id, :entregados, :observaciones, :precio_real)
                """), {
                    "remito_id": remito_id,
                    "articulo_id": articulo_id,
                    "entregados": entregados_val,
                    "observaciones": row["Observaciones"] if pd.notna(row["Observaciones"]) else None,
                    "precio_real": precio_real_val
                })
            
            return remito_id, precios_modificados

        else:
            # Lógica para crear un nuevo remito
            result = conn.execute(text("""
                INSERT INTO remitos (cliente_id, porc_dto, fecha_entrega, observaciones, fecha_alta, fecha_mod)
                VALUES (:cid, :porc_dto, :fecha_entrega, :obs, :now, :now)
                RETURNING id
            """), {
                "cid": cliente_id,
                "porc_dto": porc_dto_val,
                "fecha_entrega": fecha_entrega,
                "obs": observaciones_cabecera,
                "now": fecha_actual
            })
            remito_id = int(result.scalar())

            precios_modificados = False
            for _, row in items_df.iterrows():
                articulo_id = int(row['id_articulo'])
                precio_real_val = float(row['Precio Real'])
                entregados_val = int(row['Entregados'])
                
                current_price_result = conn.execute(text("SELECT precio_real FROM articulos WHERE id = :aid"), 
                                                     {"aid": articulo_id}).scalar()
                
                if current_price_result != precio_real_val:
                    conn.execute(text("""
                        UPDATE articulos
                        SET precio_real = :new_price, fecha_mod = :now
                        WHERE id = :aid
                    """), {
                        "new_price": precio_real_val,
                        "now": fecha_actual,
                        "aid": articulo_id
                    })
                    precios_modificados = True
                
                conn.execute(text("""
                    INSERT INTO remito_items (remito_id, articulo_id, entregados, observaciones_item, precio_real_item)
                    VALUES (:remito_id, :articulo_id, :entregados, :observaciones, :precio_real)
                """), {
                    "remito_id": remito_id,
                    "articulo_id": articulo_id,
                    "entregados": entregados_val,
                    "observaciones": row["Observaciones"] if pd.notna(row["Observaciones"]) else None,
                    "precio_real": precio_real_val
                })
            
            return remito_id, precios_modificados

def get_all_rubros():
    """Obtiene todos los rubros de la base de datos."""
    with engine.begin() as conn:
        rubros_df = pd.read_sql(text("SELECT id, nombre_rubro, fecha_alta, fecha_mod FROM rubros ORDER BY nombre_rubro"), conn)
        return rubros_df

def save_new_rubro(nombre_rubro):
    """Inserta un nuevo rubro en la base de datos."""
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO rubros (nombre_rubro, fecha_alta, fecha_mod)
            VALUES (:nombre, :fa, :fm)
        """), {
            "nombre": nombre_rubro.strip(),
            "fa": fecha_actual,
            "fm": fecha_actual
        })

def update_existing_rubro(rubro_id, nuevo_nombre):
    """Actualiza el nombre de un rubro existente."""
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE rubros
            SET nombre_rubro = :nombre,
                fecha_mod = :fm
            WHERE id = :id
        """), {
            "nombre": nuevo_nombre.strip(),
            "fm": fecha_actual,
            "id": int(rubro_id)
        })

def delete_existing_rubro(rubro_id):
    """Elimina un rubro de la base de datos."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rubros WHERE id = :id"), {"id": int(rubro_id)})

def check_rubro_in_use(rubro_id):
    """Verifica si el rubro está asociado a algún artículo."""
    with engine.begin() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM articulos WHERE rubro_id = :id"),
            {"id": int(rubro_id)}
        ).scalar()
        return count > 0

def check_rubro_exists(nombre_rubro, ignore_id=None):
    """Verifica si un nombre de rubro ya existe (no sensible a mayúsculas/minúsculas)."""
    with engine.begin() as conn:
        if ignore_id:
            count = conn.execute(
                text("SELECT COUNT(*) FROM rubros WHERE UPPER(TRIM(nombre_rubro)) = UPPER(TRIM(:nombre)) AND id != :ignore_id"),
                {"nombre": nombre_rubro, "ignore_id": int(ignore_id)}
            ).scalar()
        else:
            count = conn.execute(
                text("SELECT COUNT(*) FROM rubros WHERE UPPER(TRIM(nombre_rubro)) = UPPER(TRIM(:nombre))"),
                {"nombre": nombre_rubro}
            ).scalar()
        return count > 0

def get_all_articulos():
    """Obtiene todos los artículos de la base de datos, incluyendo el nombre del rubro."""
    with engine.begin() as conn:
        query = """
        SELECT a.id, a.nro_articulo, a.descripcion, a.costo, a.precio_publico, a.precio_real, 
        a.fecha_mod, a.rubro_id, r.nombre_rubro 
        FROM articulos a
        LEFT JOIN rubros r ON a.rubro_id = r.id
        ORDER BY a.nro_articulo
        """
        return pd.read_sql(text(query), conn)

def save_new_articulo(nro_articulo, descripcion, costo, precio_publico, precio_real, id_rubro):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO articulos (nro_articulo, descripcion, costo, precio_publico, precio_real, rubro_id, fecha_alta, fecha_mod)
            VALUES (:nro, :desc, :costo, :pp, :pr, :rubro_id, :fa, :fm)
        """), {
            "nro": nro_articulo.strip(),
            "desc": descripcion,
            "costo": costo if costo is not None else None,
            "pp": precio_publico if precio_publico is not None else None,
            "pr": precio_real,
            "rubro_id": id_rubro,
            "fa": fecha_actual,
            "fm": fecha_actual
        })

def update_existing_articulo(articulo_id, nro_articulo, descripcion, costo, precio_publico, precio_real, id_rubro):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE articulos
            SET nro_articulo = :nro,
                descripcion = :desc,
                costo = :costo,
                precio_publico = :pp,
                precio_real = :pr,
                rubro_id = :rubro_id,
                fecha_mod = :fm
            WHERE id = :id
        """), {
            "id": articulo_id,
            "nro": nro_articulo.upper(),
            "desc": descripcion.strip().capitalize(),
            "costo": costo if costo is not None else None,
            "pp": precio_publico if precio_publico is not None else None,
            "pr": precio_real,
            "rubro_id": id_rubro,
            "fm": fecha_actual
        })

def delete_existing_articulo(articulo_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM articulos WHERE id = :id"), {"id": articulo_id})

def check_article_in_remitos(articulo_id):
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM remito_items WHERE articulo_id = :aid"), {"aid": articulo_id}).scalar()
        return count > 0
    
# --- Nuevas funciones para la carga desde Excel ---
def update_or_insert_articulos_from_excel(df):
    """
    Procesa un DataFrame para actualizar o insertar artículos en la base de datos,
    evitando registros duplicados por nro_articulo en el archivo de origen.
    Retorna un diccionario con el número de artículos insertados y actualizados.
    """
    
    # Elimina duplicados basándose en la columna 'nro_articulo'.
    # 'keep="first"' asegura que el primer registro que aparece en el archivo
    # es el que se mantiene.
    df = df.drop_duplicates(subset=['nro_articulo'], keep='first')
    
    inserted_count = 0
    updated_count = 0
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with engine.begin() as conn:
        existing_articles_df = pd.read_sql("SELECT nro_articulo FROM articulos", conn)
        existing_nros = set(existing_articles_df['nro_articulo'].str.upper())

    articles_to_update = []
    articles_to_insert = []

    for index, row in df.iterrows():
        nro = str(row['nro_articulo']).strip().upper()
        desc = row['descripcion']
        precio = float(row['precio_real']) if pd.notna(row['precio_real']) else 0.0
        
        if nro in existing_nros:
            articles_to_update.append({
                "nro": nro,
                "desc": desc,
                "pr": precio,
                "fm": fecha_actual
            })
        else:
            articles_to_insert.append({
                "nro": nro,
                "desc": desc,
                "pr": precio,
                "fa": fecha_actual,
                "fm": fecha_actual
            })

    with engine.begin() as conn:
        # Bulk Update
        if articles_to_update:
            conn.execute(text("""
                UPDATE articulos
                SET descripcion = :desc,
                    precio_real = :pr,
                    fecha_mod = :fm
                WHERE nro_articulo = :nro
            """), articles_to_update)
            updated_count = len(articles_to_update)

        # Bulk Insert
        if articles_to_insert:
            conn.execute(text("""
                INSERT INTO articulos (nro_articulo, descripcion, precio_real, fecha_alta, fecha_mod, costo, precio_publico)
                VALUES (:nro, :desc, :pr, :fa, :fm, 0.00, 0.00)
            """), articles_to_insert)
            inserted_count = len(articles_to_insert)

    return {"insertados": inserted_count, "actualizados": updated_count}

def get_remito_completo(remito_id: int):
    """Devuelve un diccionario con datos de cabecera e items de un remito dado."""
    with engine.begin() as conn:
        # --- Cabecera ---
        cabecera = conn.execute(text("""
            SELECT r.id AS remito_id, r.cliente_id, r.fecha_entrega, r.fecha_retiro, r.observaciones,
                   c.razon_social, c.boca, c.direccion, c.localidad, c.telefono,
                   COALESCE(r.porc_dto, c.porc_dto, 0) AS porc_dto
            FROM remitos r
            JOIN clientes c ON r.cliente_id = c.id
            WHERE r.id = :rid
        """), {"rid": remito_id}).mappings().first()

        if not cabecera:
            return None

        # --- Items ---
        items = pd.read_sql(text("""
            SELECT a.id AS id_articulo, a.nro_articulo, a.descripcion,
                   COALESCE(a.precio_publico, 0) AS precio_publico,
                   COALESCE(ri.precio_real_item, a.precio_real, 0) AS precio_real, 
                   COALESCE(a.costo, 0) AS costo,
                   ri.entregados, ri.devueltos, COALESCE(ri.observaciones_item, '') AS observaciones
            FROM remito_items ri
            JOIN articulos a ON ri.articulo_id = a.id
            WHERE ri.remito_id = :rid
            ORDER BY ri.id ASC
        """), conn, params={"rid": remito_id})

    return {
        "cabecera": dict(cabecera),
        "items": items
    }

def update_remito_completo(remito_id, fecha_retiro, observaciones_cabecera, items_df):
    """
    Actualiza completamente la cabecera (fecha_retiro, observaciones) y los items de un remito existente.
    """
    remito_id = int(remito_id)
    fecha_actual = datetime.now()
    precios_modificados = False

    with engine.begin() as conn:
        # Actualizar la cabecera del remito
        conn.execute(text("""
            UPDATE remitos
            SET fecha_retiro = :fr, observaciones = :obs, fecha_mod = :now
            WHERE id = :rid
        """), {
            "fr": fecha_retiro,
            "obs": observaciones_cabecera,
            "now": fecha_actual,
            "rid": remito_id
        })

        # Eliminar items antiguos del remito
        conn.execute(text("""
            DELETE FROM remito_items WHERE remito_id = :rid
        """), {"rid": remito_id})

        # Reinsertar los nuevos items y actualizar precios maestros si sufrieron modificaciones
        for _, row in items_df.iterrows():
            articulo_id = int(row['id_articulo'])
            precio_real_val = float(row['Precio Real'])
            entregados_val = int(row['Entregados'])
            observaciones_val = str(row['Observaciones']).strip() if pd.notna(row['Observaciones']) and str(row['Observaciones']).strip() and str(row['Observaciones']).strip().lower() != 'none' else None

            # Verificar si el precio en el maestro cambió
            current_price_result = conn.execute(text("SELECT precio_real FROM articulos WHERE id = :aid"), 
                                                 {"aid": articulo_id}).scalar()
            
            if current_price_result is not None and float(current_price_result) != precio_real_val:
                conn.execute(text("""
                    UPDATE articulos
                    SET precio_real = :new_price, fecha_mod = :now
                    WHERE id = :aid
                """), {
                    "new_price": precio_real_val,
                    "now": fecha_actual,
                    "aid": articulo_id
                })
                precios_modificados = True

            # Insertar item
            conn.execute(text("""
                INSERT INTO remito_items (remito_id, articulo_id, entregados, observaciones_item, precio_real_item)
                VALUES (:rid, :aid, :entregados, :obs, :precio_real)
            """), {
                "rid": remito_id,
                "aid": articulo_id,
                "entregados": entregados_val,
                "obs": observaciones_val,
                "precio_real": precio_real_val
            })

    return remito_id, precios_modificados

def get_all_clientes():
    """Devuelve un DataFrame de Pandas con todos los clientes, incluyendo el nombre del vendedor."""
    query = text("""
        SELECT c.*, v.nombre AS nombre_vendedor
        FROM clientes c
        LEFT JOIN vendedores v ON c.vendedor_id = v.id
        ORDER BY c.boca ASC;
    """)
    df = pd.read_sql(query, engine)
    return df

def get_all_vendedores():
    """Devuelve un DataFrame de Pandas con todos los vendedores."""
    with engine.begin() as conn:
        query = text("SELECT id, nombre FROM vendedores ORDER BY nombre ASC;")
        df = pd.read_sql(query, conn)
    return df

def save_new_cliente(razon_social, boca, direccion, localidad, telefono, email, porc_dto, vendedor_id):
    """Guarda un nuevo cliente en la base de datos."""
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO clientes (razon_social, boca, direccion, localidad, telefono, email, porc_dto, vendedor_id)
            VALUES (:rs, :b, :d, :l, :t, :e, :pd, :vid);
        """), {
            "rs": razon_social,
            "b": boca,
            "d": direccion,
            "l": localidad,
            "t": telefono,
            "e": email,
            "pd": porc_dto,
            "vid": vendedor_id
        })

def update_existing_cliente(cliente_id, razon_social, boca, direccion, localidad, telefono, email, porc_dto, vendedor_id):
    """Actualiza un cliente existente en la base de datos."""
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE clientes
            SET razon_social = :rs,
                boca = :b,
                direccion = :d,
                localidad = :l,
                telefono = :t,
                email = :e,
                porc_dto = :pd,
                vendedor_id = :vid,
                fecha_mod = CURRENT_TIMESTAMP
            WHERE id = :id;
        """), {
            "id": cliente_id,
            "rs": razon_social,
            "b": boca,
            "d": direccion,
            "l": localidad,
            "t": telefono,
            "e": email,
            "pd": porc_dto,
            "vid": vendedor_id
        })

def delete_existing_cliente(cliente_id):
    """Elimina un cliente existente de la base de datos."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM clientes WHERE id = :id;"), {"id": cliente_id})

def check_client_in_remitos(cliente_id):
    """Verifica si un cliente está asociado a algún remito."""
    with engine.begin() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM remitos WHERE cliente_id = :id;"), {"id": cliente_id}).scalar()
        return result > 0
    
def update_remito_data(remito_id, fecha_retiro, observaciones_cabecera, items_df, fecha_entrega=None):
    """
    Actualiza la cabecera (incluyendo opcionalmente fecha_entrega) y los items de un remito existente.
    """
    remito_id = int(remito_id)
    with engine.begin() as conn:
        # Actualizar la cabecera del remito
        if fecha_entrega is not None:
            conn.execute(text("""
                UPDATE remitos
                SET fecha_entrega = :fe, fecha_retiro = :fr, observaciones = :obs, fecha_mod = CURRENT_TIMESTAMP
                WHERE id = :rid
            """), {
                "fe": fecha_entrega,
                "fr": fecha_retiro,
                "obs": observaciones_cabecera,
                "rid": remito_id
            })
        else:
            conn.execute(text("""
                UPDATE remitos
                SET fecha_retiro = :fr, observaciones = :obs, fecha_mod = CURRENT_TIMESTAMP
                WHERE id = :rid
            """), {
                "fr": fecha_retiro,
                "obs": observaciones_cabecera,
                "rid": remito_id
            })

        # Verificar si la tabla remito_items tiene la columna 'devueltos'
        # Si no existe, agregarla
        # try:
        #    conn.execute(text("ALTER TABLE remito_items ADD COLUMN IF NOT EXISTS devueltos INTEGER DEFAULT 0"))
        # except Exception:
        #    pass  # La columna ya existe o hay otro error que podemos ignorar

        # Eliminar items antiguos de este remito para sincronizar altas y bajas
        conn.execute(text("""
            DELETE FROM remito_items WHERE remito_id = :rid
        """), {"rid": remito_id})

        # Reinsertar los ítems actualizados del remito
        for _, row in items_df.iterrows():
            articulo_id = None
            if "id_articulo" in row and pd.notna(row["id_articulo"]):
                articulo_id = int(row["id_articulo"])
            else:
                articulo_result = conn.execute(text("""
                    SELECT id FROM articulos WHERE nro_articulo = :nro
                """), {"nro": str(row["nro_articulo"])}).scalar()
                if articulo_result:
                    articulo_id = int(articulo_result)
            
            if articulo_id:
                devueltos = int(row.get("devueltos", 0)) if pd.notna(row.get("devueltos")) else 0
                entregados = int(row.get("entregados", 0)) if pd.notna(row.get("entregados")) else 0
                precio_real = float(row.get("precio_real", 0)) if pd.notna(row.get("precio_real")) else 0.0
                obs_raw = row.get("observaciones", "")
                observaciones = str(obs_raw).strip() if (pd.notna(obs_raw) and str(obs_raw).strip() and str(obs_raw).strip().lower() != "none") else None
                
                conn.execute(text("""
                    INSERT INTO remito_items (remito_id, articulo_id, entregados, devueltos, observaciones_item, precio_real_item)
                    VALUES (:rid, :aid, :entregados, :devueltos, :obs, :precio_real)
                """), {
                    "rid": remito_id,
                    "aid": articulo_id,
                    "entregados": entregados,
                    "devueltos": devueltos,
                    "obs": observaciones,
                    "precio_real": precio_real
                })


def delete_remito(remito_id):
    """
    Elimina completamente un remito y todos sus items asociados.
    Retorna True si se eliminó correctamente, False si no se encontró el remito.
    """
    with engine.begin() as conn:
        # Verificar si el remito existe
        exists = conn.execute(text("""
            SELECT COUNT(*) FROM remitos WHERE id = :rid
        """), {"rid": remito_id}).scalar()
        
        if exists == 0:
            return False
        
        # Eliminar primero los items (por la foreign key)
        conn.execute(text("""
            DELETE FROM remito_items WHERE remito_id = :rid
        """), {"rid": remito_id})
        
        # Luego eliminar el remito
        conn.execute(text("""
            DELETE FROM remitos WHERE id = :rid
        """), {"rid": remito_id})
        
        return True