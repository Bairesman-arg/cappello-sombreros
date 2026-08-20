# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from sqlalchemy import text
import config
from models import engine

def format_fecha(val):
    """Formatea la fecha a formato DD/MM/YYYY o retorna string vacío si no existe o es nula."""
    if pd.isna(val) or val is None or str(val).strip() in ["", "NaT", "None", "nan"]:
        return ""
    try:
        dt = pd.to_datetime(val)
        if pd.isna(dt):
            return ""
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ""

def get_consultas_df():
    """Consulta la base de datos para obtener el listado completo de remitos."""
    query = text("""
        SELECT 
            r.id AS "Nro. Remito",
            c.boca AS "Nro. Boca",
            c.razon_social AS "Razón Social",
            COALESCE(SUM(ri.entregados), 0) AS "Cant. Artículos",
            r.fecha_entrega AS "Fecha Entrega",
            r.fecha_retiro AS "Fecha Retiro",
            r.porc_dto AS "% Dto",
            r.observaciones AS "Observaciones"
        FROM remitos r
        JOIN clientes c ON r.cliente_id = c.id
        LEFT JOIN remito_items ri ON r.id = ri.remito_id
        GROUP BY r.id, c.boca, c.razon_social, r.fecha_entrega, r.fecha_retiro, r.porc_dto, r.observaciones
        ORDER BY r.id DESC;
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    
    if not df.empty:
        # Asegurar ordenamiento descendente por Nro. Remito
        df = df.sort_values(by="Nro. Remito", ascending=False).reset_index(drop=True)
        
        # Casteo y limpieza de datos
        df["Nro. Remito"] = df["Nro. Remito"].fillna(0).astype(int)
        df["Nro. Boca"] = df["Nro. Boca"].fillna(0).astype(int)
        df["Razón Social"] = df["Razón Social"].fillna("").astype(str)
        df["Cant. Artículos"] = df["Cant. Artículos"].fillna(0).astype(int)
        df["% Dto"] = df["% Dto"].fillna(0.0).astype(float)
        df["Observaciones"] = df["Observaciones"].fillna("").astype(str).replace(["None", "none", "nan", "NaN"], "")
        
        # Formatear fechas como texto DD/MM/YYYY para evitar que aparezca 'None' cuando sean nulas
        df["Fecha Entrega"] = df["Fecha Entrega"].apply(format_fecha)
        df["Fecha Retiro"] = df["Fecha Retiro"].apply(format_fecha)

    return df

def remitos_consultas():
    st.title(config.TITULO_APP)
    st.header("Consulta de Remitos")

    df = get_consultas_df()

    if df.empty:
        st.info("No hay remitos registrados en el sistema.")
    else:
        # Configuración con anchos de píxeles ajustados milimétricamente al título/contenido
        column_config = {
            "Nro. Remito": st.column_config.NumberColumn(
                "Nro. Remito",
                format="%d",
                width=105
            ),
            "Nro. Boca": st.column_config.NumberColumn(
                "Nro. Boca",
                format="%d",
                width=90
            ),
            "Razón Social": st.column_config.TextColumn(
                "Razón Social",
                width=280
            ),
            "Cant. Artículos": st.column_config.NumberColumn(
                "Cant. Artículos",
                format="%d",
                width=135
            ),
            "Fecha Entrega": st.column_config.TextColumn(
                "Fecha Entrega",
                width=120
            ),
            "Fecha Retiro": st.column_config.TextColumn(
                "Fecha Retiro",
                width=115
            ),
            "% Dto": st.column_config.NumberColumn(
                "% Dto",
                format="%.0f%%",
                width=70
            ),
            "Observaciones": st.column_config.TextColumn(
                "Observaciones",
                width=300
            ),
        }

        # Calcular altura dinámica de la grilla (hasta 10 filas)
        num_rows = len(df)
        rows_to_show = min(max(num_rows, 1), 10)
        grid_height = int(39 + (rows_to_show * 35.5) + 4)

        st.dataframe(
            df,
            column_config=column_config,
            hide_index=True,
            width="content",
            height=grid_height
        )

    # Footer
    st.markdown(f"`{config.FOOTER_APP}`")

if __name__ == "__main__":
    remitos_consultas()
