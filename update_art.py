# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import os
import models # Make sure you have models.py in the same directory
import config

# Import new functions from models.py
from models import update_or_insert_articulos_from_excel

st.set_page_config(
    layout="wide"
)

def update_art():
    st.title(config.TITULO_APP)
    st.header("Actualización del Maestro de Artículos")
    st.subheader("Subir archivo de artículos")

    mensaje = "Por favor, suba el archivo Excel (.xlsm) con el formato de artículos. Los datos deben empezar en la fila 9.\n"
    mensaje += "ATENCIÓN: Los datos previamente existentes serán reemplazados por la información de la planilla:\n"
    mensaje += "basandose en el código de artículo, se afectarán las descripciones y precios."
    st.info(mensaje)

    uploaded_file = st.file_uploader(
        "Seleccione un archivo de Excel",
        type=['xlsm'],
        help="Solo se aceptan archivos con la extensión .xlsm"
    )

    if uploaded_file is not None:
        try:
            # Lee el archivo directamente en un DataFrame sin guardarlo
            # header=7 indica que los encabezados están en la 8ª fila (índice 7),
            # y los datos comienzan en la fila 9 (8ª fila de datos).
            df_raw = pd.read_excel(uploaded_file, header=7)
            
            # Selecciona las 3 primeras columnas (nro_articulo, descripcion, precio_real)
            df = df_raw.iloc[:, 0:3].copy()
            df.columns = ['nro_articulo', 'descripcion', 'precio_real']

            # Limpia y procesa los datos
            df['nro_articulo'] = df['nro_articulo'].astype(str).str.strip().str.upper()
            df = df.dropna(subset=['nro_articulo'])
            df['precio_real'] = pd.to_numeric(df['precio_real'], errors='coerce').fillna(0)
            df['descripcion'] = df['descripcion'].astype(str).str.strip().str.capitalize()

            st.subheader("Vista previa del archivo de actualización")

            # Muestra el DataFrame en pantalla
            st.dataframe(df.head(10), 
                        hide_index=True, 
                        width="stretch",
                        height=210,
                        column_config={
                            "nro_articulo": st.column_config.TextColumn("Artículo"),
                            "descripcion": st.column_config.TextColumn("Descripción"),
                            "precio_real": st.column_config.NumberColumn(
                                "Precio Real",
                                format="$ %.2f"
                            )
                        }
            )

            # Botón para confirmar la carga a la base de datos
            if st.button("Cargar datos al Maestro de Artículos", type="primary"):
                with st.spinner('Cargando datos (puede demorar algún minuto)...'):
                    # Llama a la función que maneja la lógica de la base de datos
                    stats = update_or_insert_articulos_from_excel(df)
                    st.success(f"¡Carga finalizada!")
                    st.write(f"  Artículos insertados: **{stats['insertados']}**  |  Artículos actualizados: **{stats['actualizados']}**")

        except Exception as e:
            st.error(f"Ocurrió un error al procesar el archivo o al actualizar la base de datos: {e}")

    st.markdown(f"`{config.FOOTER_APP}`")
