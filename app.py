# -*- coding: utf-8 -*-
"""
Script de Streamlit para leer códigos y precios desde una hoja de cálculo de Excel,
mostrarlos en una lista desplegable, generar un código de barras
estándar (Code128) del elemento seleccionado y crear un PDF de etiquetas.
"""
import streamlit as st
import openpyxl
import barcode
from barcode.writer import ImageWriter
from PIL import Image
import io
import os

# Importamos las librerías necesarias para la generación del PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128

VERSION = "1.0.2"

# --- Variables de configuración ---
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "DOCS", "ARTICULOS.xlsm")

def load_codes_from_excel(excel_file_path):
    """
    Reads codes from columns A and B, and prices from column C of the
    Excel spreadsheet. Returns a list of dictionaries, where each
    dictionary contains the code, description, and price.
    """
    if not os.path.exists(excel_file_path):
        st.error(f"Error: No se encontró el archivo en la ruta: {excel_file_path}")
        return []
    
    try:
        workbook = openpyxl.load_workbook(excel_file_path, data_only=True)
        sheet = workbook.active
        codes_data = []
        
        for row_num in range(3, sheet.max_row + 1):
            cell_value = sheet[f'A{row_num}'].value
            cell_descrip = sheet[f'B{row_num}'].value
            cell_price = sheet[f'C{row_num}'].value
            
            if cell_value is None:
                break
            
            codes_data.append({
                "code": str(cell_value),
                "description": str(cell_descrip) if cell_descrip is not None else "",
                "price": str(cell_price) if cell_price is not None else "0.00"
            })
        
        return codes_data
        
    except Exception as e:
        st.error(f"Ocurrió un error al leer el archivo de Excel: {e}")
        return []

def generate_barcode(code_to_generate: str):
    """
    Generates a barcode (Code128) from a text string and returns
    the image in a format that Streamlit can display.
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
    Generates a PDF file with barcode labels in a
    10 rows by 4 columns format (H34140).
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Dimensions of A4 sheet in millimeters
    page_width, page_height = A4

    # Dimensions and spacing of the labels (H34140)
    label_width = 48.0 * mm
    label_height = 25.4 * mm
    
    # Recalculate margins and spacing for 40 labels (4x10)
    num_cols = 4
    num_rows = 10
    col_spacing = 4.0 * mm
    row_spacing = 0.0 * mm # Labels are vertically flush
    
    # Calculate left margin to center the block horizontally
    total_block_width = (num_cols * label_width) + ((num_cols - 1) * col_spacing)
    margin_left = (page_width - total_block_width) / 2
    
    # Calculate top margin
    total_block_height = num_rows * label_height
    margin_top = (page_height - total_block_height) / 2

    # Heights of elements within the label
    barcode_height = 6 * mm
    code_font_size = 6
    price_font_size = 14

    # Vertical spacing between elements
    space_between_barcode_and_code = 1.0 * mm
    space_between_code_and_price = 1.0 * mm

    # Text and font configuration
    c.setFont("Helvetica", code_font_size)

    for i in range(quantity):
        # If the number of labels per page is exceeded, a new one is created
        if i > 0 and i % (num_rows * num_cols) == 0:
            c.showPage()
            c.setFont("Helvetica", code_font_size)

        # Calculate the position of the label on the page
        col = (i % (num_rows * num_cols)) % num_cols
        row = (i % (num_rows * num_cols)) // num_cols
        
        x_base = margin_left + col * (label_width + col_spacing)
        y_base = page_height - margin_top - (row + 1) * (label_height + row_spacing)

        # 1. Draw the barcode at the top of the block
        barcode_obj = code128.Code128(code, barWidth=0.25*mm, barHeight=barcode_height)
        barcode_width = barcode_obj.width
        x_centered_barcode = x_base + (label_width - barcode_width) / 2
        # Y position calculated from the base
        y_barcode = y_base + label_height - (barcode_height + 2 * mm)
        
        barcode_obj.drawOn(c, x_centered_barcode, y_barcode)

        # 2. Draw the alphanumeric code below the barcode
        c.setFont("Helvetica", code_font_size)
        text_width = c.stringWidth(code, "Helvetica", code_font_size)
        x_centered_text = x_base + (label_width - text_width) / 2
        y_text = y_barcode - space_between_barcode_and_code - code_font_size
        
        c.drawString(x_centered_text, y_text, code)
        
        # 3. Draw the price below the alphanumeric code
        c.setFont("Helvetica", price_font_size)
        price_string = f"${int(price):,d}"
        price_string = price_string.replace(",", ".")  # Replace comma with dot for decimal
        price_width = c.stringWidth(price_string, "Helvetica", price_font_size)
        x_centered_price = x_base + (label_width - price_width) / 2
        y_price = y_text - space_between_code_and_price - price_font_size
        
        c.drawString(x_centered_price, y_price, price_string)
        
    c.save()
    buffer.seek(0)
    return buffer

# --- Main Streamlit application logic ---
def main():

    st.title("🧢 CAPPELLO SOMBREROS")
    st.header(f"Generador de Códigos de Barras  vs {VERSION}")
    st.write("Selecciona un artículo de la lista y edita el precio si es necesario.")

    with st.sidebar:
        st.header("⚙️ Configuración")
    
    codes_data = load_codes_from_excel(EXCEL_PATH)
    
    if codes_data:
        selected_item = st.selectbox(
            "Códigos disponibles:", 
            options=codes_data, 
            index=None, 
            placeholder="Selecciona un código...",
            format_func=lambda item: f"{item['code']} - {item['description']}"
        )

        if selected_item:
            selected_code_only = selected_item['code']
            selected_description = selected_item['description']
            
            # st.markdown("---")
            col1, col2 = st.columns([2, 2])
            with col1:
                st.subheader("Código de barras:")
                barcode_image = generate_barcode(selected_code_only)
                if barcode_image:
                    st.image(barcode_image, caption=f"Código: {selected_code_only}", use_container_width=True)
            
            # st.markdown("---")
            st.subheader("Opciones de Impresión")
            
            # Use columns for horizontal layout
            col1, col2 = st.columns(2)

            with col1:
                price_input = st.text_input(
                    "Precio $:", 
                    value=selected_item['price']
                )

            with col2:
                quantity = st.number_input(
                    "Cantidad de etiquetas ( 40 p/página ):",
                    min_value=1,
                    max_value=4000, # Maximum labels per page for H34140
                    value=1,
                    step=1
                )
            
            if st.button("Generar PDF para Imprimir"):
                pdf_buffer = generate_pdf_labels(selected_code_only, price_input, quantity)
                
                if pdf_buffer:
                    st.success("PDF generado con éxito. Descarga tu archivo.")
                    st.download_button(
                        label="Descargar PDF",
                        data=pdf_buffer,
                        file_name=f"etiquetas_{selected_code_only}_{price_input}.pdf",
                        mime="application/pdf"
                    )
    else:
        st.info("No se encontraron códigos o hubo un error al leer el archivo. Por favor, revisa la ruta y el contenido del archivo Excel.")
        
if __name__ == "__main__":
    main()
