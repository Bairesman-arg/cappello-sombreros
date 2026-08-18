# -*- coding: utf-8 -*-
import datetime
import calendar
import pandas as pd
import streamlit as st
from sqlalchemy import text
from models import engine
import io
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Border, Side
import config

MESES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

def generar_excel_ganancias(agrupado, total_articulos_mes, total_utilidad_mes):
    output = io.BytesIO()
    df_excel = pd.DataFrame({
        "Fecha": agrupado["Fecha"],
        "Artículos Vendidos": agrupado["Artículos Vendidos"],
        "Utilidad ($)": agrupado["utilidad_dia"].round(2)
    })
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_excel.to_excel(writer, index=False, sheet_name="Ganancias por Día")
        ws = writer.sheets["Ganancias por Día"]
        
        # Estilos openpyxl
        header_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid") # Amarillo pastel tenue
        bold_font = Font(bold=True)

        # Aplicar estilo al encabezado (Fila 1)
        for col_idx in range(1, 4):
            cell = ws.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = bold_font

        # Formatear datos
        for row in range(2, len(df_excel) + 2):
            cell_util = ws.cell(row=row, column=3)
            cell_util.number_format = '"$"#,##0.00'
            cell_art = ws.cell(row=row, column=2)
            cell_art.number_format = '#,##0'
        
        # Fila final de Totales en Negrita
        tot_row = len(df_excel) + 3
        c1 = ws.cell(row=tot_row, column=1, value="Total del Mes")
        c2 = ws.cell(row=tot_row, column=2, value=total_articulos_mes)
        c2.number_format = '#,##0'
        c3 = ws.cell(row=tot_row, column=3, value=total_utilidad_mes)
        c3.number_format = '"$"#,##0.00'

        top_border = Border(top=Side(style='thin'))
        for c in (c1, c2, c3):
            c.font = bold_font
            c.border = top_border
        
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 5, 18)
            
    return output.getvalue()

def info_ganancias_dia():
    st.header("Informes - Ganancias por Día")
    st.markdown('<div style="font-size: 0.85rem; color: #00E676; font-weight: 500; margin-top: -0.4rem; margin-bottom: 0.8rem;">El Análisis Gráfico se encuentra al final de la página</div>', unsafe_allow_html=True)
    st.markdown("---")

    # Fecha actual para predeterminar la selección
    today = datetime.date.today()
    current_year = today.year
    current_month = today.month

    # Controles de selección de Mes y Año
    col_mes, col_anio, _ = st.columns([2, 2, 4], gap="small")
    
    with col_mes:
        mes_nombre = st.selectbox(
            "Mes",
            options=MESES,
            index=current_month - 1,
            key="info_ganancias_mes"
        )
        mes_num = MESES.index(mes_nombre) + 1

    with col_anio:
        anios_disponibles = list(range(2026, 2051))
        index_anio = anios_disponibles.index(current_year) if current_year in anios_disponibles else 0
        anio_num = st.selectbox(
            "Año",
            options=anios_disponibles,
            index=index_anio,
            key="info_ganancias_anio"
        )

    # Rango de fechas del mes completo seleccionado
    _, ult_dia = calendar.monthrange(anio_num, mes_num)
    fecha_inicio = datetime.date(anio_num, mes_num, 1)
    fecha_fin = datetime.date(anio_num, mes_num, ult_dia)

    # Consulta a base de datos de remitos con fecha_retiro en el mes seleccionado
    try:
        with engine.begin() as conn:
            query = text("""
                SELECT 
                    r.id AS remito_id,
                    r.fecha_retiro,
                    COALESCE(r.porc_dto, c.porc_dto, 0) AS porc_dto,
                    ri.entregados,
                    COALESCE(ri.devueltos, 0) AS devueltos,
                    COALESCE(ri.precio_real_item, a.precio_real, 0) AS precio_real,
                    COALESCE(a.costo, 0) AS costo
                FROM remitos r
                JOIN clientes c ON r.cliente_id = c.id
                JOIN remito_items ri ON r.id = ri.remito_id
                JOIN articulos a ON ri.articulo_id = a.id
                WHERE r.fecha_retiro IS NOT NULL 
                  AND r.fecha_retiro >= :start_date 
                  AND r.fecha_retiro <= :end_date
                ORDER BY r.fecha_retiro ASC
            """)
            df_raw = pd.read_sql(query, conn, params={"start_date": fecha_inicio, "end_date": fecha_fin})
    except Exception as e:
        st.error(f"Error al consultar la base de datos: {e}")
        return

    if df_raw.empty:
        st.info(f"ℹ️ No existen Remitos con ventas registradas en {mes_nombre} {anio_num}.")
        st.metric("Total Utilidad del Mes", "$ 0.00")
        return

    # Asegurar conversión de fecha a date
    df_raw["fecha_retiro_dt"] = pd.to_datetime(df_raw["fecha_retiro"]).dt.date

    # Aplicar cálculo de vendidos y utilidad ítem por ítem
    def calcular_item(row):
        entregados = int(row["entregados"]) if pd.notna(row["entregados"]) else 0
        devueltos = int(row["devueltos"]) if pd.notna(row["devueltos"]) else 0
        vendidos = max(0, entregados - devueltos)

        p_real = float(row["precio_real"]) if pd.notna(row["precio_real"]) else 0.0
        porc_dto = float(row["porc_dto"]) if pd.notna(row["porc_dto"]) else 0.0
        costo = float(row["costo"]) if pd.notna(row["costo"]) else 0.0

        if p_real > 0 and vendidos > 0:
            p_dto = p_real * (1.0 - (porc_dto / 100.0))
            utilidad = (p_dto - costo) * vendidos
        else:
            utilidad = 0.0

        return pd.Series({"vendidos": vendidos, "utilidad": utilidad})

    res_items = df_raw.apply(calcular_item, axis=1)
    df_raw["vendidos"] = res_items["vendidos"]
    df_raw["utilidad"] = res_items["utilidad"]

    # Agrupar por fecha_retiro cronológicamente
    agrupado = df_raw.groupby("fecha_retiro_dt").agg(
        cant_articulos=("vendidos", "sum"),
        utilidad_dia=("utilidad", "sum")
    ).reset_index()

    agrupado = agrupado.sort_values(by="fecha_retiro_dt", ascending=True)

    # Formatear columnas para la grilla
    agrupado["Fecha"] = agrupado["fecha_retiro_dt"].apply(lambda d: d.strftime("%d/%m/%Y"))
    agrupado["Artículos Vendidos"] = agrupado["cant_articulos"].astype(int)
    agrupado["Utilidad ($)"] = agrupado["utilidad_dia"].round(2)

    df_grilla = agrupado[["Fecha", "Artículos Vendidos", "Utilidad ($)"]]

    # Configuración de columnas en Streamlit dataframe
    column_cfg = {
        "Fecha": st.column_config.TextColumn("Fecha (DD/MM/AAAA)"),
        "Artículos Vendidos": st.column_config.NumberColumn("Artículos Vendidos"),
        "Utilidad ($)": st.column_config.NumberColumn("Utilidad ($)"),
    }

    st.dataframe(
        df_grilla.style.format({
            "Utilidad ($)": "$ {:,.2f}",
            "Artículos Vendidos": "{:d}"
        }),
        use_container_width=True,
        hide_index=True,
        column_config=column_cfg
    )

    # Totales del mes
    total_utilidad_mes = float(agrupado["utilidad_dia"].sum())
    total_articulos_mes = int(agrupado["Artículos Vendidos"].sum())

    m_col0, m_col1, m_col2 = st.columns([1.5, 1, 1], gap="small")

    with m_col0:
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        excel_bytes = generar_excel_ganancias(agrupado, total_articulos_mes, total_utilidad_mes)
        filename_excel = f"info_ganancias_{anio_num:04d}{mes_num:02d}.xlsx"
        st.download_button(
            label="📊 Exportar a Excel",
            data=excel_bytes,
            file_name=filename_excel,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="btn_download_info_ganancias"
        )

    with m_col1:
        st.markdown(f"""
        <div style="text-align: right; width: 100%;">
            <div style="font-size: 0.875rem; color: rgba(250, 250, 250, 0.7); font-weight: 400; margin-bottom: 4px;">Total Artículos Vendidos en el Mes</div>
            <div style="font-size: 2rem; font-weight: 600; color: var(--text-color, #ffffff); line-height: 1.2;">{total_articulos_mes:,}</div>
        </div>
        """, unsafe_allow_html=True)

    with m_col2:
        st.markdown(f"""
        <div style="text-align: right; width: 100%;">
            <div style="font-size: 0.875rem; color: rgba(250, 250, 250, 0.7); font-weight: 400; margin-bottom: 4px;">Total Utilidad del Mes</div>
            <div style="font-size: 2rem; font-weight: 600; color: var(--text-color, #ffffff); line-height: 1.2;">$ {total_utilidad_mes:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # === SECCIÓN DE GRÁFICOS VISUALES ===
    st.markdown("---")
    st.subheader("📊 Análisis Gráfico del Mes")

    import altair as alt

    df_chart = agrupado.copy()
    df_chart["utilidad_fmt"] = df_chart["utilidad_dia"].apply(lambda v: f"$ {v:,.2f}")
    df_chart["utilidad_acum"] = df_chart["utilidad_dia"].cumsum()
    df_chart["utilidad_acum_fmt"] = df_chart["utilidad_acum"].apply(lambda v: f"$ {v:,.2f}")

    tab_g1, tab_g2, tab_g3 = st.tabs([
        "💰 Utilidad Diaria ($)", 
        "📦 Artículos Vendidos", 
        "📈 Evolución Acumulada ($)"
    ])

    with tab_g1:
        chart_util = alt.Chart(df_chart).mark_bar(
            cornerRadiusTopLeft=5,
            cornerRadiusTopRight=5,
            color="#ff4b4b"
        ).encode(
            x=alt.X("Fecha:N", title="Fecha (DD/MM/AAAA)", sort=None),
            y=alt.Y("utilidad_dia:Q", title="Utilidad ($)"),
            tooltip=[
                alt.Tooltip("Fecha:N", title="Fecha"),
                alt.Tooltip("utilidad_fmt:N", title="Utilidad ($)"),
                alt.Tooltip("cant_articulos:Q", title="Artículos Vendidos")
            ]
        ).properties(
            height=340
        )
        st.altair_chart(chart_util, use_container_width=True)

    with tab_g2:
        chart_cant = alt.Chart(df_chart).mark_bar(
            cornerRadiusTopLeft=5,
            cornerRadiusTopRight=5,
            color="#00c49f"
        ).encode(
            x=alt.X("Fecha:N", title="Fecha (DD/MM/AAAA)", sort=None),
            y=alt.Y("cant_articulos:Q", title="Artículos Vendidos"),
            tooltip=[
                alt.Tooltip("Fecha:N", title="Fecha"),
                alt.Tooltip("cant_articulos:Q", title="Artículos Vendidos"),
                alt.Tooltip("utilidad_fmt:N", title="Utilidad ($)")
            ]
        ).properties(
            height=340
        )
        st.altair_chart(chart_cant, use_container_width=True)

    with tab_g3:
        chart_acum_line = alt.Chart(df_chart).mark_area(
            color=alt.Gradient(
                gradient='linear',
                stops=[alt.GradientStop(color='#1e88e5', offset=1), alt.GradientStop(color='rgba(30, 136, 229, 0.1)', offset=0)],
                x1=1, x2=1, y1=1, y2=0
            ),
            line={'color': '#29b6f6', 'strokeWidth': 2}
        ).encode(
            x=alt.X("Fecha:N", title="Fecha (DD/MM/AAAA)", sort=None),
            y=alt.Y("utilidad_acum:Q", title="Utilidad Acumulada ($)"),
            tooltip=[
                alt.Tooltip("Fecha:N", title="Fecha"),
                alt.Tooltip("utilidad_acum_fmt:N", title="Utilidad Acumulada ($)"),
                alt.Tooltip("utilidad_fmt:N", title="Utilidad del Día")
            ]
        ).properties(
            height=340
        )
        st.altair_chart(chart_acum_line, use_container_width=True)

    st.markdown(f"`{config.FOOTER_APP}`")
