# -*- coding: utf-8 -*-
"""
Script de Streamlit para leer códigos y precios desde una hoja de cálculo de Excel,
mostrarlos en una lista desplegable, generar un código de barras
estándar (Code128) del elemento seleccionado y crear un PDF de etiquetas,
con una estructura de navegación en el sidebar.
"""
import streamlit as st
import pandas as pd
import barcode
from barcode.writer import ImageWriter
from PIL import Image
import io
import os
import locale

# Importamos las librerías necesarias para la generación del PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128

import config
import models

# Configuración de locale para el formato de moneda en español
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except locale.Error:
    # Fallback para sistemas que no tienen es_ES.UTF-8
    locale.setlocale(locale.LC_ALL, '')

# --- Funciones de utilidad ---

def load_codes_from_db():
    """
    Lee códigos, descripciones y precios desde la base de datos.
    Retorna una lista de diccionarios.
    """
    try:
        articulos_df = models.get_all_articulos()
        codes_data = []

        if not articulos_df.empty:
            for index, row in articulos_df.iterrows():
                # Asegura que el formato sea el mismo que el del Excel
                codes_data.append({
                    "code": str(row['nro_articulo']),
                    "description": str(row['descripcion']) if pd.notnull(row['descripcion']) else "",
                    "price": str(int(row['precio_real'])) if pd.notnull(row['precio_real']) else "0"
                })
        
        return codes_data
        
    except Exception as e:
        st.error(f"Ocurrió un error al leer la base de datos: {e}")
        return []

def generate_barcode(code_to_generate: str):
    """
    Genera un código de barras (Code128) a partir de un string de texto y retorna
    la imagen en un formato que Streamlit puede mostrar.
    """
    try:
        code128_obj = barcode.get("code128", code_to_generate, writer=ImageWriter())
        buffer = io.BytesIO()
        options = {
            "module_height": 2,
            "quiet_zone": 2,
            "font_size": 3,
            "text_distance": 3,
            "write_text": False
        }
        code128_obj.write(buffer, options)
        buffer.seek(0)
        
        pil_image = Image.open(buffer)
        return pil_image
            
    except Exception as e:
        st.error(f"Error al generar el código de barras: {e}")
        return None
    

def generate_pdf_labels(code: str, price: str, quantity: int):
    """
    Genera un archivo PDF con etiquetas de código de barras,
    ahora optimizado para 5 columnas y 12 filas en una hoja A4.

    El contenido de cada etiqueta está centrado verticalmente para
    lograr una apariencia más equilibrada. La grilla divisoria
    cubre toda el área de las etiquetas correctamente.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Dimensiones de la hoja A4 en milímetros
    page_width, page_height = A4

    # Configuración de la grilla de etiquetas
    num_cols = 5
    num_rows = 12
    
    # Dimensiones de la etiqueta para ajustarse a 5x12
    label_width = 38.4 * mm
    label_height = 23.0 * mm
    
    col_spacing = 2.0 * mm
    
    # Calcular márgenes de la página para centrar la grilla
    total_block_width = (num_cols * label_width) + ((num_cols - 1) * col_spacing)
    total_block_height = num_rows * label_height
    
    margin_left = (page_width - total_block_width) / 2
    margin_top = (page_height - total_block_height) / 2

    # Dimensiones y espaciado de los elementos de la etiqueta
    barcode_height = 6 * mm
    code_font_size = 6
    price_font_size = 16

    space_between_barcode_and_code = 0.5 * mm
    space_between_code_and_price = 0.5 * mm

    # Altura vertical de los elementos para calcular el centrado
    # Se usa una aproximación de la altura del texto
    text_height_code = 2.1 * mm
    text_height_price = 5.6 * mm
    
    total_element_height = (barcode_height + text_height_code + text_height_price +
                            space_between_barcode_and_code + space_between_code_and_price)
    
    vertical_margin = (label_height - total_element_height) / 2

    c.setFont("Helvetica", code_font_size)
    c.setLineWidth(0.25)

    # Dibuja la grilla completa una vez por página
    x_start_grid = margin_left
    y_start_grid = page_height - margin_top - total_block_height
    x_end_grid = margin_left + total_block_width
    y_end_grid = page_height - margin_top

    def draw_grid():
        # Dibuja las líneas horizontales
        for i in range(num_rows + 1):
            y_line = y_end_grid - i * label_height
            c.line(x_start_grid, y_line, x_end_grid, y_line)

        # Dibuja las líneas verticales, corregido para la última línea
        for i in range(num_cols + 1):
            if i < num_cols:
                x_line = x_start_grid + i * (label_width + col_spacing)
            else:
                x_line = x_start_grid + total_block_width
            c.line(x_line, y_start_grid, x_line, y_end_grid)

    draw_grid()

    for i in range(quantity):
        # Avanza a la siguiente página si se alcanza el límite
        if i > 0 and i % (num_rows * num_cols) == 0:
            c.showPage()
            c.setFont("Helvetica", code_font_size)
            c.setLineWidth(0.25)
            draw_grid()
        
        col = (i % (num_rows * num_cols)) % num_cols
        row = (i % (num_rows * num_cols)) // num_cols
        
        x_base = margin_left + col * (label_width + col_spacing)
        y_base = page_height - margin_top - (row + 1) * label_height

        # Posiciona los elementos verticalmente, centrándolos en la etiqueta
        y_barcode = y_base + label_height - vertical_margin - barcode_height
        
        # 1. Dibujar el código de barras
        barcode_obj = code128.Code128(code, barWidth=0.25*mm, barHeight=barcode_height)
        barcode_width = barcode_obj.width
        x_centered_barcode = x_base + (label_width - barcode_width) / 2
        
        barcode_obj.drawOn(c, x_centered_barcode, y_barcode)

        # 2. Dibujar el código alfanumérico
        c.setFont("Helvetica", code_font_size)
        text_width = c.stringWidth(code, "Helvetica", code_font_size)
        x_centered_text = x_base + (label_width - text_width) / 2
        y_text = y_barcode - space_between_barcode_and_code - text_height_code
        
        c.drawString(x_centered_text, y_text, code)
        
        # 3. Dibujar el precio
        c.setFont("Helvetica", price_font_size)
        price_string = f"${int(float(price)):,d}".replace(",", ".")

        price_width = c.stringWidth(price_string, "Helvetica", price_font_size)
        x_centered_price = x_base + (label_width - price_width) / 2
        y_price = y_text - space_between_code_and_price - text_height_price
        
        c.drawString(x_centered_price, y_price, price_string)
            
    c.save()
    buffer.seek(0)
    return buffer

# --- Lógica de las páginas de la aplicación ---
def gen_barcode():

    st.set_page_config(
        layout="wide"
    )
    
    st.title(config.TITULO_APP)
    st.header(f"Generador de Códigos de Barras")

    codes_data = load_codes_from_db()
    
    if codes_data:
        selected_item = st.selectbox(
            " Artículos disponibles:", 
            options=codes_data, 
            index=None, 
            placeholder="Selecciona un código...",
            format_func=lambda item: f"{item['code']} - {item['description']}"
        )

        if selected_item:
            selected_code_only = selected_item['code']
            
            col1, col2 = st.columns([2, 2],gap="small")
            with col1:
                st.subheader("Código de barras:")
                barcode_image = generate_barcode(selected_code_only)
                if barcode_image:
                    st.image(barcode_image, caption=f"Código: {selected_code_only}", width='stretch')
            
            st.subheader("Opciones de Impresión")
            
            col1, col2, col3 = st.columns(3,gap="small")

            with col1:
                price_input = st.text_input(
                    "Precio $:", 
                    value=selected_item['price']
                )

            with col2:
                quantity = st.number_input(
                    "Cantidad de etiquetas (60 p/página en A4):",
                    min_value=1,
                    max_value=4000,
                    value=60,
                    step=1
                )

            if st.button("Generar PDF para Imprimir",):
                pdf_buffer = generate_pdf_labels(selected_code_only, price_input, quantity)
                
                if pdf_buffer:
                    st.success("PDF generado con éxito. Por favor, guarda el archivo en la carpeta 'Etiquetas' en tu Escritorio.")
                    st.download_button(
                        label="Descargar PDF",
                        data=pdf_buffer,
                        file_name=f"etiquetas_{selected_code_only}_{price_input}.pdf",
                        mime="application/pdf"
                    )
    else:
        st.info("No se encontraron códigos o hubo un error al leer la base de datos.")