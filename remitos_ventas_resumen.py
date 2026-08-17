import streamlit as st
import pandas as pd
import config

def remitos_ventas_resumen(remito_id, cab, df_items):
    """Muestra una vista resumen informativa y no editable del remito en su estado actual (Remito en Edición)."""
    st.markdown("<div id='resumen_top_anchor'></div>", unsafe_allow_html=True)
    st.components.v1.html(
        """
        <script>
            (function() {
                function scrollToTop() {
                    const doc = window.parent.document;
                    if (!doc) return;
                    const el = doc.getElementById('resumen_top_anchor');
                    if (el) {
                        el.scrollIntoView({ behavior: 'auto', block: 'start' });
                    }
                    const containers = doc.querySelectorAll('[data-testid="stMain"], section.main, [data-testid="stAppViewContainer"]');
                    containers.forEach(c => { c.scrollTop = 0; });
                    if (doc.documentElement) doc.documentElement.scrollTop = 0;
                    if (doc.body) doc.body.scrollTop = 0;
                    window.parent.scrollTo(0, 0);
                }
                setTimeout(scrollToTop, 10);
                setTimeout(scrollToTop, 100);
                setTimeout(scrollToTop, 300);
            })();
        </script>
        """,
        height=0,
    )

    st.title(f"Capello {config.VERSION}")
    st.header("📄 Remito en Edición")

    # Subtítulo de Cabecera
    razon_social = cab.get("razon_social", "")
    boca = cab.get("boca", "")
    st.subheader(f"#{remito_id}  |  Cliente: {razon_social} (Boca {boca})")

    # Formateo de Fechas
    f_entrega = cab.get("fecha_entrega")
    f_entrega_str = f_entrega.strftime("%d/%m/%Y") if hasattr(f_entrega, "strftime") else (str(f_entrega) if f_entrega else "-")

    is_rec_dia = bool(st.session_state.get(f"recepcion_el_dia_{remito_id}", False))
    f_retiro = None if is_rec_dia else (st.session_state.get(f"f_ret_m_{remito_id}") or cab.get("fecha_retiro"))

    if is_rec_dia:
        f_retiro_str = "Recepción en el Día"
    elif f_retiro:
        f_retiro_str = f_retiro.strftime("%d/%m/%Y") if hasattr(f_retiro, "strftime") else str(f_retiro)
    else:
        f_retiro_str = ""

    obs_cabecera = cab.get("observaciones") or ""

    # Fichas Informativas de Fechas con Letra Blanca (sin azul st.info)
    st.markdown(
        f"""
        <div style="display: flex; gap: 10px; margin-top: 0.5rem; margin-bottom: 12px;">
            <div style="flex: 1; background-color: #262730; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #00C853;">
                <div style="color: #ffffff; font-size: 0.85rem; font-weight: 500;">Fecha de Entrega</div>
                <div style="color: #ffffff; font-size: 1.05rem; font-weight: 700; margin-top: 2px;">{f_entrega_str}</div>
            </div>
            <div style="flex: 1; background-color: #262730; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #FF9800;">
                <div style="color: #ffffff; font-size: 0.85rem; font-weight: 500;">Fecha de Retiro</div>
                <div style="color: #ffffff; font-size: 1.05rem; font-weight: 700; margin-top: 2px;">{f_retiro_str if f_retiro_str else "-"}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f"**Observaciones del Remito:** {obs_cabecera if obs_cabecera else '*Sin observaciones*'}")

    # --- Grilla Informativa de Artículos ---
    st.subheader("Detalle de Artículos")
    if not df_items.empty:
        resumen_df = pd.DataFrame()
        resumen_df["Art."] = df_items["nro_articulo"].astype(str)
        resumen_df["Descripción"] = df_items["descripcion"].astype(str)
        resumen_df["Precio Real"] = df_items["precio_real"].apply(lambda x: f"$ {float(x):,.2f}")
        resumen_df["Entregados"] = df_items["entregados"].astype(int)
        resumen_df["Devueltos"] = df_items["devueltos"].astype(int)
        resumen_df["Vendidos"] = (df_items["entregados"].astype(int) - df_items["devueltos"].astype(int)).apply(lambda x: max(0, x))
        resumen_df["Observaciones"] = df_items["observaciones"].fillna("").astype(str)

        st.dataframe(
            resumen_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("⚠️ No hay artículos cargados en el remito.")

    st.divider()

    # --- Totales (Grilla y Utilidad Estimada debajo) ---
    st.subheader("Totales")
    if not df_items.empty:
        t_ent = int(df_items["entregados"].sum())
        t_dev = int(df_items["devueltos"].sum())
        t_vend = max(0, t_ent - t_dev)

        porc_dto_val = float(cab.get("porc_dto", 0) or 0)
        utilidades = []
        for idx in df_items.index:
            pr = float(df_items.loc[idx, "precio_real"])
            co = float(df_items.loc[idx, "costo"])
            ve = max(0, int(df_items.loc[idx, "entregados"]) - int(df_items.loc[idx, "devueltos"]))
            if pr > 0 and ve > 0:
                p_dto = pr * (1.0 - (porc_dto_val / 100.0))
                utilidades.append((p_dto - co) * ve)
            else:
                utilidades.append(0.0)
        t_util = float(sum(utilidades))
    else:
        t_ent = t_dev = t_vend = 0
        t_util = 0.0

    # Grilla de Totales
    totales_df = pd.DataFrame([{
        "Entregados": t_ent,
        "Devueltos": t_dev,
        "Vendidos": t_vend
    }])
    st.dataframe(totales_df, use_container_width=True, hide_index=True)

    # Utilidad Estimada debajo de la grilla
    st.metric("Utilidad Estimada", f"$ {t_util:,.2f}")

    # Botón de Cerrar Resúmen
    if st.button("Cerrar Resúmen", type="primary", width="stretch"):
        st.session_state.show_resumen_movil = False
        st.components.v1.html(
            """
            <script>
                (function() {
                    function scrollToTop() {
                        const doc = window.parent.document;
                        if (!doc) return;
                        const el = doc.getElementById('movil_top_anchor');
                        if (el) {
                            el.scrollIntoView({ behavior: 'auto', block: 'start' });
                        }
                        const containers = doc.querySelectorAll('[data-testid="stMain"], section.main, [data-testid="stAppViewContainer"]');
                        containers.forEach(c => { c.scrollTop = 0; });
                        if (doc.documentElement) doc.documentElement.scrollTop = 0;
                        if (doc.body) doc.body.scrollTop = 0;
                        window.parent.scrollTo(0, 0);
                    }
                    setTimeout(scrollToTop, 10);
                    setTimeout(scrollToTop, 100);
                })();
            </script>
            """,
            height=0,
        )
        st.rerun()
