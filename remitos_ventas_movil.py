import streamlit as st
import pandas as pd
from datetime import date, datetime
from models import get_remito_completo, update_remito_data, get_clients_and_articles
from gen_remito import gen_remito, process_generate_remito, is_local_app, get_remito_filename
import config

def clear_item_inputs_rec_movil():
    """Reinicia los valores de los inputs de items para recepciones móviles."""
    st.session_state.entregados_input_rec_movil = 1
    st.session_state.observaciones_item_input_rec_movil = ""
    st.session_state.articulo_precargado_rec_movil = None
    st.session_state.precio_real_input_rec_movil = 0.0
    st.session_state.articulo_selectbox_rec_movil = None

def remitos_ventas_movil():
    try:
        st.set_page_config(page_title="Recepción Móvil - Capello Sombreros", layout="wide", initial_sidebar_state="collapsed")
    except Exception:
        pass

    # CSS de optimización móvil (Touch friendly & Sidebar Hidden)
    st.markdown("""
    <style>
    /* Ocultar sidebar principal para vista móvil limpia a pantalla completa */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    header[data-testid="stHeader"] {
        display: none !important;
    }
    /* Estilos responsive y botones grandes para celulares */
    .stButton button {
        min-height: 44px !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    .stNumberInput input {
        font-size: 0.95rem !important;
        padding: 0.2rem 0.4rem !important;
        height: 38px !important;
        min-height: 38px !important;
        text-align: center !important;
    }
    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label {
        font-size: 0.82rem !important;
        margin-bottom: 0.1rem !important;
    }
    div[data-testid="stNumberInput"] button {
        height: 38px !important;
        min-height: 38px !important;
    }
    div[data-testid="stTextInput"] input {
        font-size: 0.95rem !important;
        padding: 0.2rem 0.4rem !important;
        height: 38px !important;
        min-height: 38px !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }
    .header-sub-text {
        font-size: 1.05rem;
        font-weight: 600;
        color: #e0e0e0;
        margin-top: 0.3rem;
        margin-bottom: 0.8rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Si el usuario solicitó la vista informativa del resumen, se renderiza arriba de todo a pantalla completa
    if st.session_state.get("show_resumen_movil", False) and "remito_activo_rec_movil" in st.session_state:
        remito_id = st.session_state["remito_activo_rec_movil"]
        cab_key = f"remito_rec_movil_{remito_id}_cab"
        items_key = f"remito_rec_movil_{remito_id}_items"
        if cab_key in st.session_state and items_key in st.session_state:
            cab = st.session_state[cab_key]
            df_items_curr = st.session_state[items_key]
            from remitos_ventas_resumen import remitos_ventas_resumen
            remitos_ventas_resumen(remito_id, cab, df_items_curr)
            return

    st.markdown("<div id='movil_top_anchor'></div>", unsafe_allow_html=True)
    st.title(f"Capello {config.VERSION}")
    st.header("📱 Recepción Móvil")

    # Inicialización de variables de estado
    if "confirmar_nuevo_movil" not in st.session_state:
        st.session_state.confirmar_nuevo_movil = False
    if "show_confirm_modal_movil" not in st.session_state:
        st.session_state.show_confirm_modal_movil = False
    if "is_form_disabled_movil" not in st.session_state:
        st.session_state.is_form_disabled_movil = False
    if "should_reset_all_movil" not in st.session_state:
        st.session_state.should_reset_all_movil = False
    if "remito_saved_movil" not in st.session_state:
        st.session_state.remito_saved_movil = False
    if "excel_saved_movil" not in st.session_state:
        st.session_state.excel_saved_movil = False
    if "remito_generado_msg_movil" not in st.session_state:
        st.session_state.remito_generado_msg_movil = None

    if "articulos_df" not in st.session_state or "clientes_df" not in st.session_state:
        st.session_state.clientes_df, st.session_state.articulos_df = get_clients_and_articles()

    if "entregados_input_rec_movil" not in st.session_state:
        st.session_state.entregados_input_rec_movil = 1
    if "observaciones_item_input_rec_movil" not in st.session_state:
        st.session_state.observaciones_item_input_rec_movil = ""
    if "precio_real_input_rec_movil" not in st.session_state:
        st.session_state.precio_real_input_rec_movil = 0.0
    if "articulo_precargado_rec_movil" not in st.session_state:
        st.session_state.articulo_precargado_rec_movil = None

    # Reset completo si corresponde
    if st.session_state.should_reset_all_movil:
        keys_to_clear = ["remito_activo_rec_movil"] + [k for k in st.session_state.keys() if k.startswith("remito_rec_movil_")]
        for k in keys_to_clear:
            st.session_state.pop(k, None)
        clear_item_inputs_rec_movil()
        st.session_state.should_reset_all_movil = False
        st.session_state.show_confirm_modal_movil = False
        st.session_state.is_form_disabled_movil = False
        st.session_state.remito_saved_movil = False
        st.session_state.excel_saved_movil = False
        st.session_state.remito_generado_msg_movil = None
        st.session_state.input_remito_rec_movil = 1
        st.rerun()

    has_active_del_confirm = any(k.startswith("confirm_del_") and st.session_state[k] for k in st.session_state)
    st.session_state.is_form_disabled_movil = st.session_state.show_confirm_modal_movil or st.session_state.excel_saved_movil or has_active_del_confirm

    # --- Cargar Remito ---
    def cargar_remito_auto_movil():
        if "input_remito_rec_movil" in st.session_state:
            remito_id = st.session_state["input_remito_rec_movil"]
            datos = get_remito_completo(remito_id)
            if datos:
                items = datos["cabecera"]
                items_df = datos["items"].copy()
                if "devueltos" not in items_df.columns:
                    items_df["devueltos"] = 0
                else:
                    items_df["devueltos"] = items_df["devueltos"].fillna(0).astype(int)

                if "observaciones" in items_df.columns:
                    items_df["observaciones"] = items_df["observaciones"].fillna("").astype(str).replace(["None", "none", "nan", "NaN"], "")
                else:
                    items_df["observaciones"] = ""

                st.session_state[f"remito_rec_movil_{remito_id}_cab"] = items
                st.session_state[f"remito_rec_movil_{remito_id}_items"] = items_df
                st.session_state["remito_activo_rec_movil"] = remito_id
                st.session_state["carga_exitosa_movil"] = True
                st.session_state.remito_saved_movil = False
                st.session_state.excel_saved_movil = False
                st.session_state.remito_generado_msg_movil = None
                clear_item_inputs_rec_movil()
            else:
                st.session_state["carga_exitosa_movil"] = False

    remito_cargado = "remito_activo_rec_movil" in st.session_state and bool(st.session_state.get("carga_exitosa_movil"))
    if remito_cargado:
        st.session_state["input_remito_rec_movil"] = st.session_state["remito_activo_rec_movil"]

    st.number_input(
        "Ingrese o seleccione el Número de Remito:",
        min_value=1,
        step=1,
        key="input_remito_rec_movil",
        on_change=cargar_remito_auto_movil,
        disabled=st.session_state.is_form_disabled_movil or remito_cargado
    )

    # Si NO hay remito cargado (o recién se abre/reinicia), enfocar y seleccionar automáticamente el texto del input
    if not remito_cargado:
        st.components.v1.html(
            """
            <script>
                (function() {
                    function focusRemitoInput() {
                        const doc = window.parent.document;
                        if (!doc) return;
                        const inputs = doc.querySelectorAll('div[data-testid="stNumberInput"] input');
                        if (inputs.length > 0) {
                            const inp = inputs[0];
                            inp.focus();
                            inp.select();
                        }
                    }
                    setTimeout(focusRemitoInput, 50);
                    setTimeout(focusRemitoInput, 200);
                })();
            </script>
            """,
            height=0,
        )

    # Botones en la misma línea: "Seleccionar Otro Remito" y "Ver Resúmen" en la cabecera
    if remito_cargado:
        col_btn_top1, col_btn_top2 = st.columns(2)
        with col_btn_top1:
            if st.button("Seleccionar Otro Remito", key="btn_sel_otro_top_movil", type="secondary", width="stretch", disabled=st.session_state.show_confirm_modal_movil):
                st.session_state.should_reset_all_movil = True
                st.rerun()
        with col_btn_top2:
            if st.button("Ver Resúmen", key="btn_resumen_top_movil", width="stretch"):
                st.session_state.show_resumen_movil = True
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
                        })();
                    </script>
                    """,
                    height=0,
                )
                st.rerun()

    if st.session_state.get("carga_exitosa_movil") == False:
        st.error(f"❌ El Remito #{st.session_state.input_remito_rec_movil} no existe.")

    # --- Formulario Principal ---
    if "remito_activo_rec_movil" in st.session_state:
        remito_id = st.session_state["remito_activo_rec_movil"]
        cab_key = f"remito_rec_movil_{remito_id}_cab"
        items_key = f"remito_rec_movil_{remito_id}_items"

        if cab_key in st.session_state and items_key in st.session_state:
            cab = st.session_state[cab_key]

            porc_dto_val = float(cab.get("porc_dto", 0) or 0)
            dto_str = f"{porc_dto_val:g}%"
            st.markdown(f'<div class="header-sub-text">#{remito_id} &nbsp;|&nbsp; Cliente: {cab["razon_social"]} (Boca {cab["boca"]}) &nbsp;|&nbsp; Dto. {dto_str}</div>', unsafe_allow_html=True)

            if f"recepcion_el_dia_{remito_id}" not in st.session_state:
                st.session_state[f"recepcion_el_dia_{remito_id}"] = False

            is_recepcion_dia = bool(st.session_state[f"recepcion_el_dia_{remito_id}"])
            habia_fecha_previa = cab.get("fecha_retiro") is not None

            if is_recepcion_dia:
                cab["fecha_retiro"] = None
                if f"f_ret_m_{remito_id}" in st.session_state:
                    st.session_state[f"f_ret_m_{remito_id}"] = None

            # Fechas y Recepción en el día
            st.date_input("Fecha de Entrega", value=cab["fecha_entrega"], format="DD/MM/YYYY", disabled=True, key=f"f_ent_m_{remito_id}")

            if is_recepcion_dia:
                nueva_fecha_retiro = None
                st.date_input("Fecha de Retiro", value=None, format="DD/MM/YYYY", disabled=True, key=f"f_ret_m_{remito_id}")
                if habia_fecha_previa:
                    st.warning("⚠️ Recepción en el Día: La Fecha de Retiro quedará en blanco.")
            else:
                fecha_entrega_val = cab.get("fecha_entrega")
                val_fecha_ret = cab.get("fecha_retiro")
                if val_fecha_ret and fecha_entrega_val and val_fecha_ret < fecha_entrega_val:
                    val_fecha_ret = fecha_entrega_val

                nueva_fecha_retiro = st.date_input(
                    "Fecha de Retiro",
                    value=val_fecha_ret,
                    min_value=fecha_entrega_val,
                    format="DD/MM/YYYY",
                    key=f"f_ret_m_{remito_id}",
                    disabled=st.session_state.is_form_disabled_movil
                )

            nuevas_observaciones = st.text_area(
                "Observaciones del Remito",
                value=cab.get("observaciones") or "",
                key=f"obs_movil_{remito_id}",
                disabled=st.session_state.is_form_disabled_movil
            )

            # === Alta de Artículos ===
            st.subheader("Alta de Artículos")
            articulo_options_full = st.session_state.articulos_df.apply(
                lambda row: f"{row['nro_articulo']} - {row['descripcion']}", axis=1
            ).tolist()

            articulo_sel_full = st.selectbox(
                f"Artículos para {cab['razon_social']}:",
                options=articulo_options_full,
                index=None,
                placeholder="Seleccione un artículo...",
                key="articulo_selectbox_rec_movil",
                disabled=st.session_state.is_form_disabled_movil
            )

            articulo_sel = None
            if articulo_sel_full and not st.session_state.is_form_disabled_movil:
                articulo_sel = articulo_sel_full.split(" - ")[0]

                should_preload = (
                    'articulo_precargado_rec_movil' not in st.session_state or
                    st.session_state.articulo_precargado_rec_movil != articulo_sel or
                    st.session_state.precio_real_input_rec_movil <= 0
                )

                if should_preload:
                    rec_dia_curr = st.session_state.get(f"recepcion_el_dia_{remito_id}", False)
                    st.session_state.articulo_precargado_rec_movil = articulo_sel

                    if items_key in st.session_state and not st.session_state[items_key].empty and articulo_sel in st.session_state[items_key]['nro_articulo'].values:
                        row = st.session_state[items_key].loc[st.session_state[items_key]['nro_articulo'] == articulo_sel].iloc[0]
                        st.session_state.entregados_input_rec_movil = int(row['entregados'])
                        st.session_state.observaciones_item_input_rec_movil = str(row['observaciones']) if pd.notna(row['observaciones']) else ""
                        st.session_state.precio_real_input_rec_movil = float(row['precio_real'])
                    else:
                        matching = st.session_state.articulos_df.loc[st.session_state.articulos_df['nro_articulo'] == articulo_sel]
                        if not matching.empty:
                            articulo_data = matching.iloc[0]
                            st.session_state.precio_real_input_rec_movil = float(articulo_data['precio_real'])
                            st.session_state.entregados_input_rec_movil = 1
                            st.session_state.observaciones_item_input_rec_movil = ""
                        else:
                            st.session_state.precio_real_input_rec_movil = 0.0
                    st.session_state[f"recepcion_el_dia_{remito_id}"] = rec_dia_curr
                    st.rerun()

            c_ent_add, c_pr_add = st.columns(2)
            with c_ent_add:
                st.number_input("Entregados:", min_value=1, step=1, key="entregados_input_rec_movil", disabled=st.session_state.is_form_disabled_movil)
            with c_pr_add:
                st.number_input("Precio Real:", min_value=0.0, step=500.0, key="precio_real_input_rec_movil", disabled=st.session_state.is_form_disabled_movil)
            st.text_input("Observaciones del Item:", key="observaciones_item_input_rec_movil", disabled=st.session_state.is_form_disabled_movil)

            add_clicked = st.button("Agregar Artículo al Remito", width="stretch", disabled=(articulo_sel is None or st.session_state.is_form_disabled_movil))

            if add_clicked:
                rec_dia_curr = st.session_state.get(f"recepcion_el_dia_{remito_id}", False)
                if items_key in st.session_state and not st.session_state[items_key].empty and articulo_sel in st.session_state[items_key]['nro_articulo'].values:
                    st.warning("⚠️ No puede ser agregado. Item existente en el Remito!")
                elif st.session_state.entregados_input_rec_movil < 1:
                    st.error("⚠️ La cantidad entregada debe ser 1 o mayor.")
                elif st.session_state.precio_real_input_rec_movil <= 0:
                    st.error("⚠️ El precio real debe ser mayor a cero.")
                else:
                    matching = st.session_state.articulos_df.loc[st.session_state.articulos_df['nro_articulo'] == articulo_sel]
                    if not matching.empty:
                        articulo_info = matching.iloc[0]
                        costo_val = float(articulo_info['costo']) if ('costo' in articulo_info and pd.notna(articulo_info['costo'])) else 0.0
                        precio_neto_input = st.session_state.precio_real_input_rec_movil * (1.0 - (porc_dto_val / 100.0))
                        if precio_neto_input < costo_val:
                            st.error(f"⚠️ El Precio Real (${st.session_state.precio_real_input_rec_movil:,.2f}) no deja utilidad con el descuento del {porc_dto_val:.0f}%.")
                        else:
                            new_row = pd.DataFrame([{
                                'id_articulo': int(articulo_info['id']),
                                'nro_articulo': str(articulo_sel),
                                'descripcion': str(articulo_info['descripcion']),
                                'precio_real': float(st.session_state.precio_real_input_rec_movil),
                                'costo': costo_val,
                                'entregados': int(st.session_state.entregados_input_rec_movil),
                                'devueltos': 0,
                                'observaciones': str(st.session_state.observaciones_item_input_rec_movil)
                            }])
                            st.session_state[items_key] = pd.concat([st.session_state[items_key], new_row], ignore_index=True)
                            st.session_state.remito_saved_movil = False
                            st.session_state[f"recepcion_el_dia_{remito_id}"] = rec_dia_curr
                            st.rerun()

            # --- Checkbox Recepción en el Día ---
            c_check, c_space = st.columns([3, 1])
            with c_check:
                st.checkbox("Recepción en el Día", key=f"recepcion_el_dia_{remito_id}", disabled=st.session_state.is_form_disabled_movil)

            if st.session_state.get(f"recepcion_el_dia_{remito_id}", False):
                st.success("Los Cambios afectarán al REMITO ORIGINAL reemplazando al anterior. Las VENTAS quedan pendientes a la Próxima Recepción.")

            # --- Lista / Grilla de Devoluciones y Modificaciones Adaptada para Celular ---
            st.subheader("Ítems del Remito")
            df_items = st.session_state[items_key]

            if df_items.empty:
                st.warning("⚠️ El remito debe tener al menos un artículo cargado.")

            items_invalidos = pd.DataFrame()
            items_precio_invalidos = pd.DataFrame()
            items_precio_menor_costo = pd.DataFrame()
            items_entregados_invalidos = pd.DataFrame()

            if not df_items.empty:
                for idx in df_items.index:
                    nro_art = df_items.loc[idx, 'nro_articulo']
                    desc = df_items.loc[idx, 'descripcion']
                    p_real = float(df_items.loc[idx, 'precio_real'])
                    entreg = int(df_items.loc[idx, 'entregados'])
                    dev = int(df_items.loc[idx, 'devueltos'])
                    obs_val = str(df_items.loc[idx, 'observaciones']) if pd.notna(df_items.loc[idx, 'observaciones']) else ""

                    st.markdown(f'<div style="font-size: 1.05rem; font-weight: 600; margin-top: 0.4rem; margin-bottom: 0.4rem;">Art. {nro_art} - {desc}</div>', unsafe_allow_html=True)
                    
                    # Controles completos de edición por artículo (Entregados/Devueltos en Línea 1, Precio Real/Obs en Línea 2)
                    c_ent, c_dev = st.columns(2)
                    with c_ent:
                        new_entreg = st.number_input(f"Entregados ({nro_art}):", min_value=1, step=1, value=entreg, key=f"entreg_movil_{remito_id}_{idx}", disabled=st.session_state.is_form_disabled_movil)
                        df_items.loc[idx, 'entregados'] = new_entreg
                    with c_dev:
                        new_dev = st.number_input(f"Devueltos ({nro_art}):", min_value=0, value=dev, key=f"dev_movil_{remito_id}_{idx}", disabled=st.session_state.is_form_disabled_movil)
                        df_items.loc[idx, 'devueltos'] = new_dev

                    c_pr, c_obs = st.columns(2)
                    with c_pr:
                        new_p_real = st.number_input(f"Precio Real ({nro_art}):", min_value=0.0, step=500.0, value=p_real, key=f"p_real_movil_{remito_id}_{idx}", disabled=st.session_state.is_form_disabled_movil)
                        df_items.loc[idx, 'precio_real'] = new_p_real
                    with c_obs:
                        new_obs_item = st.text_input(f"Observaciones ({nro_art}):", value=obs_val, key=f"obs_item_movil_{remito_id}_{idx}", disabled=st.session_state.is_form_disabled_movil)
                        df_items.loc[idx, 'observaciones'] = new_obs_item

                    # Línea de Vendidos a continuación de Observaciones
                    vend_item = max(0, new_entreg - new_dev)
                    st.markdown(
                        f'<div style="font-size: 0.95rem; font-weight: 600; color: #ffffff; margin-top: 0.4rem; margin-bottom: 0.6rem;">'
                        f'Vendidos({nro_art}): {vend_item}</div>',
                        unsafe_allow_html=True
                    )

                    # Botón Eliminar Artículo
                    if st.button("Eliminar Artículo", key=f"btn_del_card_{remito_id}_{idx}", width="stretch", disabled=st.session_state.is_form_disabled_movil):
                        st.session_state[f"confirm_del_{remito_id}_{idx}"] = True
                        st.rerun()

                    # Confirmación de eliminación por artículo
                    if st.session_state.get(f"confirm_del_{remito_id}_{idx}", False):
                        st.warning(f"¿Confirma la eliminación del artículo Art. {nro_art} - {desc}?")
                        c_conf1, c_conf2 = st.columns(2)
                        with c_conf1:
                            if st.button("Confirmar Eliminación", key=f"do_del_{remito_id}_{idx}", type="primary", width="stretch"):
                                st.session_state[items_key] = st.session_state[items_key][
                                    st.session_state[items_key]['nro_articulo'] != nro_art
                                ].reset_index(drop=True)
                                st.session_state.remito_saved_movil = False
                                st.session_state.pop(f"confirm_del_{remito_id}_{idx}", None)
                                st.rerun()
                        with c_conf2:
                            if st.button("Cancelar", key=f"cancel_del_{remito_id}_{idx}", width="stretch"):
                                st.session_state.pop(f"confirm_del_{remito_id}_{idx}", None)
                                st.rerun()

                    if idx != df_items.index[-1]:
                        st.divider()

                items_invalidos = df_items[df_items["devueltos"] > df_items["entregados"]]
                items_precio_invalidos = df_items[df_items["precio_real"].isna() | (df_items["precio_real"] <= 0)]
                precio_neto_ser = df_items["precio_real"].fillna(0).astype(float) * (1.0 - (porc_dto_val / 100.0))
                items_precio_menor_costo = df_items[(precio_neto_ser < df_items["costo"]) & (df_items["costo"] > 0)]
                items_entregados_invalidos = df_items[df_items["entregados"].isna() | (df_items["entregados"] <= 0)]

                if not items_invalidos.empty:
                    articuloss_inv = items_invalidos["nro_articulo"].tolist()
                    st.warning(f"⚠️ Hay artículos {articuloss_inv} con más devueltos que entregados.")
                if not items_precio_invalidos.empty:
                    articuloss_p_inv = items_precio_invalidos["nro_articulo"].tolist()
                    st.warning(f"⚠️ Los artículos {articuloss_p_inv} tienen un Precio Real inválido (debe ser mayor a 0). Corregir antes de guardar.")
                if not items_precio_menor_costo.empty:
                    articuloss_menores = items_precio_menor_costo["nro_articulo"].tolist()
                    articuloss_menores_str = "[" + ", ".join(str(x) for x in articuloss_menores) + "]"
                    if porc_dto_val > 0:
                        st.warning(f"⚠️ El artículo {articuloss_menores_str} tiene un Precio Real que no deja utilidad (con el {porc_dto_val:.0f}% de descuento queda por debajo del Costo). Corregir antes de guardar.")
                    else:
                        st.warning(f"⚠️ El artículo {articuloss_menores_str} tiene un Precio Real que no deja utilidad (es menor a su Costo). Corregir antes de guardar.")
                if not items_entregados_invalidos.empty:
                    articuloss_ent = items_entregados_invalidos["nro_articulo"].tolist()
                    articuloss_ent_str = "[" + ", ".join(str(x) for x in articuloss_ent) + "]"
                    st.warning(f"⚠️ Los artículos {articuloss_ent_str} tienen una cantidad Entregados inválida (debe ser mayor a 0). Corregir antes de guardar.")

            # --- Fecha de Retiro Validation ---
            is_recepcion_dia_current = bool(st.session_state.get(f"recepcion_el_dia_{remito_id}", False))
            if is_recepcion_dia_current:
                nueva_fecha_retiro = None
                fecha_retiro_error = False
            else:
                f_entrega = cab.get("fecha_entrega")
                if nueva_fecha_retiro is None:
                    fecha_retiro_error = True
                    st.warning("⚠️ Debe seleccionar una Fecha de Retiro para realizar la Recepción.")
                elif f_entrega and nueva_fecha_retiro < f_entrega:
                    fecha_retiro_error = True
                    st.warning("⚠️ La Fecha de Retiro no puede ser anterior a la Fecha de Entrega.")
                else:
                    fecha_retiro_error = False

            # --- Totales y Utilidad Estimada (Hacia el final del formulario) ---
            if not df_items.empty:
                t_ent = int(df_items["entregados"].sum())
                t_dev = int(df_items["devueltos"].sum())
                t_vend = max(0, t_ent - t_dev)

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

            # --- Totales (Grilla y Utilidad Estimada debajo) ---
            st.subheader("Totales")

            totales_df = pd.DataFrame([{
                "Entregados": t_ent,
                "Devueltos": t_dev,
                "Vendidos": t_vend
            }])
            st.dataframe(totales_df, use_container_width=True, hide_index=True)

            st.metric("Utilidad Estimada", f"$ {t_util:,.2f}")

            # === Acciones Principales ===
            st.subheader("Acciones del Remito")
            tiene_errores = df_items.empty or not items_invalidos.empty or not items_precio_invalidos.empty or not items_entregados_invalidos.empty or not items_precio_menor_costo.empty or fecha_retiro_error
            is_remito_saved = st.session_state.remito_saved_movil
            is_excel_saved = st.session_state.excel_saved_movil

            if st.button("Ver Resúmen del Remito", width="stretch"):
                st.session_state.show_resumen_movil = True
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
                        })();
                    </script>
                    """,
                    height=0,
                )
                st.rerun()

            if st.button("Actualizar Datos Remito", type="primary" if not is_remito_saved else "secondary", width="stretch", disabled=st.session_state.is_form_disabled_movil or is_remito_saved or is_excel_saved or tiene_errores):
                try:
                    update_remito_data(remito_id=remito_id, fecha_retiro=nueva_fecha_retiro, observaciones_cabecera=nuevas_observaciones, items_df=df_items)
                    st.session_state.remito_saved_movil = True
                    st.success("✅ Datos del remito actualizados correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar: {e}")

            if st.button("Seleccionar Otro Remito", type="primary" if is_excel_saved else "secondary", width="stretch", disabled=st.session_state.show_confirm_modal_movil):
                st.session_state.should_reset_all_movil = True
                st.rerun()

if __name__ == "__main__":
    remitos_ventas_movil()
