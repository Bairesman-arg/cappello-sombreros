import os
import io
import streamlit as st
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook
from models import get_remito_completo

def gen_remito(remito_id: int, is_retiro=False) -> io.BytesIO:
    """
    Genera un archivo Excel del remito usando la plantilla REMITO_Master.xls
    y devuelve un buffer listo para descargar.
    """
    # Obtener datos desde BD
    data = get_remito_completo(remito_id)
    if not data:
        raise ValueError("Remito no encontrado")

    cab = data["cabecera"]
    items = data["items"]

    # Cargar plantilla
    template_path = os.path.join(os.path.dirname(__file__), "DOCS", "REMITO_Master.xlsx")
    wb = load_workbook(template_path)
    ws = wb.active

    # --- Cabecera ---
    ws["A3"] = st.secrets["DIRECCION_CLIENTE"]
    ws["A5"] = cab["razon_social"]
    ws["H5"] = cab["boca"] or ""
    ws["H8"] = "Nro." + f'{remito_id:05d}'
    ws["A6"] = f"{cab['direccion'] or ''} - {cab['localidad'] or ''}"
    ws["G6"] = cab["telefono"] or ""
    if not is_retiro:  # Solo cuando se genera el Remito (1ra. vez)
        ws["H2"] = cab["porc_dto"] / 100 if cab["porc_dto"] else 1

    # --- Items ---
    base_row = 10
    for i, row in items.iterrows():
        ws[f"A{base_row+i}"] = row["nro_articulo"]
        ws[f"B{base_row+i}"] = row["descripcion"]
        ws[f"D{base_row+i}"] = float(row["precio_real"])
        ws[f"E{base_row+i}"] = int(row["entregados"])
        if is_retiro:
            ws[f"F{base_row+i}"] = int(row["devueltos"])
            ws[f"G{base_row+i}"] = int(row["entregados"]-row["devueltos"])
            ws[f"H{base_row+i}"] = row["observaciones"]

    # --- Fecha de entrega ---
    fecha = pd.to_datetime(cab["fecha_entrega"])
    ws["E45"] = fecha.day
    ws["F45"] = fecha.month
    ws["G45"] = fecha.year % 100

    # --- Fecha Retiro ---
    if is_retiro:
        fecha = pd.to_datetime(cab["fecha_retiro"]) #--
        ws["E46"] = fecha.day
        ws["F46"] = fecha.month
        ws["G46"] = fecha.year % 100

    # Guardar en memoria
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return output
