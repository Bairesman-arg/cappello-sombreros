import streamlit as st
import pandas as pd
from datetime import timedelta, datetime, date
import time
import config
from models import (
    get_clients_and_articles,
    save_remito
)
from gen_remito import gen_remito, process_generate_remito, is_local_app, get_remito_filename

def clear_item_inputs():
    """Reinicia los valores de los inputs de items manteniendo la clave del selectbox."""
    st.session_state.entregados_input = 1
    st.session_state.observaciones_item_input = ""
    st.session_state.articulo_precargado = None
    st.session_state.precio_real_input = 0.0
    st.session_state.precio_original_articulo = 0.0
    st.session_state.articulo_selectbox_fixed = None
    st.session_state.pop("pending_selected_item_ent", None)
    st.session_state.pop("pending_articulo_selectbox_fixed", None)
    st.session_state.ent_grid_version = st.session_state.get("ent_grid_version", 0) + 1
    for k in list(st.session_state.keys()):
        if k.startswith("ent_base_df_") or k.startswith("editor_ent_"):
            st.session_state.pop(k, None)

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
    for k in list(st.session_state.keys()):
        if k.startswith("ent_base_df_") or k.startswith("editor_ent_"):
            st.session_state.pop(k, None)
    st.session_state.ent_grid_version = 0
    clear_item_inputs()

def calculate_consignacion(items_df):
    """Calcula el total de items entregados."""
    if 'Entregados' in items_df.columns and not items_df.empty:
        return int(pd.to_numeric(items_df['Entregados'], errors='coerce').fillna(0).sum())
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
        "focus_articulo": False,
        "ent_grid_version": 0
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
    st.markdown('<div id="seccion_carga_items_ent" style="scroll-margin-top: 80px;"></div>', unsafe_allow_html=True)
    st.header("Carga de Items")

    st.markdown(
        """
        <style>
            /* Ocultar el botón 'x' (limpiar selección) en los controles selectbox */
            div[data-baseweb="select"] button {
                display: none !important;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Preparar opciones de artículos
    articulo_options_full = st.session_state.articulos_df.apply(
        lambda row: f"{row['nro_articulo']} - {row['descripcion']}", axis=1
    ).tolist()

    # Determinar el label dinámico para el selectbox de artículos
    articulo_label = "Artículo:"
    if st.session_state.cabecera_data.get('cliente_id') and st.session_state.cliente_selected_display:
        razon_social = st.session_state.cliente_selected_display.split("  |  Boca:")[0].strip()
        articulo_label = f"Artículos para {razon_social}:"

    if "pending_selected_item_ent" in st.session_state:
        pending = st.session_state.pop("pending_selected_item_ent")
        if pending:
            st.session_state.articulo_selectbox_fixed = pending.get("articulo_selectbox_fixed")
            st.session_state.entregados_input = pending.get("entregados_input", 1)
            st.session_state.precio_real_input = pending.get("precio_real_input", 0.0)
            st.session_state.precio_original_articulo = pending.get("precio_real_input", 0.0)
            st.session_state.observaciones_item_input = pending.get("observaciones_item_input", "")
            st.session_state.articulo_precargado = pending.get("articulo_precargado")

    if "pending_articulo_selectbox_fixed" in st.session_state:
        pending_val = st.session_state.pop("pending_articulo_selectbox_fixed")
        if pending_val:
            st.session_state["articulo_selectbox_fixed"] = pending_val

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
                    st.session_state["pending_articulo_selectbox_fixed"] = f"{articulo_data['nro_articulo']} - {articulo_data['descripcion']}"
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

    c1, c2, c3, c4 = st.columns(4, gap="small")

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

    with c4:
        clear_form_clicked = st.button(
            "Limpiar Formulario 🧹",
            width="stretch",
            disabled=(st.session_state.is_form_disabled or
                     (articulo_sel is None and not st.session_state.observaciones_item_input and st.session_state.precio_real_input <= 0))
        )

    if clear_form_clicked:
        st.session_state.should_clear_items = True
        st.session_state.ent_grid_version = st.session_state.get("ent_grid_version", 0) + 1
        st.rerun()

    if articulo_existe:
        st.success("Artículo existente en el nuevo Remito. Solo puede ser Modificado o Eliminado, o cancele la operación Limpiando el Formulario.")

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
            st.error(f"⚠️ El Precio Real (${st.session_state.precio_real_input:,.2f}) no deja utilidad con el descuento del {porc_dto_val:.0f}% (Neto: ${p_neto:,.2f} vs Costo: ${costo_val:,.2f}).")
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
            st.session_state.ent_grid_version = st.session_state.get("ent_grid_version", 0) + 1
            st.rerun()

    if mod_clicked and articulo_existe:
        articulo_info = st.session_state.articulos_df[st.session_state.articulos_df['nro_articulo'] == articulo_sel].iloc[0]
        costo_val = float(articulo_info['costo']) if ('costo' in articulo_info and pd.notna(articulo_info['costo'])) else 0.0
        p_neto = st.session_state.precio_real_input * (1.0 - (porc_dto_val / 100.0))

        if st.session_state.entregados_input < 1:
            st.error("La cantidad entregada debe ser 1 o mayor.")
        elif p_neto < costo_val:
            st.error(f"⚠️ El Precio Real (${st.session_state.precio_real_input:,.2f}) no deja utilidad con el descuento del {porc_dto_val:.0f}% (Neto: ${p_neto:,.2f} vs Costo: ${costo_val:,.2f}).")
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
            st.session_state.ent_grid_version = st.session_state.get("ent_grid_version", 0) + 1
            st.rerun()

    if del_clicked and articulo_existe:
        st.session_state.items_data = st.session_state.items_data[
            st.session_state.items_data['Articulo'] != articulo_sel
        ].reset_index(drop=True)
        st.warning("Artículo eliminado")
        st.session_state.should_clear_items = True
        st.session_state.ent_grid_version = st.session_state.get("ent_grid_version", 0) + 1
        st.rerun()

    # === MOSTRAR ITEMS ACTUALES ===
    st.header("Items actuales del Remito")

    if not st.session_state.items_data.empty:
        grid_ver = st.session_state.get("ent_grid_version", 0)
        editor_key = f"editor_ent_{grid_ver}"
        base_df_key = f"ent_base_df_{grid_ver}"

        if base_df_key not in st.session_state:
            df_init = st.session_state.items_data.copy().reset_index(drop=True)
            if "Seleccionado" not in df_init.columns:
                df_init.insert(0, "Seleccionado", False)
            st.session_state[base_df_key] = df_init

        df_to_show = st.session_state[base_df_key]

        st.markdown("`Seleccione la primera columna de la grilla inferior para modificar o eliminar un ítem. Para editar en grilla: ENTER -> modificar -> ENTER`")

        num_items_ent = len(df_to_show)
        rows_to_show_ent = min(max(num_items_ent, 1), 10)
        grid_height_ent = int(39 + (rows_to_show_ent * 35.5) + 4)

        if st.session_state.is_form_disabled:
            disabled_cols = [c for c in df_to_show.columns]
        elif articulo_existe:
            disabled_cols = [c for c in df_to_show.columns if c != "Seleccionado"]
        else:
            disabled_cols = ["Articulo", "Descripción"]

        edited_df = st.data_editor(
            df_to_show,
            hide_index=True,
            width="stretch",
            height=grid_height_ent,
            column_order=["Seleccionado", "Articulo", "Descripción", "Precio Real", "Entregados", "Observaciones"],
            column_config={
                "Seleccionado": st.column_config.CheckboxColumn(
                    "✔",
                    help="Marque la casilla de verificación para modificar o eliminar este artículo.",
                    width=40
                ),
                "Articulo": st.column_config.TextColumn("Artículo", disabled=True, width="medium"),
                "Descripción": st.column_config.TextColumn("Descripción", disabled=True, width="medium"),
                "Precio Real": st.column_config.NumberColumn(
                    "Precio Real",
                    min_value=0.01,
                    step=100.0,
                    format="$%.2f",
                    width="small"
                ),
                "Entregados": st.column_config.NumberColumn(
                    "Entregados",
                    min_value=1,
                    step=1,
                    width="small"
                ),
                "Observaciones": st.column_config.TextColumn("Observaciones", width="medium"),
            },
            disabled=disabled_cols,
            key=editor_key,
            num_rows="fixed"
        )

        # Sincronizar inmediatamente los cambios hacia items_data cuando no está en modo modificación por form
        if not articulo_existe and not st.session_state.is_form_disabled:
            cols_to_sync = [c for c in edited_df.columns if c != "Seleccionado" and c in st.session_state.items_data.columns]
            for col in cols_to_sync:
                st.session_state.items_data[col] = edited_df[col].values

            if editor_key in st.session_state:
                editor_changes = st.session_state[editor_key]
                if isinstance(editor_changes, dict) and 'edited_rows' in editor_changes:
                    for row_idx_str, changes in editor_changes['edited_rows'].items():
                        row_idx = int(row_idx_str)
                        for col_name, new_val in changes.items():
                            if col_name != "Seleccionado" and col_name in st.session_state.items_data.columns:
                                st.session_state.items_data.loc[row_idx, col_name] = new_val

        if "Seleccionado" in edited_df.columns:
            selected_idxs = edited_df.index[edited_df["Seleccionado"] == True].tolist()
            if selected_idxs:
                idx = selected_idxs[0]
                selected_row = edited_df.loc[idx]
                nro_art = str(selected_row["Articulo"])

                matching_opts = [opt for opt in articulo_options_full if opt.startswith(f"{nro_art} - ")]
                sel_option = matching_opts[0] if matching_opts else None

                st.session_state.pending_selected_item_ent = {
                    "articulo_selectbox_fixed": sel_option,
                    "entregados_input": int(selected_row["Entregados"]),
                    "precio_real_input": float(selected_row["Precio Real"]),
                    "observaciones_item_input": str(selected_row["Observaciones"]) if pd.notna(selected_row["Observaciones"]) else "",
                    "articulo_precargado": nro_art
                }
                st.session_state.ent_grid_version = grid_ver + 1
                st.session_state.scroll_to_carga_ent = True
                st.session_state.focus_target = "entregados"
                st.rerun()
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

    # VALIDAR grilla
    items_precio_invalidos = pd.DataFrame()
    items_entregados_invalidos = pd.DataFrame()
    items_precio_menor_costo = []
    has_item_price_error = False

    if not st.session_state.items_data.empty:
        try:
            if "Precio Real" in st.session_state.items_data.columns:
                p_real_ser = pd.to_numeric(st.session_state.items_data["Precio Real"], errors="coerce").fillna(0)
                items_precio_invalidos = st.session_state.items_data[p_real_ser <= 0]
                if not items_precio_invalidos.empty:
                    arts = items_precio_invalidos["Articulo"].tolist()
                    st.warning(f"⚠️ Los artículos [{', '.join(str(x) for x in arts)}] tienen un Precio Real inválido (debe ser mayor a 0). Corregir antes de guardar.")

            if "Entregados" in st.session_state.items_data.columns:
                ent_ser = pd.to_numeric(st.session_state.items_data["Entregados"], errors="coerce").fillna(0)
                items_entregados_invalidos = st.session_state.items_data[ent_ser <= 0]
                if not items_entregados_invalidos.empty:
                    arts = items_entregados_invalidos["Articulo"].tolist()
                    st.warning(f"⚠️ Los artículos [{', '.join(str(x) for x in arts)}] tienen una cantidad Entregados inválida (debe ser 1 o mayor). Corregir antes de guardar.")

            if "articulos_df" in st.session_state and "Precio Real" in st.session_state.items_data.columns:
                porc_dto_val = float(st.session_state.get('porc_dto', 0) or 0)
                for _, row in st.session_state.items_data.iterrows():
                    art_num = row['Articulo']
                    p_real = float(row['Precio Real']) if pd.notna(row['Precio Real']) else 0.0
                    p_neto = p_real * (1.0 - (porc_dto_val / 100.0))
                    matching_art = st.session_state.articulos_df[st.session_state.articulos_df['nro_articulo'] == art_num]
                    if not matching_art.empty:
                        costo_val = float(matching_art.iloc[0]['costo']) if ('costo' in matching_art.iloc[0] and pd.notna(matching_art.iloc[0]['costo'])) else 0.0
                        if p_neto < costo_val and costo_val > 0:
                            items_precio_menor_costo.append(art_num)
                if items_precio_menor_costo:
                    has_item_price_error = True
                    if porc_dto_val > 0:
                        st.warning(f"⚠️ Los artículos [{', '.join(str(x) for x in items_precio_menor_costo)}] tienen un Precio Real que no deja utilidad con el descuento del {porc_dto_val:.0f}% (queda por debajo del Costo). Corregir antes de guardar.")
                    else:
                        st.warning(f"⚠️ Los artículos [{', '.join(str(x) for x in items_precio_menor_costo)}] tienen un Precio Real que no deja utilidad (es menor a su Costo). Corregir antes de guardar.")
        except Exception as e:
            st.error(f"Error en validación: {str(e)}")

    is_remito_saved = st.session_state.remito_id is not None
    can_save = (st.session_state.cabecera_data['cliente_id'] is not None and
                not st.session_state.items_data.empty and
                items_precio_invalidos.empty and
                items_entregados_invalidos.empty and
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

        col_confirm, col_cancel = st.columns(2, gap="small")

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

    scroll_to_carga = st.session_state.pop('scroll_to_carga_ent', False)
    exec_nonce = time.time_ns()

    config.render_html(f"""
    <!-- exec_nonce: {exec_nonce} -->
    <script>
        (function() {{
            const _execNonce = "{exec_nonce}";
            try {{
                const doc = window.parent.document;
                const pWin = window.parent;

                // Función auxiliar para seleccionar todo el texto de un input
                function doSelect(el) {{
                    if (!el || doc.activeElement !== el) return;
                    if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'button' || el.type === 'submit') return;
                    try {{ if (typeof el.select === 'function') el.select(); }} catch(e) {{}}
                    try {{ if (typeof el.setSelectionRange === 'function' && el.value !== undefined) el.setSelectionRange(0, el.value.length); }} catch(e) {{}}
                }}

                // Limpieza de escuchadores previos
                if (pWin._selectHandlerEntregas) {{
                    doc.removeEventListener('focusin', pWin._selectHandlerEntregas, true);
                    doc.removeEventListener('click', pWin._selectHandlerEntregas, true);
                }}
                if (pWin._selectionChangeHandlerEntregas) {{
                    doc.removeEventListener('selectionchange', pWin._selectionChangeHandlerEntregas, true);
                }}
                if (pWin._keyHandlerEntregas) {{
                    doc.removeEventListener('keydown', pWin._keyHandlerEntregas, true);
                }}

                // Autoselección de texto al enfocar
                pWin._selectHandlerEntregas = function(e) {{
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
                        setTimeout(function() {{ doSelect(target); }}, 50);
                        setTimeout(function() {{ doSelect(target); }}, 150);
                        setTimeout(function() {{ doSelect(target); }}, 300);
                        requestAnimationFrame(function() {{ doSelect(target); }});
                    }}
                    runPasses();
                }};

                pWin._selectionChangeHandlerEntregas = function() {{
                    const active = doc.activeElement;
                    if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA')) {{
                        if (active.dataset.autoSelecting === 'true') {{
                            if (active.selectionStart !== 0 || active.selectionEnd !== active.value.length) {{
                                doSelect(active);
                            }}
                        }}
                    }}
                }};

                doc.addEventListener('focusin', pWin._selectHandlerEntregas, true);
                doc.addEventListener('click', pWin._selectHandlerEntregas, true);
                doc.addEventListener('selectionchange', pWin._selectionChangeHandlerEntregas, true);

                doc.addEventListener('keydown', function(e) {{
                    if (e.target && e.target.dataset) delete e.target.dataset.autoSelecting;
                }}, true);

                doc.addEventListener('focusout', function(e) {{
                    if (e.target && e.target.dataset) delete e.target.dataset.autoSelecting;
                }}, true);

                // Función para seleccionar la primera opción o la opción activa en BaseWeb Select
                function triggerOptionClick(targetOpt) {{
                    if (!targetOpt) return;
                    const rect = targetOpt.getBoundingClientRect();
                    const clientX = rect.left + rect.width / 2;
                    const clientY = rect.top + rect.height / 2;

                    // 1. Invocar props directas de React si existen
                    const allNodes = [targetOpt, ...Array.from(targetOpt.querySelectorAll('*')), targetOpt.parentElement];
                    for (let i = 0; i < allNodes.length; i++) {{
                        const node = allNodes[i];
                        if (!node) continue;
                        const nKeys = Object.keys(node);
                        for (let j = 0; j < nKeys.length; j++) {{
                            const k = nKeys[j];
                            if (k.startsWith('__reactProps$') || k.startsWith('__reactEventHandlers$')) {{
                                const props = node[k];
                                if (props) {{
                                    const mockEvt = {{
                                        preventDefault: function() {{}},
                                        stopPropagation: function() {{}},
                                        bubbles: true,
                                        cancelable: true,
                                        target: node,
                                        currentTarget: node,
                                        clientX: clientX,
                                        clientY: clientY
                                    }};
                                    if (typeof props.onClick === 'function') try {{ props.onClick(mockEvt); }} catch(e) {{}}
                                    if (typeof props.onMouseDown === 'function') try {{ props.onMouseDown(mockEvt); }} catch(e) {{}}
                                }}
                            }}
                        }}
                    }}

                    // 2. Disparar eventos DOM nativos de puntero y ratón con coordenadas
                    const targetEl = targetOpt.querySelector('span, div, p') || targetOpt;
                    ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(function(evtName) {{
                        try {{
                            const evt = new pWin.MouseEvent(evtName, {{
                                bubbles: true,
                                cancelable: true,
                                view: pWin,
                                composed: true,
                                clientX: clientX,
                                clientY: clientY,
                                buttons: 1
                            }});
                            targetEl.dispatchEvent(evt);
                            targetOpt.dispatchEvent(evt);
                        }} catch(e1) {{
                            try {{
                                const evt = new MouseEvent(evtName, {{ bubbles: true, cancelable: true, clientX: clientX, clientY: clientY, buttons: 1 }});
                                targetEl.dispatchEvent(evt);
                                targetOpt.dispatchEvent(evt);
                            }} catch(e2) {{}}
                        }}
                    }});
                    try {{ targetEl.click(); }} catch(e) {{}}
                    try {{ targetOpt.click(); }} catch(e) {{}}
                }}

                // Función para obtener el botón de acción activo (Agregar Item o Modificar Item)
                function getActionButton() {{
                    const buttons = Array.from(doc.querySelectorAll('button'));
                    const addBtn = buttons.find(b => (b.textContent || '').includes('Agregar Item') && !b.disabled);
                    if (addBtn) return addBtn;
                    const modBtn = buttons.find(b => (b.textContent || '').includes('Modificar Item') && !b.disabled);
                    if (modBtn) return modBtn;
                    return null;
                }}

                // Secuencia exacta del formulario de items para Enter
                function getFormSequence() {{
                    const sequence = [];
                    
                    // 1. Selector de artículos
                    const selectboxes = Array.from(doc.querySelectorAll('div[data-testid="stSelectbox"]'));
                    if (selectboxes.length > 0) {{
                        const artBox = selectboxes[selectboxes.length - 1];
                        const input = artBox.querySelector('input');
                        if (input && !input.disabled) sequence.push({{ container: artBox, input: input }});
                    }}
                    
                    // 2. Entregados
                    const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                    const entWidget = numInputs.find(w => (w.innerText || w.textContent || '').includes('Entregados'));
                    if (entWidget) {{
                        const input = entWidget.querySelector('input');
                        if (input && !input.disabled) sequence.push({{ container: entWidget, input: input }});
                    }}
                    
                    // 3. Botón de acción: Agregar Item o Modificar Item (salto directo desde Entregados)
                    const actionBtn = getActionButton();
                    if (actionBtn) sequence.push({{ container: actionBtn, input: actionBtn, isButton: true }});
                    
                    return sequence;
                }}

                // Handler de TECLADO
                pWin._keyHandlerEntregas = function(e) {{
                    if (e.key === 'Enter' || e.keyCode === 13 || e.key === 'Tab' || e.keyCode === 9) {{
                        const activeEl = doc.activeElement;
                        if (!activeEl) return;
                        if (activeEl.tagName === 'TEXTAREA') return;

                        // Si el foco está en el selector de artículos
                        if (activeEl.closest && activeEl.closest('div[data-testid="stSelectbox"]')) {{
                            // Si es TAB: siempre pasar al siguiente campo (Entregados)
                            if (e.key === 'Tab' || e.keyCode === 9) {{
                                const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                                const entregadosWidget = numInputs.find(w => (w.innerText || w.textContent || '').includes('Entregados')) || numInputs[0];
                                if (entregadosWidget) {{
                                    const input = entregadosWidget.querySelector('input');
                                    if (input) {{
                                        e.preventDefault();
                                        e.stopPropagation();
                                        input.focus();
                                        doSelect(input);
                                        return;
                                    }}
                                }}
                                return;
                            }}

                            // Si es ENTER:
                            if (e.key === 'Enter' || e.keyCode === 13) {{
                                const allOptions = Array.from(doc.querySelectorAll('[role="option"], [data-baseweb="menu"] li, div[data-baseweb="popover"] li, ul[role="listbox"] li'))
                                                        .filter(el => (el.textContent || '').trim().length > 0);
                                if (allOptions.length > 0) {{
                                    e.preventDefault();
                                    e.stopPropagation();
                                    const highlighted = allOptions.find(o => o.getAttribute('aria-selected') === 'true' || o.dataset.highlighted === 'true');
                                    const targetOpt = highlighted || allOptions[0];
                                    triggerOptionClick(targetOpt);
                                    return;
                                }} else {{
                                    // Menú cerrado o artículo establecido: pasar a Entregados
                                    const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                                    const entregadosWidget = numInputs.find(w => (w.innerText || w.textContent || '').includes('Entregados')) || numInputs[0];
                                    if (entregadosWidget) {{
                                        const input = entregadosWidget.querySelector('input');
                                        if (input) {{
                                            e.preventDefault();
                                            e.stopPropagation();
                                            input.focus();
                                            doSelect(input);
                                            return;
                                        }}
                                    }}
                                    return;
                                }}
                            }}
                        }}

                        // Para los demás campos, Enter salta al siguiente o al botón de acción
                        if (e.key === 'Enter' || e.keyCode === 13) {{
                            if (activeEl.tagName === 'BUTTON') return;

                            // Si el usuario está en Precio Real u Observaciones, también pasar al botón de acción
                            const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                            const precWidget = numInputs.find(w => (w.innerText || w.textContent || '').includes('Precio Real'));
                            const textInputs = Array.from(doc.querySelectorAll('div[data-testid="stTextInput"]'));
                            const obsWidget = textInputs.find(w => (w.innerText || w.textContent || '').includes('Observaciones del Item'));

                            if ((precWidget && (precWidget === activeEl || precWidget.contains(activeEl))) ||
                                (obsWidget && (obsWidget === activeEl || obsWidget.contains(activeEl)))) {{
                                const actionBtn = getActionButton();
                                if (actionBtn) {{
                                    e.preventDefault();
                                    e.stopPropagation();
                                    actionBtn.focus();
                                    return;
                                }}
                            }}

                            const sequence = getFormSequence();
                            const currIdx = sequence.findIndex(item => item.input === activeEl || item.container.contains(activeEl));
                            if (currIdx > -1 && currIdx < sequence.length - 1) {{
                                e.preventDefault();
                                e.stopPropagation();
                                const nextItem = sequence[currIdx + 1];
                                nextItem.input.focus();
                                if (!nextItem.isButton) {{
                                    doSelect(nextItem.input);
                                }}
                            }}
                        }}
                    }}
                }};
                doc.addEventListener('keydown', pWin._keyHandlerEntregas, true);
            }} catch(e) {{}}
        }})();

        // Control continuo de foco post-render (SOLO cuando Python valida y confirma el cambio)
        const targetType = '{target_to_focus}';
        if (targetType === 'entregados') {{
            let attempts = 0;
            const maxAttempts = 30;
            const interval = setInterval(function() {{
                attempts++;
                try {{
                    const doc = window.parent.document;
                    const numInputs = Array.from(doc.querySelectorAll('div[data-testid="stNumberInput"]'));
                    const entregadosWidget = numInputs.find(w => (w.innerText || w.textContent || '').includes('Entregados')) || numInputs[0];
                    if (entregadosWidget) {{
                        const input = entregadosWidget.querySelector('input');
                        if (input) {{
                            if (doc.activeElement !== input) {{
                                if (doc.activeElement && typeof doc.activeElement.blur === 'function') {{
                                    try {{ doc.activeElement.blur(); }} catch(e) {{}}
                                }}
                                try {{ input.focus({{ preventScroll: true }}); }} catch(e_f) {{ input.focus(); }}
                                try {{
                                    input.select();
                                    input.setSelectionRange(0, input.value.length);
                                }} catch(e) {{}}
                            }} else {{
                                try {{
                                    input.select();
                                    input.setSelectionRange(0, input.value.length);
                                }} catch(e) {{}}
                                if (attempts > 5) clearInterval(interval);
                            }}
                        }}
                    }}
                }} catch(e) {{
                    if (attempts >= maxAttempts) clearInterval(interval);
                }}
                if (attempts >= maxAttempts) clearInterval(interval);
            }}, 25);
        }} else if (targetType === 'articulo') {{
            let attempts = 0;
            const maxAttempts = 30;
            const interval = setInterval(function() {{
                attempts++;
                try {{
                    const doc = window.parent.document;
                    const selectboxes = doc.querySelectorAll('div[data-testid="stSelectbox"]');
                    if (selectboxes.length > 0) {{
                        const targetBox = selectboxes[selectboxes.length - 1];
                        const input = targetBox.querySelector('input') || targetBox.querySelector('div[role="combobox"]');
                        if (input) {{
                            if (doc.activeElement !== input) {{
                                if (doc.activeElement && typeof doc.activeElement.blur === 'function') {{
                                    try {{ doc.activeElement.blur(); }} catch(e) {{}}
                                }}
                                try {{ input.focus({{ preventScroll: true }}); }} catch(e_f) {{ input.focus(); }}
                                try {{ input.select(); }} catch(e) {{}}
                            }} else {{
                                if (attempts > 5) clearInterval(interval);
                            }}
                        }}
                    }}
                }} catch(e) {{
                    if (attempts >= maxAttempts) clearInterval(interval);
                }}
                if (attempts >= maxAttempts) clearInterval(interval);
            }}, 25);
        }}

        // Salto a 'Carga de Items' cuando se marca un artículo en la primera columna
        function scrollToCargaEnt() {{
            try {{
                const doc = window.parent.document;
                const pWin = window.parent;
                if (!doc) return;

                // 1. Buscar prioritariamente el encabezado visible "Carga de Items"
                const headings = Array.from(doc.querySelectorAll('h1, h2, h3, [data-testid="stHeadingWithActionElements"]'));
                let targetEl = headings.find(h => (h.innerText || h.textContent || '').trim().includes('Carga de Items'));
                if (!targetEl) {{
                    targetEl = doc.getElementById('seccion_carga_items_ent');
                }}
                if (!targetEl) {{
                    const selectboxes = doc.querySelectorAll('div[data-testid="stSelectbox"]');
                    if (selectboxes.length > 0) targetEl = selectboxes[selectboxes.length - 1];
                }}

                if (targetEl) {{
                    // Usar scrollIntoView nativo
                    try {{
                        targetEl.scrollIntoView({{ behavior: 'smooth', block: 'start', inline: 'nearest' }});
                    }} catch(e) {{}}

                    // Scrollear todos los contenedores de Streamlit que posean scroll activo
                    const containers = [
                        doc.querySelector('div[data-testid="stAppViewContainer"]'),
                        doc.querySelector('section[data-testid="stMain"]'),
                        doc.querySelector('section.main'),
                        doc.querySelector('.main'),
                        doc.documentElement,
                        doc.body
                    ].filter(Boolean);

                    containers.forEach(function(container) {{
                        try {{
                            if (container.scrollHeight > container.clientHeight) {{
                                const cRect = (container === doc.documentElement || container === doc.body)
                                    ? {{ top: 0 }}
                                    : container.getBoundingClientRect();
                                const elRect = targetEl.getBoundingClientRect();
                                const targetScroll = container.scrollTop + (elRect.top - cRect.top) - 15;
                                try {{
                                    container.scrollTo({{ top: Math.max(0, targetScroll), behavior: 'smooth' }});
                                }} catch(err) {{
                                    container.scrollTop = Math.max(0, targetScroll);
                                }}
                            }}
                        }} catch(err2) {{}}
                    }});

                    // Scroll global en la ventana
                    try {{
                        const elRectGlobal = targetEl.getBoundingClientRect();
                        const pageY = pWin.pageYOffset || doc.documentElement.scrollTop || doc.body.scrollTop || 0;
                        const globalScrollTop = pageY + elRectGlobal.top - 15;
                        if (globalScrollTop > 0) {{
                            pWin.scrollTo({{ top: Math.max(0, globalScrollTop), behavior: 'smooth' }});
                            doc.documentElement.scrollTop = Math.max(0, globalScrollTop);
                            doc.body.scrollTop = Math.max(0, globalScrollTop);
                        }}
                    }} catch(err3) {{}}
                }}
            }} catch(e) {{}}
        }}

        const shouldScrollToCarga = {'true' if scroll_to_carga else 'false'};
        if (shouldScrollToCarga) {{
            scrollToCargaEnt();
            setTimeout(scrollToCargaEnt, 30);
            setTimeout(scrollToCargaEnt, 80);
            setTimeout(scrollToCargaEnt, 160);
            setTimeout(scrollToCargaEnt, 320);
            setTimeout(scrollToCargaEnt, 600);
        }}
    </script>
    """)

if __name__ == "__main__":
    remitos_entregas()