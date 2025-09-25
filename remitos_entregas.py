import streamlit as st
import pandas as pd
from datetime import timedelta
import time
import config
from models import (
    get_clients_and_articles,
    save_remito
)
from gen_remito import gen_remito

st.set_page_config(layout="wide")

def clear_item_inputs():
    """Reinicia los valores de los inputs de items sin cambiar la clave del selectbox."""
    st.session_state.entregados_input = 1
    st.session_state.observaciones_item_input = ""
    st.session_state.articulo_precargado = None
    st.session_state.precio_real_input = 0.0
    st.session_state.precio_original_articulo = 0.0  # ← AGREGAR
    # st.session_state.selectbox_key = str(time.time())
    # NO cambiar selectbox_key para evitar reset del selectbox

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
    st.session_state.cliente_selected_display = None
    # Limpiar artículo precargado pero mantener clave del selectbox
    st.session_state.articulo_precargado = None
    clear_item_inputs()

def calculate_consignacion(items_df):
    """Calcula el total de items entregados."""
    if 'Entregados' in items_df.columns:
        return int(items_df['Entregados'].sum())
    return 0

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
        "precio_original_articulo": 0.0
    }

    for key, default in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = default

    # Manejo de flags de rerun
    if st.session_state.should_clear_items:
        clear_item_inputs()
        st.session_state.should_clear_items = False
        st.rerun()

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

    # Selectbox de cliente - simple y directo
    cliente_selection = st.selectbox(
        "Cliente:",
        options=st.session_state.clientes_df['display_name'].tolist(),
        index=None,
        placeholder="Seleccione un cliente...",
        key=f"cliente_selection_input_{st.session_state.cabecera_key}",
        disabled=st.session_state.is_form_disabled
    )

    # Manejar selección del cliente de forma directa
    if cliente_selection:
        selected_razon_social = cliente_selection.split("  |  Boca:")[0].strip()
        matching_client = st.session_state.clientes_df.loc[st.session_state.clientes_df['razon_social'] == selected_razon_social]
        st.session_state.porc_dto = matching_client["porc_dto"].values[0]

        if not matching_client.empty:
            client_data = matching_client.iloc[0]
            st.session_state.cabecera_data['cliente_id'] = client_data['id']
            st.session_state.cliente_selected_display = cliente_selection
    elif st.session_state.get('cliente_selected_display') and not cliente_selection:
        st.session_state.cabecera_data['cliente_id'] = None
        st.session_state.cliente_selected_display = None

    # Campos de fecha y descuento
    col1, col2, col3 = st.columns(3, gap="small")

    with col1:
        fecha_entrega = st.date_input(
            "Fecha de Entrega",
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
        dto_display = f"{porc_dto}%" if porc_dto is not None else "Seleccione Cliente"
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
        options=[SENTINEL] + articulo_options_full,
        key="articulo_selectbox_fixed",  # ← CLAVE FIJA en lugar de st.session_state.selectbox_key
        disabled=st.session_state.is_form_disabled,
        help="Seleccione un nuevo artículo o uno existente en la grilla para modificar o eliminar."
    )

    # Manejar selección de artículo
    articulo_sel = SENTINEL
    if articulo_sel_full != SENTINEL and not st.session_state.is_form_disabled:
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

    # with st.sidebar:
    #    st.write(st.session_state.precio_real_input)

    # Botones de acción para items
    articulo_existe = (articulo_sel != SENTINEL and
                      articulo_sel in st.session_state.items_data['Articulo'].values)

    c1, c2, c3 = st.columns(3, gap="small")

    with c1:
        add_clicked = st.button(
            "Agregar Item",
            use_container_width=True,
            disabled=(articulo_sel == SENTINEL or articulo_existe or
                     st.session_state.is_form_disabled)
        )

    with c2:
        mod_clicked = st.button(
            "Modificar Item",
            use_container_width=True,
            disabled=(articulo_sel == SENTINEL or not articulo_existe or
                     st.session_state.is_form_disabled)
        )

    with c3:
        del_clicked = st.button(
            "Eliminar Item",
            use_container_width=True,
            disabled=(articulo_sel == SENTINEL or not articulo_existe or
                     st.session_state.is_form_disabled)
        )

    # Procesar acciones de items
    if add_clicked:
        if st.session_state.entregados_input < 1:
            st.error("La cantidad entregada debe ser 1 o mayor.")
        elif st.session_state.precio_real_input <= 0:
            st.error("El precio real debe ser mayor a cero. Vuelva a seleccionar el artículo.")
        else:
            articulo_info = st.session_state.articulos_df[st.session_state.articulos_df['nro_articulo'] == articulo_sel].iloc[0]
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
        if st.session_state.entregados_input < 1:
            st.error("La cantidad entregada debe ser 1 o mayor.")
        else:
            idx = st.session_state.items_data.index[
                st.session_state.items_data['Articulo'] == articulo_sel
            ][0]
            articulo_info = st.session_state.articulos_df[st.session_state.articulos_df['nro_articulo'] == articulo_sel].iloc[0]

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
                "Precio Real": st.column_config.NumberColumn(format="$%.2f", width="small"),
                "Entregados": st.column_config.Column(width="small"),
                "Observaciones": st.column_config.Column(width="small")
            }
        )
    else:
        st.info("Sin items cargados todavía.")

    # Mostrar total de consignación
    st.metric("Consignación (Total Entregados)",
              value=calculate_consignacion(st.session_state.items_data))

    # === BOTONES PRINCIPALES ===
    st.header("Acciones del Remito")

    is_remito_saved = st.session_state.remito_id is not None
    can_save = (st.session_state.cabecera_data['cliente_id'] is not None and
                not st.session_state.items_data.empty)

    col_buttons = st.columns(3, gap="small")

    # Botón Guardar
    say_error = False
    with col_buttons[0]:
        if st.button("Guardar Remito", type="primary", use_container_width=True,
                    disabled=st.session_state.is_form_disabled or is_remito_saved):
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

        if st.button("Nuevo Remito", use_container_width=True,
                    disabled=nuevo_remito_disabled):
            st.session_state.porc_dto = None
            if st.session_state.items_data.empty or is_remito_saved:
                st.session_state.should_reset_all = True
                st.rerun()
            else:
                st.session_state.show_confirm_modal = True
                st.rerun()

    # Botón Generar/Descargar Remito
    with col_buttons[2]:
        if is_remito_saved:
            excel_buffer = gen_remito(st.session_state.remito_id, is_retiro=False)
            st.download_button(
                label=f"Descargar Remito #{st.session_state.remito_id}",
                use_container_width=True,
                data=excel_buffer,
                file_name=f"Remito_{st.session_state.remito_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.button("Generar Remito", use_container_width=True, disabled=True)

    if say_error:
        st.error("Por favor, seleccione un cliente y agregue al menos un item.")

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
            if st.button("Sí, continuar",width="stretch"):
                st.session_state.show_confirm_modal = False
                st.session_state.should_reset_all = True
                st.rerun()

        with col_cancel:
            if st.button("Cancelar",width="stretch"):
                st.session_state.show_confirm_modal = False
                st.rerun()

    # Footer
    st.markdown(f"`{config.FOOTER_APP}`")

if __name__ == "__main__":
    remitos_entregas()