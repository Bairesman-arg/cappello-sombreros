import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime
from models import get_remito_completo, update_remito_data, get_clients_and_articles

def clear_item_inputs_rec(set_focus=False):
    """Reinicia los valores de los inputs de items para recepciones."""
    st.session_state.entregados_input_rec = 1
    st.session_state.observaciones_item_input_rec = ""
    st.session_state.articulo_precargado_rec = None
    st.session_state.precio_real_input_rec = 0.0
    st.session_state.articulo_selectbox_rec = None
    if set_focus:
        st.session_state.focus_target = "articulo"
    else:
        st.session_state.pop("focus_target", None)
from gen_remito import gen_remito, process_generate_remito, is_local_app, get_remito_filename
import numpy as np
import time
import config

def remitos_ventas():
    st.set_page_config(layout="wide")
    st.title(config.TITULO_APP)
    st.header("Recepción de Remitos")

    st.markdown("""
    <style>
    div.element-container:has(iframe[height="0"]),
    div[data-testid="stCustomComponentV1"]:has(iframe[height="0"]),
    div[data-testid="stElementContainer"]:has(iframe[height="0"]) {
        display: none !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    iframe[height="0"] {
        display: none !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Inicializamos las variables de estado para los botones de confirmación
    if "confirmar_nuevo" not in st.session_state:
        st.session_state["confirmar_nuevo"] = False
    if "show_confirm_modal" not in st.session_state:
        st.session_state.show_confirm_modal = False
    if "is_form_disabled" not in st.session_state:
        st.session_state.is_form_disabled = False
    if "should_reset_all" not in st.session_state:
        st.session_state.should_reset_all = False

    if st.session_state["confirmar_nuevo"]:
        st.session_state["input_remito_rec"] = 1
        st.session_state.pop("remito_activo_rec", None)

    if "remito_grabado" not in st.session_state:
        st.session_state.remito_grabado = False
    if "error_grabacion" not in st.session_state:
        st.session_state.error_grabacion = False
    if "success_shown" not in st.session_state:
        st.session_state.success_shown = False
    if "remito_saved" not in st.session_state:
        st.session_state.remito_saved = False

    if "articulos_df" not in st.session_state or "clientes_df" not in st.session_state:
        st.session_state.clientes_df, st.session_state.articulos_df = get_clients_and_articles()

    if "entregados_input_rec" not in st.session_state:
        st.session_state.entregados_input_rec = 1
    if "observaciones_item_input_rec" not in st.session_state:
        st.session_state.observaciones_item_input_rec = ""
    if "precio_real_input_rec" not in st.session_state:
        st.session_state.precio_real_input_rec = 0.0
    if "articulo_precargado_rec" not in st.session_state:
        st.session_state.articulo_precargado_rec = None

    # Manejo de flags de rerun
    if st.session_state.get("should_clear_items_rec", False):
        clear_item_inputs_rec()
        st.session_state.should_clear_items_rec = False

    if st.session_state.should_reset_all:
        # Limpiar session state para nuevo remito
        keys_to_clear = ["remito_activo_rec"] + [k for k in st.session_state.keys() if k.startswith("remito_rec_")]
        for k in keys_to_clear:
            st.session_state.pop(k, None)
        clear_item_inputs_rec()
        st.session_state.should_reset_all = False
        st.session_state.show_confirm_modal = False
        st.session_state.is_form_disabled = False
        st.session_state.success_shown = False
        st.session_state.remito_saved = False
        st.session_state.input_remito_rec = 1
        st.rerun()

    # Control de estado del formulario
    st.session_state.is_form_disabled = st.session_state.show_confirm_modal

    # --- Entrada de número de remito ---
    col1, _ = st.columns([1, 4], gap="small")

    # Función para cargar remito automáticamente
    def cargar_remito_auto():
        if "input_remito_rec" in st.session_state:
            remito_id = st.session_state["input_remito_rec"]
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
                                
                st.session_state[f"remito_rec_{remito_id}_cab"] = items
                st.session_state[f"remito_rec_{remito_id}_items"] = items_df
                st.session_state["remito_activo_rec"] = remito_id
                st.session_state["carga_exitosa"] = True
                st.session_state.remito_saved = False  # Reset cuando se carga un nuevo remito
                st.session_state.success_shown = False
                clear_item_inputs_rec()
            else:
                st.session_state["carga_exitosa"] = False

    # Sincronizar input con el remito activo si existe datos guardados
    if "remito_activo_rec" in st.session_state and st.session_state["remito_activo_rec"] is not None:
        st.session_state["input_remito_rec"] = st.session_state["remito_activo_rec"]

    with col1:
        remito_id = st.number_input(
            label="Ingrese el número de Remito:",
            min_value=1, 
            step=1, 
            key="input_remito_rec",
            on_change=cargar_remito_auto,
            help="Ingrese un Remito existente para editar.",
            disabled=st.session_state.is_form_disabled
        )



    # Mostrar mensajes después de cualquier carga
    if "carga_exitosa" in st.session_state:
        if not st.session_state["carga_exitosa"]:
            st.error("No se encontró el remito.")
            st.stop()
        # Limpiar el flag
        del st.session_state["carga_exitosa"]

    # --- Mostrar formulario si hay remito activo ---
    if "remito_activo_rec" in st.session_state:
        remito_id = st.session_state["remito_activo_rec"]
        cab_key = f"remito_rec_{remito_id}_cab"
        items_key = f"remito_rec_{remito_id}_items"
        
        if cab_key in st.session_state and items_key in st.session_state:
            cab = st.session_state[cab_key]
            
            st.subheader(f"#{remito_id}  |  Cliente: {cab['razon_social']} (Boca {cab['boca']})")

            col_izq, col_der = st.columns(2, gap="small")

            with col_izq:
                st.date_input(
                    "Fecha de Entrega", 
                    value=cab["fecha_entrega"], 
                    format="DD/MM/YYYY", 
                    disabled=True,
                    key=f"fecha_entrega_{remito_id}"
                )
                nueva_fecha_retiro = st.date_input(
                    "Fecha de Retiro",
                    value=cab["fecha_retiro"],
                    format="DD/MM/YYYY",
                    key=f"fecha_retiro_{remito_id}",
                    disabled=st.session_state.is_form_disabled
                )

            with col_der:
                nuevas_observaciones = st.text_area(
                    "Observaciones del Remito  ( notas privadas )",
                    value=cab.get("observaciones") or "",
                    key=f"obs_remito_{remito_id}",
                    height=150,
                    disabled=st.session_state.is_form_disabled
                )

            # === SECCIÓN CARGA Y ELIMINACIÓN DE ITEMS ===
            st.header("Carga y Eliminación de Items")

            articulo_options_full = st.session_state.articulos_df.apply(
                lambda row: f"{row['nro_articulo']} - {row['descripcion']}", axis=1
            ).tolist()

            articulo_sel_full = st.selectbox(
                f"Artículos para {cab['razon_social']}:",
                options=articulo_options_full,
                index=None,
                placeholder="Seleccione un artículo...",
                key="articulo_selectbox_rec",
                disabled=st.session_state.is_form_disabled,
                help="Seleccione un nuevo artículo o uno existente para agregar o eliminar."
            )

            articulo_sel = None
            if articulo_sel_full and not st.session_state.is_form_disabled:
                articulo_sel = articulo_sel_full.split(" - ")[0]

                should_preload = (
                    'articulo_precargado_rec' not in st.session_state or
                    st.session_state.articulo_precargado_rec != articulo_sel or
                    st.session_state.precio_real_input_rec <= 0
                )

                if should_preload:
                    st.session_state.articulo_precargado_rec = articulo_sel

                    # Pre-cargar datos si el artículo existe en los items actuales
                    if items_key in st.session_state and not st.session_state[items_key].empty and articulo_sel in st.session_state[items_key]['nro_articulo'].values:
                        row = st.session_state[items_key].loc[st.session_state[items_key]['nro_articulo'] == articulo_sel].iloc[0]
                        st.session_state.entregados_input_rec = int(row['entregados'])
                        st.session_state.observaciones_item_input_rec = str(row['observaciones']) if pd.notna(row['observaciones']) else ""
                        st.session_state.precio_real_input_rec = float(row['precio_real'])
                    else:
                        matching = st.session_state.articulos_df.loc[st.session_state.articulos_df['nro_articulo'] == articulo_sel]
                        if not matching.empty:
                            articulo_data = matching.iloc[0]
                            st.session_state.precio_real_input_rec = float(articulo_data['precio_real'])
                            st.session_state.entregados_input_rec = 1
                            st.session_state.observaciones_item_input_rec = ""
                        else:
                            st.session_state.precio_real_input_rec = 0.0
                    st.session_state.focus_target = "entregados"
                    st.rerun()

            col_entregados, col_precio, col_observ = st.columns([1, 1, 3], gap="small")
            with col_entregados:
                st.number_input(
                    "Entregados:",
                    min_value=1,
                    step=1,
                    key="entregados_input_rec",
                    disabled=st.session_state.is_form_disabled
                )
            with col_precio:
                st.number_input(
                    "Precio Real:",
                    min_value=0.0,
                    step=500.0,
                    key="precio_real_input_rec",
                    disabled=st.session_state.is_form_disabled
                )
            with col_observ:
                st.text_input(
                    "Observaciones del Item:",
                    key="observaciones_item_input_rec",
                    disabled=st.session_state.is_form_disabled
                )

            # Botones de acción (Únicamente "Agregar Item ➕" y "Eliminar Item 🗑️")
            c_btn1, c_btn2 = st.columns(2, gap="small")

            with c_btn1:
                add_clicked = st.button(
                    "Agregar Item ➕",
                    use_container_width=True,
                    disabled=(articulo_sel is None or st.session_state.is_form_disabled)
                )

            with c_btn2:
                del_clicked = st.button(
                    "Eliminar Item 🗑️",
                    use_container_width=True,
                    disabled=(articulo_sel is None or st.session_state.is_form_disabled)
                )

            if add_clicked:
                if items_key in st.session_state and not st.session_state[items_key].empty and articulo_sel in st.session_state[items_key]['nro_articulo'].values:
                    st.session_state.item_rec_message = ("warning", "⚠️ No puede ser agregado. Item existente en el Remito!")
                    st.session_state.should_clear_items_rec = True
                    st.rerun()
                elif st.session_state.entregados_input_rec < 1:
                    st.session_state.item_rec_message = ("error", "⚠️ La cantidad entregada debe ser 1 o mayor.")
                    st.rerun()
                elif st.session_state.precio_real_input_rec <= 0:
                    st.session_state.item_rec_message = ("error", "⚠️ El precio real debe ser mayor a cero.")
                    st.rerun()
                else:
                    matching = st.session_state.articulos_df.loc[st.session_state.articulos_df['nro_articulo'] == articulo_sel]
                    if not matching.empty:
                        articulo_info = matching.iloc[0]
                        costo_val = float(articulo_info['costo']) if ('costo' in articulo_info and pd.notna(articulo_info['costo'])) else 0.0
                        new_row = pd.DataFrame([{
                            'id_articulo': int(articulo_info['id']),
                            'nro_articulo': str(articulo_sel),
                            'descripcion': str(articulo_info['descripcion']),
                            'precio_real': float(st.session_state.precio_real_input_rec),
                            'costo': costo_val,
                            'entregados': int(st.session_state.entregados_input_rec),
                            'devueltos': 0,
                            'observaciones': str(st.session_state.observaciones_item_input_rec)
                        }])
                        st.session_state[items_key] = pd.concat([st.session_state[items_key], new_row], ignore_index=True)
                        st.session_state.remito_saved = False
                        st.session_state.should_clear_items_rec = True
                        st.rerun()

            if del_clicked:
                if items_key in st.session_state and (st.session_state[items_key].empty or articulo_sel not in st.session_state[items_key]['nro_articulo'].values):
                    st.session_state.item_rec_message = ("warning", "⚠️ No puede ser eliminado. Item inexistente en el Remito!")
                    st.session_state.should_clear_items_rec = True
                    st.rerun()
                else:
                    st.session_state[items_key] = st.session_state[items_key][
                        st.session_state[items_key]['nro_articulo'] != articulo_sel
                    ].reset_index(drop=True)
                    st.session_state.remito_saved = False
                    st.session_state.item_rec_message = ("warning", "Artículo eliminado")
                    st.session_state.should_clear_items_rec = True
                    st.rerun()

            if "item_rec_message" in st.session_state and st.session_state.item_rec_message:
                msg_type, msg_text = st.session_state.item_rec_message
                if msg_type == "warning":
                    st.warning(msg_text)
                elif msg_type == "error":
                    st.error(msg_text)
                elif msg_type == "success":
                    st.success(msg_text)
                del st.session_state.item_rec_message

            st.subheader(f"Items del Remito #{remito_id}")

            col_edit, col_calc = st.columns([4, 1], gap="small")
            
            with col_edit:
                st.markdown("#### Editar Devoluciones y Observaciones")
                
                # Grilla editable principal SIN callback
                st.data_editor(
                    st.session_state[items_key],
                    hide_index=True,
                    width="stretch",
                    column_order=["nro_articulo", "descripcion", "precio_real", "entregados", "devueltos", "observaciones"],
                    column_config={
                        "nro_articulo": st.column_config.TextColumn("Artículo", disabled=True, width="small"),
                        "descripcion": st.column_config.TextColumn("Descripción", disabled=True, width="medium"),
                        "precio_real": st.column_config.NumberColumn(
                            "Precio Real",
                            min_value=0.01,
                            step=100.0,
                            format="$%.2f",
                            width="small"
                        ),
                        "entregados": st.column_config.NumberColumn(
                            "Entregados",
                            min_value=1,
                            step=1,
                            width="small"
                        ),
                        "devueltos": st.column_config.NumberColumn(
                            "devueltos", 
                            min_value=0,
                            step=1,
                            width="small"
                        ),
                        "Observaciones": st.column_config.TextColumn("observaciones", width="medium"),
                    },
                    disabled=["nro_articulo", "descripcion"] + (["precio_real", "entregados", "devueltos", "observaciones"] if st.session_state.is_form_disabled else []),
                    key=f"editor_{remito_id}",
                    num_rows="fixed"
                )
                
            # Obtener datos actuales del editor DESPUÉS del data_editor
            editor_key = f"editor_{remito_id}"
            df_editado = st.session_state[items_key].copy()  # Empezar con datos originales
            
            if editor_key in st.session_state:
                editor_changes = st.session_state[editor_key]
                
                # Aplicar los cambios editados al DataFrame
                if isinstance(editor_changes, dict) and 'edited_rows' in editor_changes:
                    edited_rows = editor_changes['edited_rows']
                    for row_idx, changes in edited_rows.items():
                        for col_name, new_value in changes.items():
                            df_editado.loc[row_idx, col_name] = new_value
            
            # VALIDAR grilla
            items_invalidos = pd.DataFrame()
            items_precio_invalidos = pd.DataFrame()
            items_entregados_invalidos = pd.DataFrame()
            try:
                if "devueltos" in df_editado.columns and "entregados" in df_editado.columns:
                    items_invalidos = df_editado[df_editado["devueltos"] > df_editado["entregados"]]
                    if not items_invalidos.empty:
                        articulos_problema = items_invalidos["nro_articulo"].tolist()
                        articulos_str = "[" + ", ".join(str(x) for x in articulos_problema) + "]"
                        st.warning(f"⚠️ Los artículos {articulos_str} tienen más devueltos que entregados. Corregir antes de guardar.")

                if "precio_real" in df_editado.columns:
                    items_precio_invalidos = df_editado[df_editado["precio_real"].isna() | (df_editado["precio_real"] <= 0)]
                    if not items_precio_invalidos.empty:
                        articulos_precio = items_precio_invalidos["nro_articulo"].tolist()
                        articulos_precio_str = "[" + ", ".join(str(x) for x in articulos_precio) + "]"
                        st.warning(f"⚠️ Los artículos {articulos_precio_str} tienen un Precio Real inválido (debe ser mayor a 0). Corregir antes de guardar.")

                if "entregados" in df_editado.columns:
                    items_entregados_invalidos = df_editado[df_editado["entregados"].isna() | (df_editado["entregados"] <= 0)]
                    if not items_entregados_invalidos.empty:
                        articulos_entregados = items_entregados_invalidos["nro_articulo"].tolist()
                        articulos_entregados_str = "[" + ", ".join(str(x) for x in articulos_entregados) + "]"
                        st.warning(f"⚠️ Los artículos {articulos_entregados_str} tienen una cantidad Entregados inválida (debe ser mayor a 0). Corregir antes de guardar.")

            except Exception as e:
                st.error(f"Error en validación: {str(e)}")

            with col_calc:
                st.markdown("#### Vendidos")
                
                # Calcular vendidos como Entregados - Devueltos todo el tiempo
                if "devueltos" in df_editado.columns and "entregados" in df_editado.columns:
                    devueltos_clean = df_editado["devueltos"].fillna(0).astype(int)
                    entregados_clean = df_editado["entregados"].fillna(0).astype(int)
                    vendidos_valores = (entregados_clean - devueltos_clean).clip(lower=0)

                    vendidos_df = pd.DataFrame({"Vendidos": vendidos_valores})
                    
                    st.dataframe(
                        vendidos_df,
                        hide_index=True,
                        width="stretch",
                        column_config={
                            "Vendidos": st.column_config.NumberColumn("Vendidos", width="small")
                        }
                    )
                else:
                    st.info("Datos no disponibles")

            # --- Totales y Utilidades ---
            total_utilidades = 0.0
            if isinstance(df_editado, pd.DataFrame) and "devueltos" in df_editado.columns and "entregados" in df_editado.columns:
                try:
                    entregados_clean = df_editado["entregados"].fillna(0).astype(int)
                    devueltos_clean = df_editado["devueltos"].fillna(0).astype(int)
                    vendidos_clean = (entregados_clean - devueltos_clean).clip(lower=0)

                    total_entregados = int(entregados_clean.sum())
                    total_devueltos = int(devueltos_clean.sum())
                    total_vendidos = int(vendidos_clean.sum())

                    # Porcentaje de descuento (clientes.porc_dto)
                    porc_dto_val = float(cab.get("porc_dto", 0) or 0)

                    # Precio real del remito y costo del artículo desde base de datos
                    precio_real_ser = df_editado["precio_real"].fillna(0).astype(float) if "precio_real" in df_editado.columns else pd.Series(0.0, index=df_editado.index)
                    costo_ser = df_editado["costo"].fillna(0).astype(float) if "costo" in df_editado.columns else pd.Series(0.0, index=df_editado.index)

                    # Utilidad unitaria = (precio_real - porcentaje_descuento) - costo
                    precio_con_dto = precio_real_ser * (1.0 - (porc_dto_val / 100.0))
                    utilidad_unitaria = precio_con_dto - costo_ser

                    # Utilidad total = suma de (utilidad_unitaria * vendidos)
                    total_utilidades = float((utilidad_unitaria * vendidos_clean).sum())
                except:
                    total_entregados = total_devueltos = total_vendidos = 0
                    total_utilidades = 0.0
            else:
                total_entregados = total_devueltos = total_vendidos = 0
                total_utilidades = 0.0

            col_tot_left, col_tot_right = st.columns([4, 1], gap="small")
            with col_tot_left:
                c1, c2, c3 = st.columns(3, gap="small")
                c1.metric("Total Entregados", total_entregados)
                c2.metric("Total Devueltos", total_devueltos)
                c3.metric("Total Vendidos", total_vendidos)
            with col_tot_right:
                st.metric("Utilidad del Remito", f"$ {total_utilidades:,.2f}")

            # === BOTONES PRINCIPALES (siguiendo la lógica de remitos_entregas.py) ===
            st.header("Acciones del Remito")

            # Verificar que no haya errores de validación
            tiene_errores = not items_invalidos.empty or not items_precio_invalidos.empty or not items_entregados_invalidos.empty
            is_remito_saved = st.session_state.remito_saved
            can_save = not tiene_errores  # En ventas, solo necesitamos que no haya errores

            col_buttons = st.columns(3, gap="small")

            # Botón Actualizar Datos Remito
            say_error = False
            with col_buttons[0]:
                if st.button("Actualizar Datos Remito", type="primary", use_container_width=True,
                            disabled=st.session_state.is_form_disabled or is_remito_saved or tiene_errores):
                    if not can_save:
                        say_error = True
                    else:
                        try:
                            update_remito_data(
                                remito_id=remito_id,
                                fecha_retiro=nueva_fecha_retiro,
                                observaciones_cabecera=nuevas_observaciones,
                                items_df=df_editado
                            )
                            st.session_state.remito_saved = True
                            st.session_state.success_shown = False  # Para mostrar el mensaje
                            # Forzar rerun para actualizar el estado de los botones
                            st.rerun()
                        except Exception as e:
                            st.session_state.error_grabacion = True
                            st.rerun()

            # Botón Nuevo Remito
            with col_buttons[1]:
                nuevo_remito_disabled = st.session_state.is_form_disabled

                if st.button("Nuevo Remito", use_container_width=True,
                            disabled=nuevo_remito_disabled):
                    if is_remito_saved:
                        st.session_state.should_reset_all = True
                        st.rerun()
                    else:
                        st.session_state.show_confirm_modal = True
                        st.rerun()

            # Botón Generar/Actualizar Remito en Excel
            with col_buttons[2]:
                if is_remito_saved:
                    try:
                        if is_local_app():
                            if st.button(f"Actualizar Remito en Excel #{remito_id}", use_container_width=True, key=f"btn_gen_{remito_id}"):
                                last_folder = st.session_state.get('last_used_folder')
                                success, msg, chosen_folder = process_generate_remito(remito_id, is_retiro=True, default_dir=last_folder)
                                if success:
                                    st.session_state.last_used_folder = chosen_folder
                                    st.toast(f"Remito #{remito_id} guardado con éxito", icon="📁")
                                    time.sleep(1)
                                    st.session_state.should_reset_all = True
                                    st.rerun()
                                else:
                                    st.info(msg)
                        else:
                            excel_buffer = gen_remito(remito_id, is_retiro=True)
                            download_clicked = st.download_button(
                                label=f"Actualizar Remito en Excel #{remito_id}",
                                use_container_width=True,
                                data=excel_buffer,
                                file_name=get_remito_filename(remito_id, is_retiro=True),
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key=f"download_remito_{remito_id}"
                            )
                            if download_clicked:
                                st.session_state.should_reset_all = True
                                st.rerun()
                    except Exception as e:
                        st.error(f"Error al generar el remito: {str(e)}")
                else:
                    st.button("Actualizar Remito en Excel", use_container_width=True, disabled=True)

            if say_error:
                st.error("Hay errores de validación que deben corregirse antes de guardar.")

            if tiene_errores:
                st.caption("⚠️ Botón Guardar deshabilitado por errores de validación")

            # Mensaje de éxito fuera de las columnas (ocupa todo el ancho)
            if st.session_state.remito_saved and not st.session_state.get('success_shown', False):
                st.success(f"🎉 Remito #{remito_id} actualizado con éxito!")
                st.balloons()
                # Marcar que ya se mostró el mensaje para evitar que se repita
                st.session_state.success_shown = True

            # Mensaje de error
            if st.session_state.error_grabacion:
                st.error("❌ Error al guardar el remito.")
                st.session_state.error_grabacion = False

            # === MODAL DE CONFIRMACIÓN (siguiendo la lógica de remitos_entregas.py) ===
            if st.session_state.show_confirm_modal:
                st.warning("¿Desea continuar y cargar un nuevo remito? Se perderán los cambios no guardados.")

                col_confirm, col_cancel, _ = st.columns([1, 1, 1], gap="small")

                with col_confirm:
                    if st.button("Sí, continuar ⚠️", width="stretch"):
                        st.session_state.show_confirm_modal = False
                        st.session_state.should_reset_all = True
                        st.rerun()

                with col_cancel:
                    if st.button("Cancelar ❌", width="stretch"):
                        st.session_state.show_confirm_modal = False
                        st.rerun()

    # Footer
    st.markdown(f"`{config.FOOTER_APP}`")

    target_to_focus = st.session_state.get('focus_target', '')
    if target_to_focus:
        st.session_state.focus_target = ''

    is_remito_activo = "remito_activo_rec" in st.session_state and st.session_state["remito_activo_rec"] is not None
    focus_script = ""
    if not is_remito_activo:
        focus_script = """
            function focusRemitoInput() {
                try {
                    const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                    const remitoWidget = numInputs.find(w => (w.innerText || '').includes('Remito')) || numInputs[0];
                    if (remitoWidget) {
                        const input = remitoWidget.querySelector('input');
                        if (input) {
                            input.focus();
                        }
                    }
                } catch(e) {}
            }
            setTimeout(focusRemitoInput, 150);
            setTimeout(focusRemitoInput, 350);
        """

    components.html(f"""
    <script>
        (function() {{
            const doc = window.parent.document;

            if (window.parent._selectHandler) {{
                doc.removeEventListener('focusin', window.parent._selectHandler, true);
                doc.removeEventListener('click', window.parent._selectHandler, true);
            }}
            if (window.parent._selectionChangeHandler) {{
                doc.removeEventListener('selectionchange', window.parent._selectionChangeHandler, true);
            }}

            function doSelect(el) {{
                if (!el || doc.activeElement !== el) return;
                try {{
                    if (typeof el.select === 'function') {{
                        el.select();
                    }}
                }} catch(e1) {{}}
                try {{
                    if (typeof el.setSelectionRange === 'function' && el.value !== undefined) {{
                        el.setSelectionRange(0, el.value.length);
                    }}
                }} catch(e2) {{}}
                try {{
                    doc.execCommand('selectAll', false, null);
                }} catch(e3) {{}}
            }}

            window.parent._selectHandler = function(e) {{
                const target = e.target;
                if (!target) return;
                const tag = (target.tagName || '').toUpperCase();
                if (tag !== 'INPUT' && tag !== 'TEXTAREA') return;

                if (target.dataset.autoSelecting === 'true') return;
                target.dataset.autoSelecting = 'true';

                function runPasses() {{
                    doSelect(target);
                    setTimeout(function() {{ doSelect(target); }}, 10);
                    setTimeout(function() {{ doSelect(target); }}, 40);
                    setTimeout(function() {{ doSelect(target); }}, 120);
                    setTimeout(function() {{ doSelect(target); }}, 250);
                    setTimeout(function() {{ doSelect(target); }}, 450);
                    requestAnimationFrame(function() {{ doSelect(target); }});
                }}

                runPasses();
            }};

            window.parent._selectionChangeHandler = function() {{
                const active = doc.activeElement;
                if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {{
                    if (active.dataset.autoSelecting === 'true') {{
                        if (active.selectionStart !== 0 || active.selectionEnd !== active.value.length) {{
                            doSelect(active);
                        }}
                    }}
                }}
            }};

            doc.addEventListener('focusin', window.parent._selectHandler, true);
            doc.addEventListener('click', window.parent._selectHandler, true);
            doc.addEventListener('selectionchange', window.parent._selectionChangeHandler, true);

            doc.addEventListener('keydown', function(e) {{
                if (e.target && e.target.dataset) {{
                    delete e.target.dataset.autoSelecting;
                }}
            }}, true);

            doc.addEventListener('focusout', function(e) {{
                if (e.target && e.target.dataset) {{
                    delete e.target.dataset.autoSelecting;
                }}
            }}, true);

            function getFormSequence() {{
                const sequence = [];
                const selectboxes = doc.querySelectorAll('div[data-testid="stSelectbox"]');
                if (selectboxes.length > 0) {{
                    const artBox = selectboxes[selectboxes.length - 1];
                    const input = artBox.querySelector('input');
                    if (input) sequence.push({{ container: artBox, input: input }});
                }}
                const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                numInputs.forEach(w => {{
                    const input = w.querySelector('input');
                    if (input) sequence.push({{ container: w, input: input }});
                }});
                const textInputs = Array.from(doc.querySelectorAll('div[data-testid="stTextInput"]'));
                textInputs.forEach(w => {{
                    const input = w.querySelector('input');
                    if (input) sequence.push({{ container: w, input: input }});
                }});
                const buttons = Array.from(doc.querySelectorAll('button'));
                const addBtn = buttons.find(b => (b.textContent || '').includes('Agregar Item') && !b.disabled);
                if (addBtn) sequence.push({{ container: addBtn, input: addBtn, isButton: true }});
                
                return sequence;
            }}

            if (!doc._enterAsTabAttachedRec) {{
                doc._enterAsTabAttachedRec = true;
                doc.addEventListener('keydown', function(e) {{
                    if (e.key === 'Enter' || e.keyCode === 13) {{
                        const activeEl = doc.activeElement;
                        if (!activeEl) return;
                        if (activeEl.tagName === 'BUTTON' || activeEl.tagName === 'TEXTAREA') {{
                            return;
                        }}
                        if (activeEl.closest && activeEl.closest('div[data-testid="stSelectbox"]')) {{
                            return;
                        }}
                        const sequence = getFormSequence();
                        const currIdx = sequence.findIndex(item => item.container.contains(activeEl) || item.input === activeEl);
                        if (currIdx > -1 && currIdx < sequence.length - 1) {{
                            e.preventDefault();
                            e.stopPropagation();
                            const nextItem = sequence[currIdx + 1];
                            nextItem.input.focus();
                            if (nextItem.input.select) nextItem.input.select();
                        }}
                    }}
                }}, true);
            }}

            {focus_script}
        }})();

        const targetType = '{target_to_focus}';
        if (targetType) {{
            let attempts = 0;
            const maxAttempts = 25;
            const interval = setInterval(function() {{
                attempts++;
                try {{
                    const doc = window.parent.document;
                    if (targetType === 'entregados') {{
                        const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                        const entregadosWidget = numInputs.find(w => (w.innerText || '').includes('Entregados')) || numInputs[1] || numInputs[0];
                        if (entregadosWidget) {{
                            const input = entregadosWidget.querySelector('input');
                            if (input) {{
                                if (doc.activeElement !== input) {{
                                    if (doc.activeElement && typeof doc.activeElement.blur === 'function') {{
                                        try {{ doc.activeElement.blur(); }} catch(e) {{}}
                                    }}
                                    input.focus();
                                    if (typeof input.select === 'function') {{ try {{ input.select(); }} catch(e) {{}} }}
                                }} else {{
                                    if (typeof input.select === 'function') {{ try {{ input.select(); }} catch(e) {{}} }}
                                    if (attempts > 5) {{ clearInterval(interval); }}
                                }}
                            }}
                        }}
                    }} else if (targetType === 'articulo') {{
                        const selectboxes = doc.querySelectorAll('div[data-testid="stSelectbox"]');
                        if (selectboxes.length > 0) {{
                            const targetBox = selectboxes[selectboxes.length - 1];
                            const input = targetBox.querySelector('input') || targetBox.querySelector('div[role="combobox"]');
                            if (input) {{
                                if (doc.activeElement !== input) {{
                                    if (doc.activeElement && typeof doc.activeElement.blur === 'function') {{
                                        try {{ doc.activeElement.blur(); }} catch(e) {{}}
                                    }}
                                    input.focus();
                                    try {{ input.click(); }} catch(e) {{}}
                                }} else {{
                                    if (attempts > 5) {{ clearInterval(interval); }}
                                }}
                            }}
                        }}
                    }}
                }} catch(e) {{}}
                if (attempts >= maxAttempts) {{
                    clearInterval(interval);
                }}
            }}, 100);
        }}
    </script>
    """, height=0, width=0)

if __name__ == "__main__":
    remitos_ventas()