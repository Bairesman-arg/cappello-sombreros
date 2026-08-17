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
        min-height: 48px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    .stNumberInput input {
        font-size: 1.1rem !important;
        text-align: center !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title(config.TITULO_APP)
    st.header("📱 Recepción Móvil de Remitos")

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

    st.session_state.is_form_disabled_movil = st.session_state.show_confirm_modal_movil or st.session_state.excel_saved_movil

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

    st.number_input(
        "Ingrese o seleccione el Número de Remito:",
        min_value=1,
        step=1,
        key="input_remito_rec_movil",
        on_change=cargar_remito_auto_movil,
        disabled=st.session_state.is_form_disabled_movil
    )

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
            st.subheader(f"#{remito_id}  |  Cliente: {cab['razon_social']} (Boca {cab['boca']})  |  Dto. {dto_str}")

            if f"recepcion_el_dia_{remito_id}" not in st.session_state:
                st.session_state[f"recepcion_el_dia_{remito_id}"] = False

            is_recepcion_dia = bool(st.session_state[f"recepcion_el_dia_{remito_id}"])
            habia_fecha_previa = cab.get("fecha_retiro") is not None

            if is_recepcion_dia:
                cab["fecha_retiro"] = None

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
                elif not val_fecha_ret and fecha_entrega_val:
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

            # === Carga e Ítems ===
            st.subheader("Carga / Modificación de Items")
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

            st.number_input("Entregados:", min_value=1, step=1, key="entregados_input_rec_movil", disabled=st.session_state.is_form_disabled_movil)
            st.number_input("Precio Real:", min_value=0.0, step=500.0, key="precio_real_input_rec_movil", disabled=st.session_state.is_form_disabled_movil)
            st.text_input("Observaciones del Item:", key="observaciones_item_input_rec_movil", disabled=st.session_state.is_form_disabled_movil)

            col_add, col_del = st.columns(2, gap="small")
            with col_add:
                add_clicked = st.button("Agregar Item ➕", width="stretch", disabled=(articulo_sel is None or st.session_state.is_form_disabled_movil))
            with col_del:
                del_clicked = st.button("Eliminar Item 🗑️", width="stretch", disabled=(articulo_sel is None or st.session_state.is_form_disabled_movil))

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

            if del_clicked:
                rec_dia_curr = st.session_state.get(f"recepcion_el_dia_{remito_id}", False)
                if items_key in st.session_state and (st.session_state[items_key].empty or articulo_sel not in st.session_state[items_key]['nro_articulo'].values):
                    st.warning("⚠️ No puede ser eliminado. Item inexistente en el Remito!")
                else:
                    st.session_state[items_key] = st.session_state[items_key][
                        st.session_state[items_key]['nro_articulo'] != articulo_sel
                    ].reset_index(drop=True)
                    st.session_state.remito_saved_movil = False
                    st.session_state[f"recepcion_el_dia_{remito_id}"] = rec_dia_curr
                    st.rerun()

            # --- Checkbox Recepción en el Día ---
            st.divider()
            c_check, c_space = st.columns([3, 1])
            with c_check:
                st.checkbox("Recepción en el Día", key=f"recepcion_el_dia_{remito_id}", disabled=st.session_state.is_form_disabled_movil)

            if st.session_state.get(f"recepcion_el_dia_{remito_id}", False):
                st.success("Los Cambios afectarán al REMITO ORIGINAL reemplazando al anterior. Las VENTAS quedan pendientes a la Próxima Recepción.")

            # --- Lista / Grilla de Devoluciones Adaptada ---
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

                    st.markdown(f"**Art. {nro_art} - {desc}**")
                    c1, c2 = st.columns(2)
                    with c1:
                        new_dev = st.number_input(f"Devueltos ({nro_art}):", min_value=0, max_value=entreg, value=dev, key=f"dev_movil_{remito_id}_{idx}", disabled=st.session_state.is_form_disabled_movil)
                        df_items.loc[idx, 'devueltos'] = new_dev
                    with c2:
                        vend_item = max(0, entreg - new_dev)
                        st.metric(f"Vendidos ({nro_art}):", vend_item)

                    df_items.loc[idx, 'observaciones'] = st.text_input(f"Obs ({nro_art}):", value=obs_val, key=f"obs_item_movil_{remito_id}_{idx}", disabled=st.session_state.is_form_disabled_movil)
                    st.divider()

                items_invalidos = df_items[df_items["devueltos"] > df_items["entregados"]]
                items_precio_invalidos = df_items[df_items["precio_real"].isna() | (df_items["precio_real"] <= 0)]
                precio_neto_ser = df_items["precio_real"].fillna(0).astype(float) * (1.0 - (porc_dto_val / 100.0))
                items_precio_menor_costo = df_items[(precio_neto_ser < df_items["costo"]) & (df_items["costo"] > 0)]
                items_entregados_invalidos = df_items[df_items["entregados"].isna() | (df_items["entregados"] <= 0)]

                if not items_invalidos.empty:
                    st.warning("⚠️ Hay artículos con más devueltos que entregados.")
                if not items_precio_invalidos.empty:
                    st.warning("⚠️ Hay artículos con Precio Real menor o igual a cero.")
                if not items_precio_menor_costo.empty:
                    st.warning(f"⚠️ Hay artículos con un Precio Real que no deja utilidad con el {porc_dto_val:.0f}% de descuento.")

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

            # --- Totales ---
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

            m1, m2 = st.columns(2)
            with m1:
                st.metric("Total Vendidos", t_vend)
            with m2:
                st.metric("Utilidad Estimada", f"$ {t_util:,.2f}")

            # === Acciones Principales ===
            st.subheader("Acciones del Remito")
            tiene_errores = df_items.empty or not items_invalidos.empty or not items_precio_invalidos.empty or not items_entregados_invalidos.empty or not items_precio_menor_costo.empty or fecha_retiro_error
            is_remito_saved = st.session_state.remito_saved_movil
            is_excel_saved = st.session_state.excel_saved_movil

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

            is_retiro_for_excel = not is_recepcion_dia
            excel_btn_label = f"Sobreescribir Remito Original en Excel #{remito_id}" if is_recepcion_dia else f"Actualizar Remito de Ventas en Excel #{remito_id}"

            if is_remito_saved and not is_excel_saved:
                try:
                    if is_local_app():
                        if st.button(excel_btn_label, type="primary", width="stretch"):
                            last_folder = st.session_state.get('last_used_folder')
                            success, msg, chosen_folder = process_generate_remito(remito_id, is_retiro=is_retiro_for_excel, default_dir=last_folder)
                            if success:
                                st.session_state.last_used_folder = chosen_folder
                                st.session_state.remito_generado_msg_movil = f"🎉 ¡Remito #{remito_id} guardado exitosamente en: **{msg}**!"
                                st.session_state.excel_saved_movil = True
                            st.rerun()
                    else:
                        excel_buffer = gen_remito(remito_id, is_retiro=is_retiro_for_excel)
                        if st.download_button(label=excel_btn_label, type="primary", width="stretch", data=excel_buffer, file_name=get_remito_filename(remito_id, is_retiro=is_retiro_for_excel), mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
                            st.session_state.excel_saved_movil = True
                            st.session_state.remito_generado_msg_movil = f"🎉 ¡Remito #{remito_id} descargado exitosamente!"
                            st.rerun()
                except Exception as e:
                    st.error(f"Error Excel: {e}")
            else:
                st.button(excel_btn_label, width="stretch", disabled=True)

            if st.session_state.get("remito_generado_msg_movil"):
                st.success(st.session_state.remito_generado_msg_movil)

if __name__ == "__main__":
    remitos_ventas_movil()
