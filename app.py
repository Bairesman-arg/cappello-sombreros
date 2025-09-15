# -*- coding: utf-8 -*-
import streamlit as st
from streamlit_option_menu import option_menu

from gen_barcode import gen_barcode
from update_art import update_art
from clientes import clientes_crud
from articulos import articulos_crud
from remitos import remitos
import sys, os, time, traceback
import datetime

import models  # This will create the engine
# Intenta obtener el estado de la variable, si no existe, la inicializa
if 'db_initialized' not in st.session_state:
    # Se ejecuta solo la primera vez que la aplicación arranca
    models.init_db()
    st.session_state.db_initialized = True

def where_am_i():
    ruta_script = ""
    if getattr(sys, 'frozen', False):
        # Si el programa se ejecuta como un archivo ejecutable
        ruta_script = os.path.dirname(sys.executable)
    else:
        # Si el programa se ejecuta como un script de Python
        ruta_script = os.path.dirname(os.path.abspath(__file__))
    return ruta_script

RUTA_SCRIPT = where_am_i()

# Manejador general de errores
def manejar_error(exctype, valor, trace):

    # Detecta la interrupcion del teclado y cierra el script en lugar de reiniciarlo.
    if exctype == KeyboardInterrupt:
        print("\nScript detenido por el usuario (Ctrl+C). Cerrando de forma segura...")
        # Aquí se puede agregar logica de limpieza, como cerrar hilos o cerrar conexiones.
        time.sleep(2.5)
        os._exit(0) # Termina el script de forma abrupta pero controlada.

    # Obtener el mensaje de error para mostrar al usuario
    try:
        if "testnet.binance.vision" in str(valor):
            mensaje_usuario = "Conexión a Internet no disponible.\nVerifique y vuelva a intentar."
        else:
            mensaje_usuario = str(valor) + " "*15
    except:
        valor = "ERROR INDETERMINADO"
        mensaje_usuario = valor + " "*15

    # Imprimir el mensaje de error para el usuario en stderr
    sys.stderr.write(f"Error: {mensaje_usuario}\n")

    # Obtener el traceback como una cadena
    traceback_str = ''.join(traceback.format_exception(exctype, valor, trace))

    # Guardar el traceback en un archivo
    with open( RUTA_SCRIPT + "\\cappello_system.err", "a") as archivo:
        archivo.write("Fecha: "
            + datetime.datetime.today().strftime("%d/%m/%y--%H:%M:%S") + "\n")

        archivo.write(traceback_str + "\n")

    print("\nSE HA PRODUCIDO UN ERROR. POR FAVOR VERIFIQUE 'cappello_system.err'\n")
    # Atención! Ante errores se reinicia el script
    st.stop()

# Configurar el hook personalizado para manejar errores no manejados
sys.excepthook = manejar_error

def app():
    
    # --- Sidebar con menú principal y submenú ---
    with st.sidebar:

        st.markdown(
            """
            <style>
                /* Sidebar ancho fijo */
                [data-testid="stSidebar"] {
                    min-width: 300px;
                    max-width: 300px;
                }
            </style>
            """,
            unsafe_allow_html=True
        )

        # --- Control de estado de navegación ---
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Códigos de Barra"

        # Menú principal
        main_menu = option_menu(
            menu_title=None,  # No mostramos título aquí porque ya usamos st.header
            options=["Códigos de Barra", "Clientes", "Artículos", "Remitos"],
            icons=["file", "pencil", "pencil", "truck"],
            menu_icon="app-indicator",
            default_index=0
        )

        # --- Lógica de reinicio de página ---
        if main_menu != st.session_state.current_page:
            st.session_state.current_page = main_menu
            st.rerun() # Fuerza el reinicio de la aplicación para limpiar los estados

        # Submenú si selecciona Remitos
        if main_menu == "Remitos":
            sub_menu = option_menu(
                menu_title="Remitos",
                options=["Entregas"],
                icons=["file-earmark-plus"],
                menu_icon="folder",
                default_index=0,
                orientation="vertical"
            )
        elif main_menu == "Artículos":
            sub_menu = option_menu(
                menu_title="Artículos",
                options=["Cargar Novedades", "ABM Artículos"],
                icons=["file-earmark-plus","file-earmark-plus"],
                menu_icon="folder",
                default_index=0,
                orientation="vertical"
            )
        else:
            sub_menu = None

    # --- Lógica de navegación ---
    if main_menu == "Códigos de Barra":
        gen_barcode()
    elif main_menu == "Clientes":
        clientes_crud()
    elif main_menu == "Artículos":
        if sub_menu == "Cargar Novedades":
            update_art()
        if sub_menu == "ABM Artículos":
            articulos_crud()
    elif main_menu == "Remitos":
        if sub_menu == "Entregas":
            remitos()

if __name__ == "__main__":
    app()
