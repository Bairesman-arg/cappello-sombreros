# -*- coding: utf-8 -*-
"""
Script de Streamlit para leer códigos y precios desde una hoja de cálculo de Excel,
mostrarlos en una lista desplegable, generar un código de barras
estándar (Code128) del elemento seleccionado y crear un PDF de etiquetas,
con una estructura de navegación en el sidebar.
"""
import streamlit as st
import pandas as pd
import openpyxl
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

VERSION = "1.0.7"

# --- Variables de configuración ---
EXCEL_PATH = os.path.join(os.path.dirname(__file__), "DOCS", "ARTICULOS.xlsm")

st.set_page_config(
    page_title="Generador de Etiquetas",
    layout="wide"
)

# Configuración de locale para el formato de moneda en español
try:
    locale.setlocale(locale.LC_ALL, 'es_ES.UTF-8')
except locale.Error:
    # Fallback para sistemas que no tienen es_ES.UTF-8
    locale.setlocale(locale.LC_ALL, '')

# --- Funciones de utilidad ---

def load_codes_from_excel(excel_file_path):
    """
    Lee códigos desde las columnas A y B, y precios desde la columna C de la
    hoja de cálculo de Excel. Retorna una lista de diccionarios.
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
    Genera un archivo PDF con etiquetas de código de barras en formato
    10 filas por 4 columnas (H34140).
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    
    # Dimensiones de la hoja A4 en milímetros
    page_width, page_height = A4

    # Dimensiones y espaciado de las etiquetas (H34140)
    label_width = 48.0 * mm
    label_height = 25.4 * mm
    
    num_cols = 4
    num_rows = 10
    col_spacing = 4.0 * mm
    row_spacing = 0.0 * mm 
    
    total_block_width = (num_cols * label_width) + ((num_cols - 1) * col_spacing)
    margin_left = (page_width - total_block_width) / 2
    
    total_block_height = num_rows * label_height
    margin_top = (page_height - total_block_height) / 2

    barcode_height = 6 * mm
    code_font_size = 6
    price_font_size = 14

    space_between_barcode_and_code = 1.0 * mm
    space_between_code_and_price = 1.0 * mm

    c.setFont("Helvetica", code_font_size)

    for i in range(quantity):
        if i > 0 and i % (num_rows * num_cols) == 0:
            c.showPage()
            c.setFont("Helvetica", code_font_size)

        col = (i % (num_rows * num_cols)) % num_cols
        row = (i % (num_rows * num_cols)) // num_cols
        
        x_base = margin_left + col * (label_width + col_spacing)
        y_base = page_height - margin_top - (row + 1) * (label_height + row_spacing)

        # 1. Dibujar el código de barras
        barcode_obj = code128.Code128(code, barWidth=0.25*mm, barHeight=barcode_height)
        barcode_width = barcode_obj.width
        x_centered_barcode = x_base + (label_width - barcode_width) / 2
        y_barcode = y_base + label_height - (barcode_height + 2 * mm)
        
        barcode_obj.drawOn(c, x_centered_barcode, y_barcode)

        # 2. Dibujar el código alfanumérico
        c.setFont("Helvetica", code_font_size)
        text_width = c.stringWidth(code, "Helvetica", code_font_size)
        x_centered_text = x_base + (label_width - text_width) / 2
        y_text = y_barcode - space_between_barcode_and_code - code_font_size
        
        c.drawString(x_centered_text, y_text, code)
        
        # 3. Dibujar el precio
        c.setFont("Helvetica", price_font_size)

        # Formatear el precio con punto
        price_string = f"${int(price):,d}"
        price_string = price_string.replace(",", ".")

        price_width = c.stringWidth(price_string, "Helvetica", price_font_size)
        x_centered_price = x_base + (label_width - price_width) / 2
        y_price = y_text - space_between_code_and_price - price_font_size
        
        c.drawString(x_centered_price, y_price, price_string)
            
    c.save()
    buffer.seek(0)
    return buffer

# --- Lógica de las páginas de la aplicación ---

def main_page():

    # col1, col2 = st.columns([6, 1])
    # with col2:
    #    st.image("C:\WORKS\CAPELLO SOMBREROS\APPLICATION\IMAGES\Cappello_Logo.png",width=100, use_container_width=True)

    st.title("🧢 CAPPELLO SOMBREROS")
    st.header(f"Generador de Códigos de Barras vs {VERSION}")

    codes_data = load_codes_from_excel(EXCEL_PATH)
    
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
            
            col1, col2 = st.columns([2, 2])
            with col1:
                st.subheader("Código de barras:")
                barcode_image = generate_barcode(selected_code_only)
                if barcode_image:
                    st.image(barcode_image, caption=f"Código: {selected_code_only}", use_container_width=True)
            
            st.subheader("Opciones de Impresión")
            
            col1, col2, col3 = st.columns(3)

            with col1:
                price_input = st.text_input(
                    "Precio $:", 
                    value=selected_item['price']
                )

            with col2:
                quantity = st.number_input(
                    "Cantidad de etiquetas (40 p/página):",
                    min_value=1,
                    max_value=4000,
                    value=40,
                    step=1
                )

            if st.button("Generar PDF para Imprimir",):
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
        
# Puedes agregar más funciones para otras páginas aquí
def update_art():

    st.title("Subir archivo de artículos")
    st.markdown("---")

    # Muestra instrucciones al usuario
    st.info("Por favor, suba el archivo de Excel (.xlsm) con el formato de artículos.")

    # Widget para la carga de archivos
    uploaded_file = st.file_uploader(
        "Seleccione un archivo de Excel",
        type=['xlsm'],
        help="Solo se aceptan archivos con la extensión .xlsm"
    )

    # Verifica si se ha subido un archivo
    if uploaded_file is not None:
        try:
            # Crea la ruta de la carpeta 'DOCS'
            # os.getcwd() obtiene el directorio de trabajo actual (donde esta el script)
            docs_folder = os.path.join(os.getcwd(), 'DOCS')

            # Crea la carpeta 'DOCS' si no existe
            os.makedirs(docs_folder, exist_ok=True)
            
            # Define el nombre del archivo de destino
            file_path = os.path.join(docs_folder, 'ARTICULOS.xlsm')
            
            # Guarda el archivo en la carpeta 'DOCS'
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"¡Archivo '{uploaded_file.name}' guardado correctamente como 'ARTICULOS.xlsm'!")

            # Opcional: Mostrar los primeros registros del Excel
            # Esta parte solo es para verificar, puedes eliminarla si no la necesitas
            # st.markdown("---")
            st.subheader("Vista previa del archivo cargado")

            # Lee el archivo guardado, indicando que los encabezados están en la segunda fila (índice 1)
            df = pd.read_excel(file_path, header=1)

            # Asegura que la tercera columna (índice 2) sea de tipo entero
            # Primero convierte a numérico, maneja errores y luego rellena los nulos con 0 para poder convertirlos a enteros
            df.iloc[:, 2] = pd.to_numeric(df.iloc[:, 2], errors='coerce').fillna(0).astype(int)

            # Crea una copia del DataFrame para la visualización
            df_display = df.head(10).copy()

            # Aplica el formato de moneda a la tercera columna en el DataFrame de visualización
            df_display.iloc[:, 2] = df_display.iloc[:, 2].apply(lambda x: f"${x:,.0f}")
            
            # Muestra las 10 primeras filas del DataFrame
            st.dataframe(df_display, hide_index=True)
            
        except Exception as e:
            st.error(f"Ocurrió un error al guardar el archivo: {e}")





















# --- Main application logic with navigation ---

def app():
    # Definir las páginas disponibles
    PAGES = {
        "Generación de Códigos de Barra": main_page,
        "Actualización de Artículos": update_art
        # Puedes agregar más páginas aquí:
        # "Otra Página": another_page,
    }

    # Crear el sidebar con navegación
    with st.sidebar:
        st.header("Menú")
        selected_page = st.radio(
            "",
            list(PAGES.keys())
        )

    # Llamar a la función de la página seleccionada
    PAGES[selected_page]()

if __name__ == "__main__":
    app()
