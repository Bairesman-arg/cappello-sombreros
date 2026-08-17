import streamlit as st
import sys
import os

# Agregar directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models
if 'dbinitialized' not in st.session_state:
    models.init_db()
    st.session_state.dbinitialized = True

from remitos_ventas_movil import remitos_ventas_movil

if __name__ == "__main__":
    remitos_ventas_movil()
