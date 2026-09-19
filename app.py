import streamlit as st
import config

st.set_page_config(
    page_title=config.TITULO_APP,
    layout="wide"
)

import sys, os, time, traceback
import datetime
import models
from gen_barcode import gen_barcode
from update_art import update_art
from clientes import clientes_crud
from articulos import articulos_crud
from remitos_ventas import remitos_ventas
from remitos_anulaciones import remitos_anulaciones
import remitos_entregas as rem_ent

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
                    padding-top: 0.4rem !important;
                    padding-bottom: 1.5rem !important;
                }
                [data-testid="stSidebarHeader"],
                [data-testid="stSidebarNav"],
                [data-testid="stSidebarNavItems"],
                div[data-testid="stSidebarNavSeparator"] {
                    display: none !important;
                }
                /* Espaciado compacto pero limpio entre elementos */
                [data-testid="stSidebar"] div[data-testid="stVerticalBlock"],
                [data-testid="stSidebar"] div[data-testid="stVerticalBlockBorderWrapper"] {
                    gap: 0.35rem !important;
                }
                .sidebar-section-title {
                    display: block !important;
                    font-size: 0.98rem;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.6px;
                    color: #ffffff;
                    margin-top: 1rem !important;
                    margin-bottom: 0.55rem !important;
                    padding-left: 0.3rem;
                    padding-bottom: 0.3rem;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
                    line-height: 1.4 !important;
                }
                [data-testid="stSidebar"] button {
                    display: flex !important;
                    justify-content: flex-start !important;
                    align-items: center !important;
                    text-align: left !important;
                    padding: 0.22rem 0.65rem !important;
                    min-height: 1.85rem !important;
                    margin: 0 !important;
                    border-radius: 6px !important;
                    width: 100% !important;
                }
                [data-testid="stSidebar"] button > div,
                [data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] {
                    display: flex !important;
                    justify-content: flex-start !important;
                    text-align: left !important;
                    width: 100% !important;
                }
                [data-testid="stSidebar"] button p,
                [data-testid="stSidebar"] button div p {
                    font-size: 0.80rem !important;
                    font-weight: 500 !important;
                    text-align: left !important;
                    justify-content: flex-start !important;
                    line-height: 1.3 !important;
                    margin: 0 !important;
                    width: 100% !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )



        # Inicialización de estados de navegación
        if 'currentpage' not in st.session_state:
            st.session_state.currentpage = 'Codigos de Barra'
        if 'remitos_sub_nav' not in st.session_state:
            st.session_state.remitos_sub_nav = 'Entregas'
        if 'articulos_sub_nav' not in st.session_state:
            st.session_state.articulos_sub_nav = 'ABM Articulos'
        if 'informes_sub_nav' not in st.session_state:
            st.session_state.informes_sub_nav = 'Ganancias por Día'
        if 'backup_sub_nav' not in st.session_state:
            st.session_state.backup_sub_nav = 'Crear Backup'

        def nav_item(label, page, sub_page=None, key=None):
            is_active = (st.session_state.currentpage == page)
            if sub_page is not None:
                is_active = is_active and (st.session_state.get(f"{page.lower()}_sub_nav") == sub_page)
            
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=key or f"nav_{page}_{sub_page or 'main'}", width="stretch", type=btn_type):
                if not is_active:
                    st.session_state.currentpage = page
                    if sub_page is not None:
                        st.session_state[f"{page.lower()}_sub_nav"] = sub_page
                    for clave in ['clientes_df', 'articulos_df', 'backup_manager']:
                        st.session_state.pop(clave, None)
                    st.rerun()

        # --- SECCIÓN GENERAL ---
        st.markdown("<div class='sidebar-section-title'>📋 General</div>", unsafe_allow_html=True)
        nav_item("🏷️ Códigos de Barra", "Codigos de Barra")
        nav_item("👥 Clientes", "Clientes")
        nav_item("📝 Artículos", "Articulos", "ABM Articulos")
        nav_item("🔖 Rubros", "Rubros")

        # --- SECCIÓN REMITOS (SIEMPRE ABIERTA) ---
        st.markdown("<div class='sidebar-section-title'>📦 Remitos</div>", unsafe_allow_html=True)
        nav_item("➕ Entregas (Carga)", "Remitos", "Entregas")
        nav_item("📥 Recepciones (Ventas)", "Remitos", "Recepciones")
        nav_item("🔍 Consultas", "Remitos", "Consultas")
        nav_item("❌ Anulaciones", "Remitos", "Anulaciones")

        # --- SECCIÓN INFORMES ---
        st.markdown("<div class='sidebar-section-title'>📊 Informes</div>", unsafe_allow_html=True)
        nav_item("📈 Ganancias por Día", "Informes", "Ganancias por Día")
        nav_item("🏢 Ranking por Empresa", "Informes", "Ranking por Empresa")
        nav_item("🧢 Ranking por Artículo", "Informes", "Ranking por Artículo")

        # --- SECCIÓN SISTEMA ---
        st.markdown("<div class='sidebar-section-title'>🛡️ Sistema</div>", unsafe_allow_html=True)
        nav_item("💾 Crear Backup", "Backup", "Crear Backup")
        nav_item("🔄 Restaurar Backup", "Backup", "Restaurar Backup")
        nav_item("📂 Carga de Artículos", "Articulos", "Cargar Novedades")

        mainmenu = st.session_state.get("currentpage", "Codigos de Barra")
        submenu = st.session_state.get(f"{mainmenu.lower()}_sub_nav", None)

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
        else:
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