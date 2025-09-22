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
            observaciones_item TEXT
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
        clientes_df = pd.read_sql("SELECT id, razon_social, boca FROM clientes", conn)
        articulos_df = pd.read_sql("SELECT id, nro_articulo, descripcion, precio_publico FROM articulos", conn)
    return clientes_df, articulos_df

def save_remito(cliente_id, fecha_entrega, fecha_retiro, observaciones_cabecera, items_df):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with engine.begin() as conn:
        result = conn.execute(text("""
            INSERT INTO remitos (cliente_id, fecha_entrega, fecha_retiro, observaciones, fecha_alta, fecha_mod)
            VALUES (:cid, :fe, :fr, :obs, :fc, :fm)
            RETURNING id
        """), {
            "cid": int(cliente_id),
            "fe": fecha_entrega,
            "fr": fecha_retiro,
            "obs": observaciones_cabecera,
            "fc": fecha_actual,
            "fm": fecha_actual
        })
        remito_id = result.scalar()

        for _, row in items_df.iterrows():
            conn.execute(text("""
                INSERT INTO remito_items (remito_id, articulo_id, entregados, observaciones_item)
                VALUES (:rid, :aid, :ent, :obs)
            """), {
                "rid": int(remito_id),
                "aid": int(row["id_articulo"]),
                "ent": int(row["Entregados"]),
                "obs": str(row["Observaciones"])  if row["Observaciones"] else None
            })

    return remito_id

# --- Nuevas funciones para el CRUD de artículos y rubros---
def get_all_rubros():
    """Obtiene todos los rubros de la base de datos."""
    with engine.begin() as conn:
        rubros_df = pd.read_sql("SELECT id, nombre_rubro FROM rubros ORDER BY nombre_rubro", conn)
        return rubros_df

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
        precio = row['precio_real']
        
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
            SELECT r.id AS remito_id, r.fecha_entrega, r.observaciones,
                   c.razon_social, c.boca, c.direccion, c.localidad, c.telefono,
                   COALESCE(c.porc_dto, 1) AS porc_dto
            FROM remitos r
            JOIN clientes c ON r.cliente_id = c.id
            WHERE r.id = :rid
        """), {"rid": remito_id}).mappings().first()

        if not cabecera:
            return None

        # --- Items ---
        items = pd.read_sql(text("""
            SELECT a.nro_articulo, a.descripcion, a.precio_real, 
                    ri.entregados, ri.devueltos, ri.observaciones_item observaciones
            FROM remito_items ri
            JOIN articulos a ON ri.articulo_id = a.id
            WHERE ri.remito_id = :rid
        """), conn, params={"rid": remito_id})

    return {
        "cabecera": dict(cabecera),
        "items": items
    }

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
    
def update_remito_data(remito_id, fecha_retiro, observaciones_cabecera, items_df):
    """
    Actualiza la cabecera y los items de un remito existente.
    """
    with engine.begin() as conn:
        # Actualizar la cabecera del remito
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

        # Actualizar los ítems del remito
        for _, row in items_df.iterrows():
            # Obtener el ID del artículo
            articulo_result = conn.execute(text("""
                SELECT id FROM articulos WHERE nro_articulo = :nro
            """), {"nro": row["nro_articulo"]}).scalar()
            
            if articulo_result:
                # Preparar valores, manejando posibles valores NaN o None
                devueltos = int(row.get("devueltos", 0)) if pd.notna(row.get("devueltos")) else 0
                observaciones = str(row.get("observaciones", "")) if pd.notna(row.get("observaciones")) else ""
                
                conn.execute(text("""
                    UPDATE remito_items
                    SET observaciones_item = :obs, 
                        devueltos = :devueltos
                    WHERE remito_id = :rid
                    AND articulo_id = :aid
                """), {
                    "obs": observaciones if observaciones.strip() else None,
                    "devueltos": devueltos,
                    "rid": remito_id,
                    "aid": articulo_result
                })
            else:
                # Log o manejar el caso donde no se encuentra el artículo
                print(f"Warning: Artículo {row['nro_articulo']} no encontrado en la base de datos")