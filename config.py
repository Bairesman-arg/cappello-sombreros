# -*- coding: utf-8 -*-
import streamlit as st

VERSION = "1.0.49"
TITULO_APP = f"🧢 SISTEMA CAPPELLO vs {VERSION}"
# TITULO_APP = "INTRODUCCION A PYTHON"
FOOTER_APP = "Sistema Capello® - Powered by Python and Streamlit - Telegram: @Bairesman - 2025"

RUBRO_DEFAULT = "GORRAS"
VENDEDOR_DEFAULT = "VICENTE"

# Funciones Comunes ---
def init_clientes_articulos():
    # Recarga Clientes y Articulos en diversas páginas
    try:
        if "porc_dto" in st.session_state:
            st.session_state.porc_dto = None
        del st.session_state.clientes_df
        del st.session_state.articulos_df
    except:
        pass
