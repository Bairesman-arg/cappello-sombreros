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
    # Detectar si la URL contiene /carga_movil en la ruta y forzar ?page=carga_movil
    st.components.v1.html(
        """
        <script>
            (function() {
                const parentDoc = window.parent.document;
                if (parentDoc && parentDoc.documentElement) {
                    parentDoc.documentElement.lang = 'es';
                }
                const parentUrl = window.parent.location.href;
                const parentPath = window.parent.location.pathname;
                if ((parentPath.toLowerCase().includes("carga_movil")) && !parentUrl.includes("page=carga_movil")) {
                    const searchParams = new URLSearchParams(window.parent.location.search);
                    searchParams.set("page", "carga_movil");
                    window.parent.location.search = searchParams.toString();
                }
            })();
        </script>
        """,
        height=0,
    )

    query_page = str(st.query_params.get("page", "")).lower()
    if query_page == "carga_movil" or "carga_movil" in st.query_params:
        from remitos_ventas_movil import remitos_ventas_movil
        remitos_ventas_movil()
        return

    # Si el programa se ejecuta como un script de Python...
    with st.sidebar:
        st.markdown(
            """
            <style>
                [data-testid="stSidebar"] {
                    min-width: 280px;
                    max-width: 280px;
                }
                [data-testid="stSidebarUserContent"],
                section[data-testid="stSidebar"] > div {
                    padding-top: 0.5rem !important;
                }
                [data-testid="stSidebarHeader"],
                [data-testid="stSidebarNav"],
                [data-testid="stSidebarNavItems"],
                div[data-testid="stSidebarNavSeparator"] {
                    display: none !important;
                }
                [data-testid="stSidebar"] button,
                [data-testid="stSidebar"] button div,
                [data-testid="stSidebar"] button p {
                    font-size: 0.78rem !important;
                    font-weight: 500 !important;
                }
                [data-testid="stSidebar"] button {
                    padding: 0.2rem 0.5rem !important;
                    min-height: 1.9rem !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Botón arriba de todo para recargar la navegación
        if st.button("🔄 Recargar Menús", use_container_width=True, help="Refresca la navegación"):
            for k in ["main_menu_nav", "remitos_sub_nav", "articulos_sub_nav", "backup_sub_nav", "currentpage"]:
                st.session_state.pop(k, None)
            st.rerun()

        st.markdown("<div style='margin-bottom: 0.4rem;'></div>", unsafe_allow_html=True)

        # Control de estado de navegación
        if 'currentpage' not in st.session_state:
            st.session_state.currentpage = 'Codigos de Barra'

        menu_styles = {
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#fafafa", "font-size": "13px"},
            "nav-link": {
                "font-size": "13px",
                "text-align": "left",
                "margin": "2px 0px",
                "padding": "5px 10px",
            },
            "nav-link-selected": {"background-color": "#ff4b4b", "font-size": "13px", "font-weight": "600"},
        }

        submenu_styles = {
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#fafafa", "font-size": "12px"},
            "title": {"font-size": "13px", "font-weight": "600"},
            "nav-link": {
                "font-size": "12px",
                "text-align": "left",
                "margin": "2px 0px",
                "padding": "4px 10px",
            },
            "nav-link-selected": {"background-color": "#ff4b4b", "font-size": "12px", "font-weight": "600"},
        }

        # MENÚ PRINCIPAL - Incluye Rubros, Informes y Backup
        mainmenu = option_menu(menu_title=None,
                               options=["Codigos de Barra", "Clientes", "Articulos", "Rubros", "Remitos", "Informes", "Backup"],
                               icons=["file", "pencil", "pencil", "tag", "truck", "graph-up-arrow", "shield-check"],
                               menu_icon="app-indicator",
                               default_index=0,
                               styles=menu_styles,
                               key="main_menu_nav")

        if not mainmenu:
            mainmenu = st.session_state.get("currentpage", "Codigos de Barra")

        # Detectar cambio de página principal
        if mainmenu != st.session_state.currentpage:
            st.session_state.currentpage = mainmenu
            st.session_state["remitos_sub_nav"] = "Entregas"
            st.session_state["articulos_sub_nav"] = "ABM Articulos"
            st.session_state["backup_sub_nav"] = "Crear Backup"
            for clave in ['clientes_df', 'articulos_df', 'backup_manager']:
                st.session_state.pop(clave, None)

        if mainmenu == "Remitos":
            if "remitos_sub_nav" not in st.session_state or not st.session_state["remitos_sub_nav"]:
                st.session_state["remitos_sub_nav"] = "Entregas"
            submenu = option_menu(menu_title="Remitos",
                                  options=["Entregas", "Recepciones", "Carga Móvil", "Anulaciones"],
                                  icons=["file-earmark-plus", "file-earmark-plus", "phone", "file-earmark-plus"],
                                  menu_icon="folder", default_index=0, orientation="vertical",
                                  styles=submenu_styles,
                                  key="remitos_sub_nav")
            if not submenu:
                submenu = st.session_state.get("remitos_sub_nav", "Entregas")

        elif mainmenu == "Articulos":
            if "articulos_sub_nav" not in st.session_state or not st.session_state["articulos_sub_nav"]:
                st.session_state["articulos_sub_nav"] = "ABM Articulos"
            submenu = option_menu(menu_title="Articulos",
                                  options=["ABM Articulos", "Cargar Novedades"],
                                  icons=["file-earmark-plus", "file-earmark-plus"],
                                  menu_icon="folder", default_index=0, orientation="vertical",
                                  styles=submenu_styles,
                                  key="articulos_sub_nav")
            if not submenu:
                submenu = st.session_state.get("articulos_sub_nav", "ABM Articulos")
        
        elif mainmenu == "Backup":
            if "backup_sub_nav" not in st.session_state or not st.session_state["backup_sub_nav"]:
                st.session_state["backup_sub_nav"] = "Crear Backup"
            submenu = option_menu(menu_title="Backup",
                                  options=["Crear Backup", "Restaurar Backup"],
                                  icons=["download", "upload"],
                                  menu_icon="shield-check", 
                                  default_index=0, 
                                  orientation="vertical",
                                  styles=submenu_styles,
                                  key="backup_sub_nav")
            if not submenu:
                submenu = st.session_state.get("backup_sub_nav", "Crear Backup")
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
        elif submenu == "Carga Móvil":
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