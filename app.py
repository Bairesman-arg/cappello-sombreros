import streamlit as st
import config

st.set_page_config(
    page_title=config.TITULO_APP,
    layout="wide"
)

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
    st.components.v1.html(
        """
        <script>
            (function() {
                const parentDoc = window.parent ? window.parent.document : document;
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

                function selectAll(el) {
                    if (!el) return;
                    try {
                        if (el.type === 'number') {
                            el.type = 'text';
                            el.select();
                            el.setSelectionRange(0, 9999);
                            const restoreNumber = function() {
                                el.type = 'number';
                                el.removeEventListener('blur', restoreNumber);
                            };
                            el.addEventListener('blur', restoreNumber);
                        } else {
                            el.select();
                            el.setSelectionRange(0, 9999);
                        }
                    } catch(e) {
                        try { el.select(); } catch(err) {}
                    }
                }

                function attachAutoSelect() {
                    const inputs = parentDoc.querySelectorAll('input[type="text"], input[type="number"]');
                    inputs.forEach(input => {
                        if (!input.dataset.autoSelectAttached) {
                            input.dataset.autoSelectAttached = "true";
                            const handler = function() {
                                const el = this;
                                setTimeout(() => selectAll(el), 30);
                            };
                            input.addEventListener('focus', handler);
                            input.addEventListener('click', handler);
                            input.addEventListener('mousedown', function() {
                                const el = this;
                                setTimeout(() => selectAll(el), 50);
                            });
                        }
                    });
                }

                attachAutoSelect();
                if (!window.parent._autoSelectTimer) {
                    window.parent._autoSelectTimer = setInterval(attachAutoSelect, 300);
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
        if st.button("🔄 Recargar Menús", width="stretch", help="Refresca la navegación"):
            st.session_state.menu_version = st.session_state.get("menu_version", 0) + 1
            st.rerun()

        st.markdown("<div style='margin-bottom: 0.4rem;'></div>", unsafe_allow_html=True)

        # Control de estado de navegación
        menu_v = st.session_state.get("menu_version", 0)
        if 'currentpage' not in st.session_state:
            st.session_state.currentpage = 'Codigos de Barra'

        main_options = ["Codigos de Barra", "Clientes", "Articulos", "Rubros", "Remitos", "Informes", "Backup"]
        current_page = st.session_state.currentpage
        default_main_index = main_options.index(current_page) if current_page in main_options else 0

        menu_styles = {
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#fafafa", "font-size": "15px"},
            "nav-link": {
                "font-size": "15px",
                "text-align": "left",
                "margin": "3px 0px",
                "padding": "6px 10px",
            },
            "nav-link-selected": {"background-color": "#ff4b4b", "font-size": "15px", "font-weight": "600"},
        }

        submenu_styles = {
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"color": "#fafafa", "font-size": "14px"},
            "title": {"font-size": "15px", "font-weight": "600"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "3px 0px",
                "padding": "5px 10px",
            },
            "nav-link-selected": {"background-color": "#ff4b4b", "font-size": "14px", "font-weight": "600"},
        }

        # MENÚ PRINCIPAL - Incluye Rubros, Informes y Backup
        main_selected = option_menu(menu_title=None,
                               options=main_options,
                               icons=["file", "pencil", "pencil", "tag", "truck", "graph-up-arrow", "shield-check"],
                               menu_icon="app-indicator",
                               default_index=default_main_index,
                               styles=menu_styles,
                               key=f"main_menu_nav_{menu_v}")

        # Solo si main_selected devuelve un valor válido (evita rehidratación asíncrona de iframe en la nube)
        if main_selected and main_selected != st.session_state.get("currentpage"):
            st.session_state.currentpage = main_selected
            if main_selected == "Remitos":
                st.session_state["remitos_sub_nav"] = "Entregas"
            elif main_selected == "Articulos":
                st.session_state["articulos_sub_nav"] = "ABM Articulos"
            elif main_selected == "Informes":
                st.session_state["informes_sub_nav"] = "Ganancias por Día"
            elif main_selected == "Backup":
                st.session_state["backup_sub_nav"] = "Crear Backup"
            for clave in ['clientes_df', 'articulos_df', 'backup_manager']:
                st.session_state.pop(clave, None)

        mainmenu = st.session_state.get("currentpage", "Codigos de Barra")

        if mainmenu == "Remitos":
            rem_options = ["Entregas", "Recepciones", "Consultas", "Carga Móvil", "Anulaciones"]
            cur_rem_sub = st.session_state.get("remitos_sub_nav", "Entregas")
            def_rem_idx = rem_options.index(cur_rem_sub) if cur_rem_sub in rem_options else 0

            sub_selected = option_menu(menu_title="Remitos",
                                  options=rem_options,
                                  icons=["file-earmark-plus", "file-earmark-plus", "search", "phone", "file-earmark-plus"],
                                  menu_icon="folder", default_index=def_rem_idx, orientation="vertical",
                                  styles=submenu_styles,
                                  key=f"remitos_sub_nav_{menu_v}")
            if sub_selected:
                st.session_state["remitos_sub_nav"] = sub_selected
            submenu = st.session_state.get("remitos_sub_nav", "Entregas")

        elif mainmenu == "Articulos":
            art_options = ["ABM Articulos", "Cargar Novedades"]
            cur_art_sub = st.session_state.get("articulos_sub_nav", "ABM Articulos")
            def_art_idx = art_options.index(cur_art_sub) if cur_art_sub in art_options else 0

            sub_selected = option_menu(menu_title="Articulos",
                                  options=art_options,
                                  icons=["file-earmark-plus", "file-earmark-plus"],
                                  menu_icon="folder", default_index=def_art_idx, orientation="vertical",
                                  styles=submenu_styles,
                                  key=f"articulos_sub_nav_{menu_v}")
            if sub_selected:
                st.session_state["articulos_sub_nav"] = sub_selected
            submenu = st.session_state.get("articulos_sub_nav", "ABM Articulos")

        elif mainmenu == "Informes":
            inf_options = ["Ganancias por Día", "Ranking por Empresa", "Ranking por Artículo"]
            cur_inf_sub = st.session_state.get("informes_sub_nav", "Ganancias por Día")
            def_inf_idx = inf_options.index(cur_inf_sub) if cur_inf_sub in inf_options else 0

            sub_selected = option_menu(menu_title="Informes",
                                  options=inf_options,
                                  icons=["graph-up-arrow", "building", "box-seam"],
                                  menu_icon="graph-up", 
                                  default_index=def_inf_idx, 
                                  orientation="vertical",
                                  styles=submenu_styles,
                                  key=f"informes_sub_nav_{menu_v}")
            if sub_selected:
                st.session_state["informes_sub_nav"] = sub_selected
            submenu = st.session_state.get("informes_sub_nav", "Ganancias por Día")
        
        elif mainmenu == "Backup":
            bak_options = ["Crear Backup", "Restaurar Backup"]
            cur_bak_sub = st.session_state.get("backup_sub_nav", "Crear Backup")
            def_bak_idx = bak_options.index(cur_bak_sub) if cur_bak_sub in bak_options else 0

            sub_selected = option_menu(menu_title="Backup",
                                  options=bak_options,
                                  icons=["download", "upload"],
                                  menu_icon="shield-check", 
                                  default_index=def_bak_idx, 
                                  orientation="vertical",
                                  styles=submenu_styles,
                                  key=f"backup_sub_nav_{menu_v}")
            if sub_selected:
                st.session_state["backup_sub_nav"] = sub_selected
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
        elif submenu == "Consultas":
            from remitos_consultas import remitos_consultas
            remitos_consultas()
        elif submenu == "Carga Móvil":
            from remitos_ventas_movil import remitos_ventas_movil
            remitos_ventas_movil()
        elif submenu == "Anulaciones":
            remitos_anulaciones()

    elif mainmenu == "Informes":
        st.title(config.TITULO_APP)
        if submenu == "Ganancias por Día":
            from info_ganancias import info_ganancias_dia
            info_ganancias_dia()
        elif submenu == "Ranking por Empresa":
            from info_empresas import info_empresas_ranking
            info_empresas_ranking()
        elif submenu == "Ranking por Artículo":
            from info_articulos import info_articulos_ranking
            info_articulos_ranking()
        else:
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