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
    # Si el programa se ejecuta como un script de Python...
    with st.sidebar:
        st.markdown(
            """
            <style>
                [data-testid=stSidebar] {
                    min-width: 300px;
                    max-width: 300px;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Control de estado de navegación
        if 'currentpage' not in st.session_state:
            st.session_state.currentpage = 'Codigos de Barra'  # valor por defecto

        mainmenu = option_menu(menu_title=None,
                              options=["Codigos de Barra", "Clientes", "Articulos", "Remitos"],
                              icons=["file", "pencil", "pencil", "truck"],
                              menu_icon="app-indicator",
                              default_index=0)

        # Detectar cambio de página
        if mainmenu != st.session_state.currentpage:
            # Limpiar variables en session_state que puedan contener datos viejos
            claves_a_limpiar = [
                'clientes_df',
                'articulos_df'
            ]
            for clave in claves_a_limpiar:
                if clave in st.session_state:
                    del st.session_state[clave]

            # Actualizar la página actual y forzar recarga completa
            st.session_state.currentpage = mainmenu
            st.rerun()

        # Definición de submenús y lógica por página...
        if mainmenu == "Remitos":
            submenu = option_menu(menu_title="Remitos",
                                      options=["Entregas", "Devoluciones y Ventas", "Anulaciones"],
                                      icons=["file-earmark-plus", "file-earmark-plus", "file-earmark-plus"],
                                      menu_icon="folder", default_index=0, orientation="vertical")

        elif mainmenu == "Articulos":
            submenu = option_menu(menu_title="Articulos",
                                      options=["ABM Articulos", "Cargar Novedades"],
                                      icons=["file-earmark-plus", "file-earmark-plus"],
                                      menu_icon="folder", default_index=0, orientation="vertical")
        else:
            submenu = None

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

    elif mainmenu == "Remitos":
        if submenu == "Entregas":
            rem_ent.remitos_entregas()
        elif submenu == "Devoluciones y Ventas":
            remitos_ventas()
        elif submenu == "Anulaciones":
            remitos_anulaciones()

if __name__ == '__main__':
    app()
