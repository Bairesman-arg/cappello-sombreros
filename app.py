# -*- coding: utf-8 -*-
"""
Script de Streamlit para leer códigos desde una hoja de cálculo de Excel,
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

# --- Variables de configuración ---
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "DOCS", "ARTICULOS.xlsm")

def load_codes_from_excel(excel_file_path):
    """
    Reads codes from columns A and B of the Excel spreadsheet.
    Returns a list of dictionaries, where each dictionary contains
    the code and the description.
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
            
            if cell_value is None:
                break
            
            codes_data.append({
                "code": str(cell_value),
                "description": str(cell_descrip) if cell_descrip is not None else ""
            })
        
        return codes_data
        
    except Exception as e:
        st.error(f"Ocurrió un error al leer el archivo de Excel: {e}")
        return []

def generate_barcode(code_to_generate: str):
    """
    Generates a barcode (Code128) from a text string
    and returns the image in a format that Streamlit can display.
    """
    try:
        code128_obj = barcode.get("code128", code_to_generate, writer=ImageWriter())
        buffer = io.BytesIO()
        options = {
            "module_height": 1.5,
            "quiet_zone": 2,
            "font_size": 5,
            "text_distance": 3
        }
        code128_obj.write(buffer, options)
        buffer.seek(0)
        
        pil_image = Image.open(buffer)
        return pil_image
            
    except Exception as e:
        st.error(f"Error al generar el código de barras: {e}")
        return None

def generate_pdf_labels(code: str, description: str, quantity: int):
    """
    Generates a PDF file with barcode labels
    in a 13-row by 5-column format.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # A4 page dimensions in millimeters
    page_width, page_height = A4

    # Label dimensions and spacing (H34165)
    label_width = 38.1 * mm
    label_height = 21.2 * mm
    
    # Recalculated margin to center the entire block of labels
    # (page_width - (5 * label_width + 4 * col_spacing)) / 2
    col_spacing = 3.6 * mm
    margin_left = (page_width - (5 * label_width + 4 * col_spacing)) / 2
    
    margin_top = 15.3 * mm
    row_spacing = 0.5 * mm
    
    # Dimensions of the elements to be centered
    barcode_height = 6 * mm
    # Adjusted font size to fit the code on the label
    font_size = 6
    font_name = "Helvetica"
    
    # Increased vertical space between the barcode and the text
    vertical_space_between_elements = 2.5 * mm

    # Text height calculation (approximate)
    text_height = font_size * 0.35 * mm # A rough estimate based on font size

    # Configuration of text and font
    c.setFont(font_name, font_size)

    for i in range(quantity):
        # If the number of labels per page is exceeded, a new page is created
        if i > 0 and i % (13 * 5) == 0:
            c.showPage()
            c.setFont(font_name, font_size)

        # Calculate the label's position on the page
        col = (i % (13 * 5)) % 5
        row = (i % (13 * 5)) // 5
        
        # Coordinates of the bottom-left corner of the label space
        x_base = margin_left + col * (label_width + col_spacing)
        y_base = page_height - margin_top - (row + 1) * (label_height + row_spacing)

        # Calculate the Y position for the complete block (barcode + text)
        y_center_of_label = y_base + (label_height / 2)
        total_block_height = barcode_height + vertical_space_between_elements + text_height

        # 1. Draw the alphanumeric text
        text_width = c.stringWidth(code, font_name, font_size)
        x_centered_text = x_base + (label_width - text_width) / 2
        y_text = y_center_of_label - (total_block_height / 2)
        
        c.drawString(x_centered_text, y_text, code)

        # 2. Draw the barcode above the text
        barcode_obj = code128.Code128(code, barWidth=0.25*mm, barHeight=barcode_height)
        barcode_width = barcode_obj.width
        x_centered_barcode = x_base + (label_width - barcode_width) / 2
        
        # The barcode position is above the text with the desired spacing
        y_barcode = y_text + text_height + vertical_space_between_elements
        
        barcode_obj.drawOn(c, x_centered_barcode, y_barcode)
        
    c.save()
    buffer.seek(0)
    return buffer

# --- Main Streamlit application logic ---
def main():
    st.title("🧢 Capello S")
    st.header("Generador de Códigos de Barras")
    st.write("Selecciona un código de la lista y se generará un código de barras.")

    with st.sidebar:
        st.header("⚙️ Configuración")
    
    codes_and_desc = load_codes_from_excel(EXCEL_PATH)
    
    if codes_and_desc:
        selected_item = st.selectbox(
            "Códigos disponibles:", 
            options=codes_and_desc, 
            index=None, 
            placeholder="Selecciona un código...",
            format_func=lambda item: f"{item['code']} - {item['description']}"
        )
        
        if selected_item:
            selected_code_only = selected_item['code']
            selected_description = selected_item['description']
            
            st.markdown("---")
            col1, col2 = st.columns([2, 2])
            with col1:
                st.subheader("Código de barras:")
                barcode_image = generate_barcode(selected_code_only)
                if barcode_image:
                    st.image(barcode_image, caption=f"Código: {selected_code_only}", use_container_width=True)
            
            # st.markdown("---")
            
            st.subheader("Impresión")
            # The user can choose how many labels to print

            col1, col2 = st.columns([2, 2])
            with col1:
                quantity = st.number_input(
                    "Cantidad de etiquetas a imprimir:",
                    min_value=1,
                    max_value=65, # Maximum labels per page
                    value=1,
                    step=1
                )
            
                if st.button("Generar PDF para Imprimir"):
                    pdf_buffer = generate_pdf_labels(selected_code_only, selected_description, quantity)
                    
                    if pdf_buffer:
                        st.success("PDF generado con éxito. Descarga tu archivo.")
                        st.download_button(
                            label="Descargar PDF",
                            data=pdf_buffer,
                            file_name=f"etiquetas_{selected_code_only}.pdf",
                            mime="application/pdf"
                        )
    else:
        st.info("No se encontraron códigos o hubo un error al leer el archivo. Por favor, revisa la ruta y el contenido del archivo Excel.")
        
if __name__ == "__main__":
    main()
