import streamlit as st
from streamlit_option_menu import option_menu

from gen_barcode import gen_barcode
from update_art import update_art
from clientes import clientes_crud
from articulos import articulos_crud
from remitos_ventas import remitos_ventas
from remitos_anulaciones import remitos_anulaciones
import remitos_entregas as rem_ent
import sys, os, time, traceback
import datetime
import models
import config

# This will create the engine
# TITLE -- coding utf-8 --

if 'dbinitialized' not in st.session_state:
    # Intenta obtener el estado de la variable, si no existe, la inicializa...
    models.init_db()
    st.session_state.dbinitialized = True

def whereami():
    rutascript = ''
    if getattr(sys, 'frozen', False):
        # Se ejecuta solo la primera vez que la aplicación arranca...
        rutascript = os.path.dirname(sys.executable)
    else:
        # Si el programa se ejecuta como un archivo ejecutable...
        rutascript = os.path.dirname(os.path.abspath(__file__))
    return rutascript

RUTASCRIPT = whereami()

def app():
    # Inyectar idioma español en el documento principal para tooltips nativos del navegador en TODO el sistema
    st.components.v1.html(
        """
        <script>
            (function() {
                const doc = window.parent.document;
                if (doc && doc.documentElement) {
                    doc.documentElement.lang = 'es';
                }
            })();
        </script>
        """,
        height=0,
    )

    # Si el programa se ejecuta como un script de Python...
    with st.sidebar:
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] {
                    min-width: 300px;
                    max-width: 300px;
                }
                [data-testid="stSidebarUserContent"],
                section[data-testid="stSidebar"] > div {
                    padding-top: 1rem !important;
                }
                [data-testid="stSidebarHeader"] {
                    display: none !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Control de estado de navegación
        if 'currentpage' not in st.session_state:
            st.session_state.currentpage = 'Codigos de Barra'  # valor por defecto

        # MENÚ PRINCIPAL - Incluye Rubros, Informes y Backup
        mainmenu = option_menu(menu_title=None,
                               options=["Codigos de Barra", "Clientes", "Articulos", "Rubros", "Remitos", "Informes", "Backup"],
                               icons=["file", "pencil", "pencil", "tag", "truck", "graph-up-arrow", "shield-check"],
                               menu_icon="app-indicator",
                               default_index=0,
                               key="main_menu_nav")

        # Detectar cambio de página
        if mainmenu != st.session_state.currentpage:
            # Limpiar variables en session_state que puedan contener datos viejos
            claves_a_limpiar = [
                'clientes_df',
                'articulos_df',
                'backup_manager'
            ]
            for clave in claves_a_limpiar:
                if clave in st.session_state:
                    del st.session_state[clave]

            # Actualizar la página actual en session_state
            st.session_state.currentpage = mainmenu

        if mainmenu == "Remitos":
            submenu = option_menu(menu_title="Remitos",
                                  options=["Entregas", "Recepciones", "Carga Móvil", "Anulaciones"],
                                  icons=["file-earmark-plus", "file-earmark-plus", "phone", "file-earmark-plus"],
                                  menu_icon="folder", default_index=0, orientation="vertical",
                                  key="remitos_submenu_nav")

        elif mainmenu == "Articulos":
            submenu = option_menu(menu_title="Articulos",
                                  options=["ABM Articulos", "Cargar Novedades"],
                                  icons=["file-earmark-plus", "file-earmark-plus"],
                                  menu_icon="folder", default_index=0, orientation="vertical",
                                  key="articulos_submenu_nav")
        
        elif mainmenu == "Backup":
            submenu = option_menu(menu_title="Backup",
                                  options=["Crear Backup", "Restaurar Backup"],
                                  icons=["download", "upload"],
                                  menu_icon="shield-check", 
                                  default_index=0, 
                                  orientation="vertical",
                                  key="backup_submenu_nav")
        else:
            submenu = None

    # Redirección por URL directa de parámetro ?page=carga_movil
    if st.query_params.get("page") == "carga_movil":
        from remitos_ventas_movil import remitos_ventas_movil
        remitos_ventas_movil()
        return

    # Lógica para renderizar contenido según menú y submenú
    if mainmenu == "Codigos de Barra":
        gen_barcode()

    elif mainmenu == "Clientes":
        clientes_crud()

    elif mainmenu == "Articulos":
        if submenu == "Cargar Novedades":
            update_art()
        elif submenu == "ABM Articulos":
            articulos_crud()

    elif mainmenu == "Rubros":
        from rubros import rubros_crud
        rubros_crud()

    elif mainmenu == "Remitos":
        if submenu == "Entregas":
            rem_ent.remitos_entregas()
        elif submenu == "Recepciones":
            remitos_ventas()
        elif submenu == "Carga Móvil 📱":
            from remitos_ventas_movil import remitos_ventas_movil
            remitos_ventas_movil()
        elif submenu == "Anulaciones":
            remitos_anulaciones()

    elif mainmenu == "Informes":
        st.title(config.TITULO_APP)
        st.header("Informes")
        st.info("Módulo de Informes en desarrollo.")
    
    # NUEVA SECCIÓN PARA BACKUP - Importación lazy
    elif mainmenu == "Backup":
        if submenu == "Crear Backup":
            from backup_simple import simple_backup
            simple_backup()
        if submenu == "Restaurar Backup":
            from restore_backup import restore_backup
            restore_backup()

if __name__ == '__main__':
    app()