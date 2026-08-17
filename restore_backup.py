#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de restauración de backup
Permite seleccionar un ZIP de backup y restaurar la base de datos completa
"""

import streamlit as st
import zipfile
import tempfile
import os
from sqlalchemy import create_engine, text
import shutil
import config

def restore_backup_page():
    """Página principal de restauración de backup"""
    
    st.title(config.TITULO_APP)
    st.header("🔄 Restaurar Base de Datos")
    
    # Verificación de configuración
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
    
    # Advertencia importante
    st.warning("""
    ⚠️ **ADVERTENCIA IMPORTANTE:**
    
    Este proceso:
    - **ELIMINARÁ** todos los datos actuales de la base de datos
    - **RECREARÁ** la estructura de tablas
    - **INSERTARÁ** los datos del backup
    
    **Asegúrese de haber hecho un backup actual antes de proceder.**
    """)
    
    # Selector de archivo
    st.markdown("### 📁 Seleccionar Archivo de Backup")
    
    uploaded_file = st.file_uploader(
        "Sube el archivo ZIP de backup",
        type=['zip'],
        help="Archivo generado por la función de backup"
    )
    
    if uploaded_file is not None:
        # Mostrar información del archivo
        file_size = len(uploaded_file.getvalue()) / 1024 / 1024  # MB
        st.info(f"📦 Archivo cargado: **{uploaded_file.name}** ({file_size:.2f} MB)")
        
        # Vista previa del contenido
        with st.expander("🔍 Vista Previa del Contenido del ZIP"):
            try:
                with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
                    files_list = zip_ref.namelist()
                    
                    st.markdown("**Archivos encontrados:**")
                    for file in files_list:
                        if file.endswith('.sql'):
                            st.markdown(f"- 📋 `{file}`")
                        elif file.endswith('.db'):
                            st.markdown(f"- 🗄️ `{file}`")
                        elif file.endswith('.py'):
                            st.markdown(f"- 🐍 `{file}`")
                        else:
                            st.markdown(f"- 📄 `{file}`")
                    
                    # Verificar archivos requeridos
                    required_files = ['01_structure.sql', '02_data.sql']
                    missing_files = [f for f in required_files if f not in files_list]
                    
                    if missing_files:
                        st.error(f"❌ Archivos faltantes: {', '.join(missing_files)}")
                        st.stop()
                    else:
                        st.success("✅ Todos los archivos requeridos están presentes")
            
            except Exception as e:
                st.error(f"❌ Error leyendo el archivo ZIP: {str(e)}")
                st.stop()
        
        st.markdown("---")
        
        # Opciones de restauración
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⚙️ Opciones de Restauración")
            
            restore_option = st.radio(
                "Seleccione el método:",
                ["Restauración Completa (Recomendado)", "Solo Estructura", "Solo Datos"],
                help="Completa: borra todo y restaura. Estructura: solo crea tablas. Datos: solo inserta datos."
            )
            
            confirm_delete = st.checkbox(
                "⚠️ Confirmo que deseo eliminar todos los datos actuales",
                help="Debe marcar esta casilla para proceder"
            )
        
        with col2:
            st.markdown("### 📊 Información")
            st.info("""
            **Proceso de Restauración:**
            
            1. Extracción del ZIP
            2. Validación de archivos
            3. Eliminación de datos actuales
            4. Creación de estructura
            5. Inserción de datos
            6. Verificación final
            """)
        
        # Botón de restauración
        st.markdown("---")
        
        if not confirm_delete:
            st.error("⚠️ Debe confirmar la eliminación de datos para continuar")
        else:
            if st.button("🚀 INICIAR RESTAURACIÓN", type="primary", width="stretch"):
                restore_database(uploaded_file, db_url, restore_option)

    st.markdown(f"`{config.FOOTER_APP}`")

def restore_database(uploaded_file, db_url, restore_option):
    """Ejecuta el proceso de restauración"""
    
    progress = st.progress(0)
    status = st.empty()
    
    try:
        # Paso 1: Extraer ZIP
        status.text("📦 Extrayendo archivos del backup...")
        progress.progress(10)
        
        # Crear directorio temporal
        temp_dir = tempfile.mkdtemp()
        extract_dir = os.path.join(temp_dir, "backup_extract")
        os.makedirs(extract_dir)
        
        # Extraer ZIP
        uploaded_file.seek(0)  # Volver al inicio del archivo
        with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        st.success("✅ Archivos extraídos correctamente")
        progress.progress(20)
        
        # Paso 2: Localizar archivos SQL
        status.text("🔍 Localizando archivos SQL...")
        
        structure_file = None
        data_file = None
        
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file == '01_structure.sql':
                    structure_file = os.path.join(root, file)
                elif file == '02_data.sql':
                    data_file = os.path.join(root, file)
        
        if not structure_file or not data_file:
            st.error("❌ No se encontraron los archivos SQL en el backup")
            shutil.rmtree(temp_dir)
            return
        
        st.success("✅ Archivos SQL localizados")
        progress.progress(30)
        
        # Paso 3: Conectar a la base de datos
        status.text("🔌 Conectando a PostgreSQL...")
        
        engine = create_engine(db_url, pool_pre_ping=True)
        
        st.success("✅ Conexión establecida")
        progress.progress(40)
        
        # Paso 4: Eliminar datos actuales (si corresponde)
        if restore_option in ["Restauración Completa (Recomendado)", "Solo Datos"]:
            status.text("🗑️ Eliminando datos actuales...")
            
            with engine.begin() as conn:
                # Desactivar foreign keys temporalmente
                conn.execute(text("SET session_replication_role = 'replica';"))
                
                # Orden inverso para respetar foreign keys
                tables = ['remito_items', 'remitos', 'articulos', 'rubros', 'clientes', 'vendedores']
                
                for table in tables:
                    try:
                        conn.execute(text(f"DELETE FROM {table};"))
                        st.success(f"✅ Tabla {table} limpiada")
                    except Exception as e:
                        st.warning(f"⚠️ Error limpiando {table}: {str(e)}")
                
                conn.execute(text("SET session_replication_role = 'origin';"))
            
            progress.progress(50)
        
        # Paso 5: Restaurar estructura (si corresponde)
        if restore_option in ["Restauración Completa (Recomendado)", "Solo Estructura"]:
            status.text("🏗️ Recreando estructura de tablas...")
            
            with open(structure_file, 'r', encoding='utf-8') as f:
                structure_sql = f.read()
            
            with engine.begin() as conn:
                # Eliminar tablas existentes primero
                conn.execute(text("""
                    DROP TABLE IF EXISTS remito_items CASCADE;
                    DROP TABLE IF EXISTS remitos CASCADE;
                    DROP TABLE IF EXISTS articulos CASCADE;
                    DROP TABLE IF EXISTS rubros CASCADE;
                    DROP TABLE IF EXISTS clientes CASCADE;
                    DROP TABLE IF EXISTS vendedores CASCADE;
                """))
                
                # Ejecutar comandos de estructura
                for cmd in structure_sql.split(';'):
                    if cmd.strip() and not cmd.strip().startswith('--'):
                        try:
                            conn.execute(text(cmd))
                        except Exception as e:
                            st.warning(f"⚠️ Warning en estructura: {str(e)}")
            
            st.success("✅ Estructura recreada")
            progress.progress(70)
        
        # Paso 6: Restaurar datos
        if restore_option in ["Restauración Completa (Recomendado)", "Solo Datos"]:
            status.text("💾 Restaurando datos...")
            
            with open(data_file, 'r', encoding='utf-8') as f:
                data_sql = f.read()
            
            with engine.begin() as conn:
                # Ejecutar comandos de datos
                commands = data_sql.split(';')
                total_commands = len(commands)
                
                for i, cmd in enumerate(commands):
                    if cmd.strip() and not cmd.strip().startswith('--'):
                        try:
                            conn.execute(text(cmd))
                            if i % 10 == 0:  # Actualizar progreso cada 10 comandos
                                current_progress = 70 + int((i / total_commands) * 25)
                                progress.progress(current_progress)
                        except Exception as e:
                            st.warning(f"⚠️ Warning en datos: {str(e)[:100]}")
            
            st.success("✅ Datos restaurados")
            progress.progress(95)
        
        # Paso 7: Verificación final
        status.text("✅ Verificando restauración...")
        
        with engine.begin() as conn:
            tables = ['vendedores', 'clientes', 'rubros', 'articulos', 'remitos', 'remito_items']
            verification = []
            
            for table in tables:
                try:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    verification.append({
                        "Tabla": table.capitalize(),
                        "Registros": f"{count:,}",
                        "Estado": "✅ OK"
                    })
                except Exception as e:
                    verification.append({
                        "Tabla": table.capitalize(),
                        "Registros": "Error",
                        "Estado": f"❌ {str(e)[:30]}"
                    })
            
            import pandas as pd
            df_verification = pd.DataFrame(verification)
        
        progress.progress(100)
        status.text("🎉 Restauración completada!")
        
        # Mostrar resultados
        st.success("### 🎉 ¡Restauración Completada Exitosamente!")
        
        st.markdown("### 📊 Verificación de Tablas:")
        st.dataframe(df_verification, width="stretch", hide_index=True)
        
        # Resumen
        total_records = sum(
            int(v['Registros'].replace(',', '')) 
            for v in verification 
            if v['Registros'] != 'Error'
        )
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("📋 Tablas Restauradas", len(verification))
        with col_b:
            st.metric("💾 Registros Totales", f"{total_records:,}")
        with col_c:
            ok_tables = len([v for v in verification if v['Estado'] == '✅ OK'])
            st.metric("✅ Tablas OK", f"{ok_tables}/{len(verification)}")
        
        # Limpiar archivos temporales
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        st.error(f"❌ Error durante la restauración: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        
        # Intentar limpiar
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

# Función principal para el menú
def restore_backup():
    """Función para llamar desde el menú principal"""
    restore_backup_page()

if __name__ == "__main__":
    restore_backup()