#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de backup simple con persistencia de resultado y diálogo nativo de guardado
"""

import streamlit as st
import pandas as pd
import os
import zipfile
from datetime import datetime
import io
import sqlite3
import config

def get_desktop_path() -> str:
    """Obtiene la ruta del Escritorio del usuario."""
    return os.path.join(os.path.expanduser("~"), "Desktop")

def is_local_app() -> bool:
    """Verifica si la aplicación corre localmente."""
    return not os.environ.get("STREAMLIT_SERVER_TARGET") and (
        os.path.exists("C:\\") or os.name == 'nt' or 'localhost' in os.environ.get("SERVER_NAME", "")
    )

def select_backup_folder(default_dir: str = None) -> str:
    """Abre un diálogo nativo (Tkinter) para seleccionar la carpeta donde guardar el backup."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        
        initial_dir = default_dir or os.path.join(get_desktop_path(), "BACKUPS CAPELLO")
        if not os.path.exists(initial_dir):
            initial_dir = get_desktop_path()

        folder = filedialog.askdirectory(
            title="Seleccione la carpeta donde guardar el Backup (.zip)",
            initialdir=initial_dir
        )
        root.destroy()
        return folder if folder else None
    except Exception as e:
        st.error(f"Error abriendo el explorador de archivos: {e}")
        return None

def simple_backup_page():
    """Página simple de backup sin complicaciones"""
    
    st.title(config.TITULO_APP)
    st.header("💾 Backup de Base de Datos")
    
    # Inicialización de estado persistente
    if "backup_result" not in st.session_state:
        st.session_state.backup_result = None
    if "backup_saved_msg" not in st.session_state:
        st.session_state.backup_saved_msg = None

    # Verificación inicial simple
    try:
        db_url = st.secrets["DB_URL"]
        st.success("✅ Configuración de base de datos encontrada")
    except:
        st.error("❌ No se encontró DB_URL en secrets.toml")
        st.code("""
# Agrega esto a .streamlit/secrets.toml
DB_URL = "postgresql://usuario:contraseña@servidor:puerto/basededatos"
        """)
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📊 Estado de la Base de Datos")
        verificar_estado = st.button("🔍 Verificar Estado", use_container_width=True)
    
    with col2:
        st.markdown("### 🚀 Crear Backup")
        ejecutar_backup = st.button("💾 Ejecutar Backup", type="primary", use_container_width=True)
    
    # Procesar acciones
    if verificar_estado:
        st.session_state.backup_saved_msg = None
        st.markdown("---")
        check_database_status(db_url)
    
    if ejecutar_backup:
        st.session_state.backup_result = None
        st.session_state.backup_saved_msg = None
        st.markdown("---")
        create_backup(db_url)

    # Si hay un resultado de backup en sesión, mostrar la sección de guardado/descarga de forma persistente
    if st.session_state.backup_result and not ejecutar_backup:
        st.markdown("---")
        b_res = st.session_state.backup_result
        st.info(f"📦 Tamaño del backup: {b_res['size_mb']:.2f} MB")
        
        if is_local_app():
            col_save1, col_save2 = st.columns(2, gap="small")
            with col_save1:
                if st.button("📁 Seleccionar Carpeta y Guardar Backup", type="primary", use_container_width=True, key="btn_save_folder"):
                    chosen_folder = select_backup_folder()
                    if chosen_folder:
                        destination_path = os.path.join(chosen_folder, b_res['filename'])
                        try:
                            with open(destination_path, "wb") as f_out:
                                f_out.write(b_res['bytes'])
                            st.session_state.backup_saved_msg = f"🎉 ¡Backup guardado exitosamente en: **{destination_path}**!"
                            st.rerun()
                        except Exception as err_save:
                            st.error(f"❌ Error al guardar el archivo: {err_save}")
                    else:
                        st.warning("⚠️ No se seleccionó ninguna carpeta.")
            with col_save2:
                st.download_button(
                    label="📥 Descargar por Navegador (.zip)",
                    data=b_res['bytes'],
                    file_name=b_res['filename'],
                    mime="application/zip",
                    use_container_width=True,
                    key="btn_download_browser"
                )
        else:
            st.download_button(
                label="📥 DESCARGAR BACKUP COMPLETO (.zip)",
                data=b_res['bytes'],
                file_name=b_res['filename'],
                mime="application/zip",
                use_container_width=True,
                key="btn_download_full"
            )

        if st.session_state.get('backup_saved_msg'):
            st.success(st.session_state.backup_saved_msg)

        # Info detallada
        with st.expander("📋 Detalles del Backup", expanded=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown("""
                **🎯 Archivo Principal:**
                - `backup_database.db` - SQLite completo
                
                **📄 Archivos PostgreSQL:**
                - `01_structure.sql`
                - `02_data.sql`
                - `restore_postgres.py`
                """)
            
            with col_b:
                st.markdown("""
                **📊 Estadísticas:**
                """)
                st.metric("Registros totales", f"{b_res['total_rows']:,}")
                st.metric("Tablas", b_res['total_tables'])
        
        st.markdown("""
        ### 🚀 Ahora...:
        
        1. **Guarde o Descargue** el archivo ZIP utilizando los botones superiores.
        
        💡 **Tip:** El archivo README.txt dentro del ZIP tiene instrucciones detalladas para recuperar los datos.
        """)

def check_database_status(db_url):
    """Verifica el estado de las tablas"""
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine(db_url, pool_pre_ping=True)
        
        with st.spinner("Consultando base de datos..."):
            with engine.begin() as conn:
                tables = ['vendedores', 'clientes', 'rubros', 'articulos', 'remitos', 'remito_items']
                stats = []
                
                for table in tables:
                    try:
                        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                        stats.append({
                            "Tabla": table.capitalize(),
                            "Registros": f"{count:,}",
                            "Estado": "✅ OK" if count >= 0 else "⚠️ Vacía"
                        })
                    except Exception as e:
                        stats.append({
                            "Tabla": table.capitalize(),
                            "Registros": "Error",
                            "Estado": f"❌ {str(e)[:30]}..."
                        })
                
                df = pd.DataFrame(stats)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Resumen
                total_tables = len(stats)
                ok_tables = len([s for s in stats if s['Estado'] == '✅ OK'])
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("📋 Total Tablas", total_tables)
                with col_b:
                    st.metric("✅ Tablas OK", f"{ok_tables}/{total_tables}")
    
    except Exception as e:
        st.error(f"❌ Error consultando base de datos: {str(e)}")

def create_sqlite_database(sqlite_file, tables_data):
    """Crea la base de datos SQLite con estructura y datos"""
    
    # Crear conexión SQLite
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()
    
    try:
        # 1. CREAR ESTRUCTURA DE TABLAS
        st.info("📝 Creando estructura de tablas SQLite...")
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendedores (
            id INTEGER PRIMARY KEY,
            nombre TEXT NOT NULL,
            direccion TEXT,
            localidad TEXT,
            telefono TEXT,
            email TEXT,
            comision REAL,
            fecha_alta TEXT,
            fecha_mod TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY,
            razon_social TEXT NOT NULL,
            boca INTEGER,
            direccion TEXT,
            localidad TEXT,
            telefono TEXT,
            email TEXT,
            porc_dto REAL,
            vendedor_id INTEGER,
            fecha_alta TEXT,
            fecha_mod TEXT,
            FOREIGN KEY (vendedor_id) REFERENCES vendedores(id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rubros (
            id INTEGER PRIMARY KEY,
            nombre_rubro TEXT NOT NULL UNIQUE,
            fecha_alta TEXT,
            fecha_mod TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS articulos (
            id INTEGER PRIMARY KEY,
            nro_articulo TEXT UNIQUE NOT NULL,
            descripcion TEXT NOT NULL,
            costo REAL,
            precio_publico REAL,
            precio_real REAL NOT NULL,
            rubro_id INTEGER,
            fecha_alta TEXT,
            fecha_mod TEXT,
            FOREIGN KEY (rubro_id) REFERENCES rubros(id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS remitos (
            id INTEGER PRIMARY KEY,
            cliente_id INTEGER NOT NULL,
            porc_dto REAL,
            fecha_entrega TEXT,
            fecha_retiro TEXT,
            observaciones TEXT,
            fecha_alta TEXT NOT NULL,
            fecha_mod TEXT NOT NULL,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS remito_items (
            id INTEGER PRIMARY KEY,
            remito_id INTEGER NOT NULL,
            articulo_id INTEGER NOT NULL,
            entregados INTEGER NOT NULL,
            devueltos INTEGER DEFAULT 0,
            observaciones_item TEXT,
            precio_real_item REAL NULL,
            FOREIGN KEY (remito_id) REFERENCES remitos(id),
            FOREIGN KEY (articulo_id) REFERENCES articulos(id)
        )
        """)
        
        conn.commit()
        
        # 2. INSERTAR DATOS
        st.info("💾 Insertando datos en SQLite...")
        
        tables_order = ['vendedores', 'clientes', 'rubros', 'articulos', 'remitos', 'remito_items']
        total_inserted = 0
        
        for table in tables_order:
            df = tables_data.get(table, pd.DataFrame())
            
            if not df.empty:
                # Convertir datetime a string
                for col in df.columns:
                    if pd.api.types.is_datetime64_any_dtype(df[col]):
                        df[col] = df[col].astype(str)
                
                # Insertar cada fila
                columns = list(df.columns)
                placeholders = ','.join(['?' for _ in columns])
                insert_sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
                
                for _, row in df.iterrows():
                    values = tuple(None if pd.isna(val) else val for val in row)
                    cursor.execute(insert_sql, values)
                    total_inserted += 1
                
                conn.commit()
                st.success(f"✅ Tabla {table}: {len(df)} registros insertados")
        
        st.success(f"🎉 SQLite completado: {total_inserted} registros totales")
        
    except Exception as e:
        st.error(f"❌ Error creando SQLite: {str(e)}")
        raise
    finally:
        conn.close()

def create_backup(db_url):
    """Crea el backup de forma simple"""
    try:
        from sqlalchemy import create_engine, text
        import tempfile
        import shutil
        
        progress = st.progress(0)
        status = st.empty()
        
        status.text("🔄 Conectando a PostgreSQL...")
        progress.progress(10)
        
        engine = create_engine(db_url, pool_pre_ping=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Crear directorio temporal
        temp_dir = tempfile.mkdtemp()
        backup_name = f"capello_backup_{timestamp}"
        backup_dir = os.path.join(temp_dir, backup_name)
        os.makedirs(backup_dir)
        
        # Archivos que vamos a crear
        structure_file = os.path.join(backup_dir, "01_structure.sql")
        data_file = os.path.join(backup_dir, "02_data.sql")
        sqlite_file = os.path.join(backup_dir, "backup_database.db")
        
        status.text("📊 Extrayendo datos de PostgreSQL...")
        progress.progress(30)
        
        with engine.begin() as conn:
            # PASO 1: Obtener todos los datos de PostgreSQL
            tables = ['vendedores', 'clientes', 'rubros', 'articulos', 'remitos', 'remito_items']
            tables_data = {}
            
            for table in tables:
                try:
                    df = pd.read_sql(f"SELECT * FROM {table}", conn)
                    tables_data[table] = df
                except Exception as e:
                    st.warning(f"⚠️ Error leyendo {table}: {str(e)}")
                    tables_data[table] = pd.DataFrame()
            
            progress.progress(50)
            
            # PASO 2: Crear archivos SQL de PostgreSQL
            status.text("📝 Generando archivos SQL PostgreSQL...")
            
            with open(structure_file, 'w', encoding='utf-8') as f:
                f.write(f"-- Backup de estructura PostgreSQL - {datetime.now()}\n\n")
                f.write("""
-- Tabla vendedores
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

-- Tabla clientes
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
    fecha_mod TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendedor_id) REFERENCES vendedores(id)
);

-- Tabla rubros
CREATE TABLE IF NOT EXISTS rubros (
    id SERIAL PRIMARY KEY,
    nombre_rubro TEXT NOT NULL UNIQUE,
    fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_mod TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla articulos
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

-- Tabla remitos
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

-- Tabla remito_items
CREATE TABLE IF NOT EXISTS remito_items (
    id SERIAL PRIMARY KEY,
    remito_id INTEGER NOT NULL REFERENCES remitos(id),
    articulo_id INTEGER NOT NULL REFERENCES articulos(id),
    entregados INTEGER NOT NULL,
    devueltos INTEGER DEFAULT 0,
    observaciones_item TEXT,
    precio_real_item REAL NULL
);
""")
            
            with open(data_file, 'w', encoding='utf-8') as f:
                f.write(f"-- Backup de datos PostgreSQL - {datetime.now()}\n\n")
                f.write("SET session_replication_role = 'replica';\n\n")
                
                for table in tables:
                    df = tables_data.get(table, pd.DataFrame())
                    
                    if not df.empty:
                        f.write(f"-- Datos de {table}\n")
                        f.write(f"DELETE FROM {table};\n")
                        
                        columns = ', '.join(df.columns)
                        f.write(f"INSERT INTO {table} ({columns}) VALUES\n")
                        
                        values_list = []
                        for _, row in df.iterrows():
                            values = []
                            for col in df.columns:
                                value = row[col]
                                if pd.isna(value) or value is None:
                                    values.append('NULL')
                                elif isinstance(value, str):
                                    escaped = value.replace("'", "''")
                                    values.append(f"'{escaped}'")
                                elif isinstance(value, datetime):
                                    values.append(f"'{value.isoformat()}'")
                                else:
                                    values.append(str(value))
                            
                            values_list.append(f"({', '.join(values)})")
                        
                        f.write(',\n'.join(values_list))
                        f.write(';\n\n')
                
                f.write("SET session_replication_role = 'origin';\n")
            
            progress.progress(70)
        
        # PASO 3: Crear base de datos SQLite
        status.text("🗄️ Creando base de datos SQLite...")
        create_sqlite_database(sqlite_file, tables_data)
        progress.progress(85)
        
        # PASO 4: Crear archivos complementarios
        status.text("📄 Creando archivos complementarios...")
        
        restore_file = os.path.join(backup_dir, "restore_postgres.py")
        with open(restore_file, 'w', encoding='utf-8') as f:
            f.write('''#!/usr/bin/env python3
import sys
from sqlalchemy import create_engine, text

def restore(db_url):
    engine = create_engine(db_url)
    files = ["01_structure.sql", "02_data.sql"]
    
    for file in files:
        print(f"Ejecutando {file}...")
        with open(file, 'r', encoding='utf-8') as f:
            sql = f.read()
        
        with engine.begin() as conn:
            for cmd in sql.split(';'):
                if cmd.strip():
                    try:
                        conn.execute(text(cmd))
                    except Exception as e:
                        print(f"Warning: {e}")
        
        print(f"✅ {file} completado")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python restore_postgres.py postgresql://user:pass@host:port/db")
        sys.exit(1)
    restore(sys.argv[1])
''')
        
        readme_file = os.path.join(backup_dir, "README.txt")
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(f"""
═══════════════════════════════════════════════════════════
  BACKUP BASE DE DATOS CAPELLO
  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
═══════════════════════════════════════════════════════════

CONTENIDO DEL BACKUP:


🎯 ARCHIVO PRINCIPAL (RECOMENDADO):
   📁 backup_database.db ............ Base de datos SQLite completa

📄 ARCHIVOS POSTGRESQL:
   📋 01_structure.sql .............. Estructura de tablas
   💾 02_data.sql ................... Datos completos
   🔧 restore_postgres.py ........... Script de restauración
   
📖 DOCUMENTACIÓN:
   📝 README.txt .................... Este archivo

═══════════════════════════════════════════════════════════
  OPCIÓN 1: USAR SQLITE (RECOMENDADO - MÁS FÁCIL)
═══════════════════════════════════════════════════════════

El archivo "backup_database.db" es una base de datos completa,
portable y lista para usar. NO necesita instalación de servidor.

CÓMO ABRIR LA BASE SQLITE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DB Browser for SQLite:
  1. Descargar gratis: https://sqlitebrowser.org/
  2. Instalar el programa
  3. Archivo → Abrir base de datos
  4. Seleccionar "backup_database.db"
  5. ¡Listo! Ya puedes ver y consultar todo

═══════════════════════════════════════════════════════════
  OPCIÓN 2: RESTAURAR EN POSTGRESQL
═══════════════════════════════════════════════════════════

Si necesitas restaurar en un servidor PostgreSQL:

python restore_postgres.py "postgresql://user:pass@localhost:5432/dbname"

NOTA: Necesitas tener PostgreSQL instalado y una base de datos creada.

═══════════════════════════════════════════════════════════

  INFORMACIÓN TÉCNICA


TABLAS INCLUIDAS:
  • vendedores .................... Información de vendedores
  • clientes ...................... Base de clientes
  • rubros ........................ Categorías de productos
  • articulos ..................... Inventario completo
  • remitos ....................... Documentos de entrega
  • remito_items .................. Detalle de entregas

VENTAJAS DE SQLITE:
  ✓ Un solo archivo con todo
  ✓ No requiere servidor PostgreSQL
  ✓ Portable - funciona en cualquier computadora
  ✓ Compatible con múltiples herramientas
  ✓ Perfecto para consultas y análisis
  ✓ Gratis y de código abierto

SEGURIDAD:
  ⚠ Este backup contiene datos sensibles
  ⚠ Mantenerlo en lugar seguro
  ⚠ No compartir públicamente

═══════════════════════════════════════════════════════════
""")
        
        progress.progress(95)
        
        # PASO 5: Crear ZIP
        status.text("📦 Comprimiendo archivos...")
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, backup_dir)
                    zf.write(file_path, arc_name)
        
        zip_buffer.seek(0)
        progress.progress(100)
        status.text("✅ Backup completado!")
        
        zip_data_bytes = zip_buffer.getvalue()
        backup_filename = f"{backup_name}.zip"
        zip_size = len(zip_data_bytes) / 1024 / 1024  # MB

        # Guardar resultado en session_state para persistencia
        st.session_state.backup_result = {
            'bytes': zip_data_bytes,
            'filename': backup_filename,
            'size_mb': zip_size,
            'total_rows': sum(len(df) for df in tables_data.values()),
            'total_tables': len(tables_data)
        }
        
        # Limpiar archivos temporales
        shutil.rmtree(temp_dir)
        
        # Forzar un rerun limpio para mostrar la sección de guardado/descarga persistente
        st.rerun()

    except Exception as e:
        st.error(f"❌ Error creando backup: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# Función principal para el menú
def simple_backup():
    """Función para llamar desde el menú principal"""
    simple_backup_page()

if __name__ == "__main__":
    simple_backup()