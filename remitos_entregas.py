import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import timedelta, datetime, date
import time
import config
from models import (
    get_clients_and_articles,
    save_remito
)
from gen_remito import gen_remito, process_generate_remito, is_local_app, get_remito_filename

st.set_page_config(layout="wide")

def clear_item_inputs():
    """Reinicia los valores de los inputs de items manteniendo la clave del selectbox."""
    st.session_state.entregados_input = 1
    st.session_state.observaciones_item_input = ""
    st.session_state.articulo_precargado = None
    st.session_state.precio_real_input = 0.0
    st.session_state.precio_original_articulo = 0.0
    st.session_state.articulo_selectbox_fixed = None

def new_remito():
    """Reinicia completamente el formulario para un nuevo remito."""
    st.session_state.remito_id = None
    st.session_state.items_data = pd.DataFrame(columns=[
        'Articulo', 'Descripción', 'Precio Real',
        'Entregados', 'Observaciones', 'id_articulo'
    ])
    st.session_state.cabecera_data = {
        'cliente_id': None,
        'fecha_entrega': None,
        'fecha_retiro': None,
        'observaciones': ''
    }
    st.session_state.cabecera_key = str(time.time())
    st.session_state.is_saved = False
    st.session_state.success_shown = False
    st.session_state.remito_generado_msg = None
    st.session_state.cliente_selected_display = None
    # Limpiar artículo precargado pero mantener clave del selectbox
    st.session_state.articulo_precargado = None
    clear_item_inputs()

def calculate_consignacion(items_df):
    """Calcula el total de items entregados."""
    if 'Entregados' in items_df.columns:
        return int(items_df['Entregados'].sum())
    return 0

def calculate_total_facturar(items_df, cliente_id, porc_dto):
    """
    Calcula el total a facturar considerando el descuento del cliente.
    Si cliente_id es None, retorna 'Ingrese el Cliente'.
    """
    if cliente_id is None:
        return "Ingrese el Cliente"

    if items_df.empty or 'Precio Real' not in items_df.columns or 'Entregados' not in items_df.columns:
        return "$ 0,00"

    precios = pd.to_numeric(items_df['Precio Real'], errors='coerce').fillna(0)
    entregados = pd.to_numeric(items_df['Entregados'], errors='coerce').fillna(0)
    
    dto_val = float(porc_dto) if (porc_dto is not None and pd.notna(porc_dto)) else 0.0
    factor = 1.0 - (dto_val / 100.0)

    total = (precios * entregados).sum() * factor
    formatted = f"{float(total):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {formatted}"

def remitos_entregas():
    st.title(config.TITULO_APP)
    st.header("Carga de Remitos - Entregas")

    if not "clientes_df" in st.session_state or not "articulos_df" in st.session_state:
        st.session_state.clientes_df, st.session_state.articulos_df = get_clients_and_articles()
        # Paso la columna boca a integros
        st.session_state.clientes_df['boca'] = st.session_state.clientes_df['boca'].astype('Int64')
    
    SENTINEL = "— Seleccione un artículo —"

    # Inicialización de session_state
    default_values = {
        "remito_id": None,
        "items_data": pd.DataFrame(columns=[
            "Articulo", "Descripción", "Precio Real",
            "Entregados", "Observaciones", "id_articulo"
        ]),
        "cabecera_data": {
            "cliente_id": None,
            "fecha_entrega": None,
            "fecha_retiro": None,
            "observaciones": ""
        },
        "entregados_input": 1,
        "observaciones_item_input": "",
        "precio_real_input": 0.0,
        "cabecera_key": "initial_cabecera",
        "should_clear_items": False,
        "should_reset_all": False,
        "show_confirm_modal": False,
        "is_form_disabled": False,
        "is_saved": False,
        "success_shown": False,
        "cliente_selected_display": None,
        "precios_actualizados": False,
        "articulo_precargado": None,
        "precio_original_articulo": 0.0,
        "focus_articulo": False
    }

    for key, default in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # Manejo de flags de rerun
    if st.session_state.should_clear_items:
        clear_item_inputs()
        st.session_state.should_clear_items = False
        st.session_state.focus_target = "articulo"

    if st.session_state.should_reset_all:
        new_remito()
        st.session_state.should_reset_all = False
        st.rerun()

    # Manejo el porcentaje de descuento aparte
    if not "porc_dto" in st.session_state:
        st.session_state.porc_dto = None

    # Control de estado del formulario
    st.session_state.is_form_disabled = st.session_state.show_confirm_modal

    # === SECCIÓN CABECERA ===
    st.subheader("Datos del Cliente")

    # Preparar opciones del cliente
    st.session_state.clientes_df['display_name'] = st.session_state.clientes_df.apply(
        lambda row: f"{row['razon_social']}  |  Boca: {row['boca']}" if pd.notna(row['boca']) else row['razon_social'],
        axis=1
    )

    options_list = st.session_state.clientes_df['display_name'].tolist()
    
    # Determinar el index predeterminado si ya hay un cliente seleccionado guardado
    default_client_index = None
    if st.session_state.get('cliente_selected_display') in options_list:
        default_client_index = options_list.index(st.session_state.cliente_selected_display)

    # Selectbox de cliente - simple y directo
    cliente_selection = st.selectbox(
        "Cliente:",
        options=options_list,
        index=default_client_index,
        placeholder="Seleccione un cliente...",
        key=f"cliente_selection_input_{st.session_state.cabecera_key}",
        disabled=st.session_state.is_form_disabled
    )

    # Manejar selección del cliente de forma directa
    if cliente_selection:
        matching_client = st.session_state.clientes_df.loc[st.session_state.clientes_df['display_name'] == cliente_selection]
        if matching_client.empty:
            # Fallback a buscar por razón social si por alguna extraña razón no coincide display_name
            selected_razon_social = cliente_selection.split("  |  Boca:")[0].strip()
            matching_client = st.session_state.clientes_df.loc[
                st.session_state.clientes_df['razon_social'].str.strip() == selected_razon_social
            ]

        if not matching_client.empty:
            client_data = matching_client.iloc[0]
            st.session_state.porc_dto = client_data["porc_dto"]
            st.session_state.cabecera_data['cliente_id'] = client_data['id']
            st.session_state.cliente_selected_display = cliente_selection

    # Campos de fecha y descuento
    col1, col2, col3 = st.columns(3, gap="small")

    with col1:
        val_fecha = st.session_state.cabecera_data.get('fecha_entrega') or datetime.now()
        fecha_entrega = st.date_input(
            "Fecha de Entrega",
            value=val_fecha,
            format="DD/MM/YYYY",
            key=f"fecha_entrega_{st.session_state.cabecera_key}",
            disabled=st.session_state.is_form_disabled
        )
        st.session_state.cabecera_data['fecha_entrega'] = fecha_entrega

    with col2:
        st.text_input(
            "Fecha de Retiro",
            disabled=True,
            key=f"fecha_retiro_{st.session_state.cabecera_key}"
        )
        st.session_state.cabecera_data['fecha_retiro'] = None

    with col3:
        # Mostrar descuento como métrica (no editable)
        porc_dto = st.session_state.porc_dto
        dto_display = f"{porc_dto}%" if pd.notna(porc_dto) else "Seleccione Cliente"
        st.metric(
            label="Descuento ( dato privado )",
            value=dto_display
        )

    # Observaciones de cabecera
    observaciones_cabecera = st.text_area(
        "Observaciones del Remito (notas privadas)",
        value=st.session_state.cabecera_data.get('observaciones', ''),
        key=f"observaciones_cabecera_input_{st.session_state.cabecera_key}",
        disabled=st.session_state.is_form_disabled
    )
    st.session_state.cabecera_data['observaciones'] = observaciones_cabecera

    # === SECCIÓN ITEMS ===
    st.header("Carga de Items")

    # Preparar opciones de artículos
    articulo_options_full = st.session_state.articulos_df.apply(
        lambda row: f"{row['nro_articulo']} - {row['descripcion']}", axis=1
    ).tolist()

    # Determinar el label dinámico para el selectbox de artículos
    articulo_label = "Artículo:"
    if st.session_state.cabecera_data.get('cliente_id') and st.session_state.cliente_selected_display:
        razon_social = st.session_state.cliente_selected_display.split("  |  Boca:")[0].strip()
        articulo_label = f"Artículos para {razon_social}:"

    # Selectbox de artículo
    articulo_sel_full = st.selectbox(
        articulo_label,
        options=articulo_options_full,
        index=None,
        placeholder="Seleccione un artículo...",
        key="articulo_selectbox_fixed",
        disabled=st.session_state.is_form_disabled,
        help="Seleccione un nuevo artículo o uno existente en la grilla para modificar o eliminar."
    )

    # Manejar selección de artículo
    articulo_sel = None
    if articulo_sel_full and not st.session_state.is_form_disabled:
        articulo_sel = articulo_sel_full.split(" - ")[0]
        
        # Verificar si necesitamos precargar datos O si el precio está en cero (siempre recargar si es cero)
        should_preload = (
            'articulo_precargado' not in st.session_state or 
            st.session_state.articulo_precargado != articulo_sel or
            st.session_state.precio_real_input <= 0  # ← SIEMPRE recargar si precio es cero o menor
        )
        
        if should_preload:
            st.session_state.articulo_precargado = articulo_sel
            
            # Pre-cargar datos si el artículo ya existe en la grilla
            if articulo_sel in st.session_state.items_data['Articulo'].values:
                row = st.session_state.items_data.loc[
                    st.session_state.items_data['Articulo'] == articulo_sel
                ].iloc[0]
                st.session_state.entregados_input = int(row['Entregados'])
                st.session_state.observaciones_item_input = row['Observaciones']
                st.session_state.precio_real_input = float(row['Precio Real'])
                st.session_state.precio_original_articulo = float(row['Precio Real'])
            else:
                # Cargar precio desde maestro de artículos
                matching_articulo = st.session_state.articulos_df.loc[
                    st.session_state.articulos_df['nro_articulo'] == articulo_sel
                ]
                if not matching_articulo.empty:
                    articulo_data = matching_articulo.iloc[0]
                    precio_maestro = float(articulo_data['precio_real'])
                    st.session_state.precio_real_input = precio_maestro
                    st.session_state.precio_original_articulo = precio_maestro
                    st.session_state.entregados_input = 1
                    st.session_state.observaciones_item_input = ""
                else:
                    st.error(f"Error: No se encontró el artículo {articulo_sel}")
                    st.session_state.precio_real_input = 0.0
                    st.session_state.precio_original_articulo = 0.0
            
            st.session_state.focus_target = "entregados"
            st.rerun()

    # Inputs de item
    col_entregados, col_precio, col_observ = st.columns([1, 1, 3], gap="small")

    with col_entregados:
        st.number_input(
            "Entregados:",
            min_value=1,
            step=1,
            key="entregados_input",
            disabled=st.session_state.is_form_disabled
        )

    with col_precio:
        st.number_input(
            "Precio Real:",
            min_value=0.0,
            step=500.00,
            key="precio_real_input",
            disabled=st.session_state.is_form_disabled
        )

    with col_observ:
        st.text_input(
            "Observaciones del Item:",
            key="observaciones_item_input",
            disabled=st.session_state.is_form_disabled
        )

    # Botones de acción para items
    articulo_existe = (articulo_sel is not None and
                      articulo_sel in st.session_state.items_data['Articulo'].values)

    c1, c2, c3 = st.columns(3, gap="small")

    with c1:
        add_clicked = st.button(
            "Agregar Item ➕",
            width="stretch",
            disabled=(articulo_sel is None or articulo_existe or
                     st.session_state.is_form_disabled)
        )

    with c2:
        mod_clicked = st.button(
            "Modificar Item ✍️",
            width="stretch",
            disabled=(articulo_sel is None or not articulo_existe or
                     st.session_state.is_form_disabled)
        )

    with c3:
        del_clicked = st.button(
            "Eliminar Item 🗑️",
            width="stretch",
            disabled=(articulo_sel is None or not articulo_existe or
                     st.session_state.is_form_disabled)
        )

    porc_dto_val = float(st.session_state.get('porc_dto', 0) or 0)

    # Procesar acciones de items
    if add_clicked:
        articulo_info = st.session_state.articulos_df[st.session_state.articulos_df['nro_articulo'] == articulo_sel].iloc[0]
        costo_val = float(articulo_info['costo']) if ('costo' in articulo_info and pd.notna(articulo_info['costo'])) else 0.0
        p_neto = st.session_state.precio_real_input * (1.0 - (porc_dto_val / 100.0))

        if st.session_state.entregados_input < 1:
            st.error("La cantidad entregada debe ser 1 o mayor.")
        elif st.session_state.precio_real_input <= 0:
            st.error("El precio real debe ser mayor a cero. Vuelva a seleccionar el artículo.")
        elif p_neto < costo_val:
            st.error(f"⚠️ El Precio Real (\${st.session_state.precio_real_input:,.2f}) no deja utilidad con el descuento del {porc_dto_val:.0f}% (Neto: \${p_neto:,.2f} vs Costo: \${costo_val:,.2f}).")
        else:
            new_item = {
                'Articulo': articulo_sel,
                'Descripción': articulo_info['descripcion'],
                'Precio Real': st.session_state.precio_real_input,
                'Entregados': st.session_state.entregados_input,
                'Observaciones': st.session_state.observaciones_item_input,
                'id_articulo': articulo_info['id']
            }

            if st.session_state.items_data.empty:
                st.session_state.items_data = pd.DataFrame([new_item])
            else:
                st.session_state.items_data = pd.concat(
                    [st.session_state.items_data, pd.DataFrame([new_item])],
                    ignore_index=True
                )

            st.session_state.should_clear_items = True
            st.rerun()

    if mod_clicked and articulo_existe:
        articulo_info = st.session_state.articulos_df[st.session_state.articulos_df['nro_articulo'] == articulo_sel].iloc[0]
        costo_val = float(articulo_info['costo']) if ('costo' in articulo_info and pd.notna(articulo_info['costo'])) else 0.0
        p_neto = st.session_state.precio_real_input * (1.0 - (porc_dto_val / 100.0))

        if st.session_state.entregados_input < 1:
            st.error("La cantidad entregada debe ser 1 o mayor.")
        elif p_neto < costo_val:
            st.error(f"⚠️ El Precio Real (\${st.session_state.precio_real_input:,.2f}) no deja utilidad con el descuento del {porc_dto_val:.0f}% (Neto: \${p_neto:,.2f} vs Costo: \${costo_val:,.2f}).")
        else:
            idx = st.session_state.items_data.index[
                st.session_state.items_data['Articulo'] == articulo_sel
            ][0]

            st.session_state.items_data.loc[idx, :] = {
                'Articulo': articulo_sel,
                'Descripción': articulo_info['descripcion'],
                'Precio Real': st.session_state.precio_real_input,
                'Entregados': st.session_state.entregados_input,
                'Observaciones': st.session_state.observaciones_item_input,
                'id_articulo': articulo_info['id']
            }
            st.success("Artículo modificado")
            st.session_state.should_clear_items = True
            st.rerun()

    if del_clicked and articulo_existe:
        st.session_state.items_data = st.session_state.items_data[
            st.session_state.items_data['Articulo'] != articulo_sel
        ].reset_index(drop=True)
        st.warning("Artículo eliminado")
        st.session_state.should_clear_items = True
        st.rerun()

    # === MOSTRAR ITEMS ACTUALES ===
    st.header("Items actuales del Remito")

    if not st.session_state.items_data.empty:
        # Se muestra el dataframe sin edición
        st.dataframe(
            st.session_state.items_data[['Articulo', 'Descripción', 'Precio Real', 'Entregados', 'Observaciones']],
            hide_index=True,
            column_config={
                "Articulo": st.column_config.Column(width="medium"),
                "Descripción": st.column_config.Column(width="medium"),
                "Precio Real": st.column_config.NumberColumn(format="$%,.2f", width="small"),
                "Entregados": st.column_config.Column(width="small"),
                "Observaciones": st.column_config.Column(width="small")
            }
        )
    else:
        st.info("Sin items cargados todavía.")

    # Mostrar métricas de consignación y total a facturar a la misma altura (Total a Facturar bien marginado a la derecha)
    col_m1, col_m2 = st.columns(2, gap="small")
    with col_m1:
        st.metric(
            "Consignación (Total Entregados)",
            value=calculate_consignacion(st.session_state.items_data)
        )
    with col_m2:
        cliente_id = st.session_state.cabecera_data.get('cliente_id')
        porc_dto = st.session_state.get('porc_dto')
        total_facturar_val = calculate_total_facturar(st.session_state.items_data, cliente_id, porc_dto)
        
        val_color = "#ff4b4b" if total_facturar_val == "Ingrese el Cliente" else "var(--text-color, #ffffff)"
        val_font_size = "1.5rem" if total_facturar_val == "Ingrese el Cliente" else "2rem"

        st.markdown(f"""
        <div style="text-align: right; width: 100%;">
            <div style="font-size: 0.875rem; color: rgba(250, 250, 250, 0.7); font-weight: 400; margin-bottom: 4px;">Total a Facturar</div>
            <div style="font-size: {val_font_size}; font-weight: 600; color: {val_color}; line-height: 1.2;">{total_facturar_val}</div>
        </div>
        """, unsafe_allow_html=True)

    # === BOTONES PRINCIPALES ===
    st.header("Acciones del Remito")

    # Verificar si hay algún ítem con precio real que no deje utilidad
    has_item_price_error = False
    if not st.session_state.items_data.empty and 'articulos_df' in st.session_state:
        porc_dto_val = float(st.session_state.get('porc_dto', 0) or 0)
        for _, row in st.session_state.items_data.iterrows():
            art_num = row['Articulo']
            p_real = float(row['Precio Real'])
            p_neto = p_real * (1.0 - (porc_dto_val / 100.0))
            matching_art = st.session_state.articulos_df[st.session_state.articulos_df['nro_articulo'] == art_num]
            if not matching_art.empty:
                costo_val = float(matching_art.iloc[0]['costo']) if ('costo' in matching_art.iloc[0] and pd.notna(matching_art.iloc[0]['costo'])) else 0.0
                if p_neto < costo_val and costo_val > 0:
                    has_item_price_error = True
                    break

    if has_item_price_error:
        st.error("⚠️ No se puede guardar el remito: contiene artículos cuyo Precio Real no deja utilidad (queda por debajo del Costo con el descuento aplicado).")

    is_remito_saved = st.session_state.remito_id is not None
    can_save = (st.session_state.cabecera_data['cliente_id'] is not None and
                not st.session_state.items_data.empty and
                not has_item_price_error)

    col_buttons = st.columns(3, gap="small")

    # Botón Guardar
    say_error = False
    with col_buttons[0]:
        if st.button("Guardar Remito", type="primary", width="stretch",
                    disabled=st.session_state.is_form_disabled or is_remito_saved or not can_save):
            if not can_save:
                say_error = True
            else:
                remito_id, precios_actualizados = save_remito(
                    st.session_state.cabecera_data['cliente_id'],
                    st.session_state.cabecera_data['fecha_entrega'],
                    st.session_state.cabecera_data['fecha_retiro'],
                    st.session_state.cabecera_data['observaciones'],
                    st.session_state.porc_dto,
                    st.session_state.items_data
                )
                st.session_state.remito_id = remito_id
                st.session_state.precios_actualizados = precios_actualizados
                # Forzar rerun para actualizar el estado de los botones
                st.rerun()

    # Botón Nuevo Remito
    with col_buttons[1]:
        nuevo_remito_disabled = st.session_state.is_form_disabled

        if st.button("Nuevo Remito", width="stretch",
                    disabled=nuevo_remito_disabled):
            st.session_state.porc_dto = None
            if st.session_state.items_data.empty or is_remito_saved:
                st.session_state.should_reset_all = True
                st.rerun()
            else:
                st.session_state.show_confirm_modal = True
                st.rerun()

    # Botón Generar Remito
    with col_buttons[2]:
        if is_remito_saved:
            if is_local_app():
                if st.button(f"Generar Remito en Excel #{st.session_state.remito_id}", width="stretch", key=f"btn_gen_{st.session_state.remito_id}"):
                    last_folder = st.session_state.get('last_used_folder')
                    success, msg, chosen_folder = process_generate_remito(st.session_state.remito_id, is_retiro=False, default_dir=last_folder)
                    if success:
                        st.session_state.last_used_folder = chosen_folder
                        st.session_state.remito_generado_msg = f"📁 Remito #{st.session_state.remito_id} guardado exitosamente en: **{msg}**"
                        st.toast(f"Remito #{st.session_state.remito_id} guardado con éxito", icon="📁")
                    else:
                        st.session_state.remito_generado_msg = None
                        st.info(msg)
                    st.rerun()
            else:
                excel_buffer = gen_remito(st.session_state.remito_id, is_retiro=False)
                st.download_button(
                    label=f"Generar Remito en Excel #{st.session_state.remito_id}",
                    width="stretch",
                    data=excel_buffer,
                    file_name=get_remito_filename(st.session_state.remito_id, is_retiro=False),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.button("Generar Remito en Excel", width="stretch", disabled=True)

    if say_error:
        st.error("Por favor, seleccione un cliente y agregue al menos un item.")

    if st.session_state.get('remito_generado_msg'):
        st.success(st.session_state.remito_generado_msg)

    # Mensaje de éxito fuera de las columnas (ocupa todo el ancho)
    if st.session_state.get('remito_id') and not st.session_state.get('success_shown', False):
        st.success(f"🎉 Remito #{st.session_state.remito_id} guardado con éxito!")
        if st.session_state.precios_actualizados:
            st.success("💰 ¡Los precios modificados fueron actualizados en el maestro de artículos!")
        st.balloons()
        # Marcar que ya se mostró el mensaje para evitar que se repita
        st.session_state.success_shown = True

    # === MODAL DE CONFIRMACIÓN ===
    if st.session_state.show_confirm_modal:
        st.warning("Hay artículos cargados en la grilla. ¿Desea continuar y borrar todos los datos del remito?")

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

    # CSS para ocultar el contenedor de componentes de altura cero y eliminar huecos negros
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

    # Footer
    st.markdown(f"`{config.FOOTER_APP}`")

    # Componente para navegación con Enter como Tab y foco automático
    target_to_focus = st.session_state.get('focus_target', '')
    if target_to_focus:
        st.session_state.focus_target = ''

    components.html(f"""
    <script>
        (function() {{
            try {{
                const doc = window.parent.document;

                // Desvincular escuchadores anteriores si existían
                if (window.parent._selectHandlerEntregas) {{
                    doc.removeEventListener('focusin', window.parent._selectHandlerEntregas, true);
                    doc.removeEventListener('click', window.parent._selectHandlerEntregas, true);
                }}
                if (window.parent._selectionChangeHandlerEntregas) {{
                    doc.removeEventListener('selectionchange', window.parent._selectionChangeHandlerEntregas, true);
                }}

                function doSelect(el) {{
                    if (!el || doc.activeElement !== el) return;
                    if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'button' || el.type === 'submit') return;
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
                }}

                window.parent._selectHandlerEntregas = function(e) {{
                    const target = e.target;
                    if (!target) return;
                    const tag = (target.tagName || '').toUpperCase();
                    if (tag !== 'INPUT' && tag !== 'TEXTAREA') return;
                    if (target.type === 'checkbox' || target.type === 'radio' || target.type === 'button' || target.type === 'submit') return;

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

                window.parent._selectionChangeHandlerEntregas = function() {{
                    const active = doc.activeElement;
                    if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {{
                        if (active.dataset.autoSelecting === 'true') {{
                            if (active.selectionStart !== 0 || active.selectionEnd !== active.value.length) {{
                                doSelect(active);
                            }}
                        }}
                    }}
                }};

                doc.addEventListener('focusin', window.parent._selectHandlerEntregas, true);
                doc.addEventListener('click', window.parent._selectHandlerEntregas, true);
                doc.addEventListener('selectionchange', window.parent._selectionChangeHandlerEntregas, true);

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
                    const numInputs = doc.querySelectorAll('div[data-testid="stNumberInput"]');
                    numInputs.forEach(w => {{
                        const input = w.querySelector('input');
                        if (input) sequence.push({{ container: w, input: input }});
                    }});
                    const textInputs = doc.querySelectorAll('div[data-testid="stTextInput"]');
                    textInputs.forEach(w => {{
                        const input = w.querySelector('input');
                        if (input) sequence.push({{ container: w, input: input }});
                    }});
                    const buttons = Array.from(doc.querySelectorAll('button'));
                    const addBtn = buttons.find(b => (b.textContent || '').includes('Agregar Item') && !b.disabled);
                    if (addBtn) sequence.push({{ container: addBtn, input: addBtn, isButton: true }});
                    
                    return sequence;
                }}

                if (!doc._enterAsTabAttached) {{
                    doc._enterAsTabAttached = true;
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
            }} catch(e) {{}}
        }})();

        const targetType = '{target_to_focus}';
        if (targetType) {{
            setTimeout(function() {{
                try {{
                    const doc = window.parent.document;
                    if (targetType === 'entregados') {{
                        const numInputs = doc.querySelectorAll('div[data-testid="stNumberInput"] input');
                        if (numInputs.length > 0) {{
                            const target = numInputs[0];
                            target.focus();
                            if (target.select) target.select();
                        }}
                    }} else if (targetType === 'articulo') {{
                        const selectboxes = doc.querySelectorAll('div[data-testid="stSelectbox"]');
                        if (selectboxes.length > 0) {{
                            const targetBox = selectboxes[selectboxes.length - 1];
                            const input = targetBox.querySelector('input') || targetBox.querySelector('div[role="combobox"]');
                            if (input) {{
                                input.focus();
                                input.click();
                            }}
                        }}
                    }}
                }} catch(e) {{}}
            }}, 300);
        }}
    </script>
    """, height=0, width=0)

if __name__ == "__main__":
    remitos_entregas()