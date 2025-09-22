# -*- coding: utf-8 -*-
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

st.set_page_config(
    layout="wide"
)

clientes_df, articulos_df = get_clients_and_articles()
# Paso la columna boca a integros
clientes_df['boca'] = clientes_df['boca'].astype('Int64') 
SENTINEL = "— Seleccione un artículo —"

def clear_item_inputs():
    """Reinicia los valores de los inputs de items y fuerza el reinicio del selectbox."""
    st.session_state.entregados_input = 1
    st.session_state.observaciones_item_input = ""
    st.session_state.selectbox_key = str(time.time())
    st.session_state.articulo_precargado = None

def new_remito():
    st.session_state.remito_id = None
    st.session_state.items_data = pd.DataFrame(columns=[
        'Articulo', 'Descripción', 'Precio al Público',
        'Entregados', 'Observaciones', 'id_articulo'
    ])
    st.session_state.cabecera_data = {
        'cliente_id': None, 'fecha_entrega': None, 
        'fecha_retiro': None, 'observaciones': ''
    }
    st.session_state.cabecera_key = str(time.time())
    # Restablece el estado de los botones
    st.session_state.is_saved = False 
    clear_item_inputs()

def calculate_consignacion(items_df):
    if 'Entregados' in items_df.columns:
        return int(items_df['Entregados'].sum())
    return 0

def remitos():
    st.title(config.TITULO_APP)
    st.header("Carga de Remitos - Entregas")

    for key, default in {
        "remito_id": None,
        "items_data": pd.DataFrame(columns=[
            "Articulo", "Descripción", "Precio al Público",
            "Entregados", "Observaciones", "id_articulo"
        ]),
        "cabecera_data": {"cliente_id": None, "fecha_entrega": None, "fecha_retiro": None, "observaciones": ""},
        "entregados_input": 1,
        "observaciones_item_input": "",
        "selectbox_key": "initial_key",
        "cabecera_key": "initial_cabecera",
        "should_clear_items": False,
        "should_reset_all": False,
        "show_confirm_modal": False,
        "is_form_disabled": False,
        "is_saved": False
    }.items():
        if key not in st.session_state:
            st.session_state[key] = default

    if st.session_state.should_clear_items:
        clear_item_inputs()
        st.session_state.should_clear_items = False
        st.rerun()

    if st.session_state.should_reset_all:
        new_remito()
        st.session_state.should_reset_all = False
        st.rerun()

    # Lógica para deshabilitar el formulario completo
    st.session_state.is_form_disabled = st.session_state.show_confirm_modal

    cabecera_key = st.session_state.cabecera_key

    #cliente_selection = st.selectbox(
    #    "Cliente:",
    #    options=clientes_df['razon_social'].tolist(),
    #    index=None,
    #    placeholder="Seleccione un cliente...",
    #    key=f"cliente_selection_input_{cabecera_key}",
    #    disabled=st.session_state.is_form_disabled
    #)

    # Create a new column with the concatenated string for the selectbox options.
    clientes_df['display_name'] = clientes_df.apply(
        lambda row: f"{row['razon_social']}  |  Boca: {row['boca']}" if pd.notna(row['boca']) else row['razon_social'],
        axis=1
    )

    # Use the new 'display_name' column as the options for the selectbox.
    cliente_selection = st.selectbox(
        "Cliente:",
        options=clientes_df['display_name'].tolist(),
        index=None,
        placeholder="Seleccione un cliente...",
        key=f"cliente_selection_input_{cabecera_key}",
        disabled=st.session_state.is_form_disabled
    )

    if cliente_selection:
        # Use the original 'razon_social' to find the corresponding client ID.
        selected_razon_social = cliente_selection.split("  |  Boca:")[0].strip()
        st.session_state.cabecera_data['cliente_id'] = clientes_df.loc[
            clientes_df['razon_social'] == selected_razon_social, 'id'
        ].iloc[0]
    else:
        st.session_state.cabecera_data['cliente_id'] = None


    #if cliente_selection:
    #    st.session_state.cabecera_data['cliente_id'] = clientes_df.loc[
    #        clientes_df['razon_social'] == cliente_selection, 'id'
    #        ].iloc[0]
    #else:
    #    st.session_state.cabecera_data['cliente_id'] = None

    if cliente_selection:
        # Split the selected string to get the 'razon_social'
        # This handles both cases: "Razon Social" and "Razon Social  |  Boca: XYZ"
        selected_razon_social = cliente_selection.split("  |  Boca:")[0]

        # Find the row in the DataFrame that matches the 'razon_social'
        # Use .loc to get the ID
        matching_client = clientes_df.loc[clientes_df['razon_social'] == selected_razon_social]
        if not matching_client.empty:
            st.session_state.cabecera_data['cliente_id'] = matching_client['id'].iloc[0]
        else:
            st.session_state.cabecera_data['cliente_id'] = None
    else:
        st.session_state.cabecera_data['cliente_id'] = None

    col1, col2 = st.columns(2,gap="small")
    with col1:
        fecha_entrega = st.date_input("Fecha de Entrega", format="DD/MM/YYYY", key=f"fecha_entrega_{cabecera_key}", disabled=st.session_state.is_form_disabled)
        st.session_state.cabecera_data['fecha_entrega'] = fecha_entrega
    with col2:
        fecha_retiro = st.text_input("Fecha de Retiro", disabled=True, key=f"fecha_retiro_{cabecera_key}")
        st.session_state.cabecera_data['fecha_retiro'] = None

    observaciones_cabecera = st.text_area(
        "Observaciones del Remito ( notas privadas )",
        value="",
        key=f"observaciones_cabecera_input_{cabecera_key}",
        disabled=st.session_state.is_form_disabled
    )
    st.session_state.cabecera_data['observaciones'] = observaciones_cabecera

    st.header("Carga de Items")

    articulo_options_full = articulos_df.apply(
        lambda row: f"{row['nro_articulo']} - {row['descripcion']}", axis=1
    ).tolist()

    articulo_sel_full = st.selectbox(
        "Artículo:",
        options=[SENTINEL] + articulo_options_full,
        key=st.session_state.selectbox_key,
        disabled=st.session_state.is_form_disabled
    )

    if articulo_sel_full != SENTINEL and not st.session_state.is_form_disabled:
        articulo_sel = articulo_sel_full.split(" - ")[0]
        if 'articulo_precargado' not in st.session_state or st.session_state.articulo_precargado != articulo_sel:
            st.session_state.articulo_precargado = articulo_sel
            if articulo_sel in st.session_state.items_data['Articulo'].values:
                row = st.session_state.items_data.loc[st.session_state.items_data['Articulo'] == articulo_sel].iloc[0]
                st.session_state.entregados_input = int(row['Entregados'])
                st.session_state.observaciones_item_input = row['Observaciones']
            else:
                st.session_state.entregados_input = 1
                st.session_state.observaciones_item_input = ""
            st.rerun()
    else:
        articulo_sel = SENTINEL

    col_entregados, col_observ = st.columns([1,3],gap="small")
    with col_entregados:
        st.number_input(
            "Entregados:",
            min_value=1,
            step=1,
            key="entregados_input",
            disabled=st.session_state.is_form_disabled
        )
    with col_observ:
        st.text_input(
            "Observaciones del Item:",
            # value=st.session_state.observaciones_item_input,
            key="observaciones_item_input",
            disabled=st.session_state.is_form_disabled
        )

    articulo_existe = (articulo_sel != SENTINEL) and (articulo_sel in st.session_state.items_data['Articulo'].values)

    c1, c2, c3 = st.columns(3,gap="small")
    with c1:
        add_clicked = st.button("Agregar Item", width="stretch", disabled=(articulo_sel == SENTINEL) or articulo_existe or st.session_state.is_form_disabled)
    with c2:
        mod_clicked = st.button("Modificar Item", width="stretch", disabled=(articulo_sel == SENTINEL) or (not articulo_existe) or st.session_state.is_form_disabled)
    with c3:
        del_clicked = st.button("Eliminar Item", width="stretch", disabled=(articulo_sel == SENTINEL) or (not articulo_existe) or st.session_state.is_form_disabled)

    if add_clicked:
        if st.session_state.entregados_input < 1:
            st.error("La cantidad entregada debe ser 1 o mayor.")
        else:
            articulo_info = articulos_df[articulos_df['nro_articulo'] == articulo_sel].iloc[0]
            new_item = {
                'Articulo': articulo_sel,
                'Descripción': articulo_info['descripcion'],
                'Precio al Público': articulo_info['precio_publico'],
                'Entregados': st.session_state.entregados_input,
                'Observaciones': st.session_state.observaciones_item_input,
                'id_articulo': articulo_info['id']
            }
            # st.session_state.items_data = pd.concat([st.session_state.items_data, pd.DataFrame([new_item])], ignore_index=True)
            if not st.session_state.items_data.empty:
                st.session_state.items_data = pd.concat([st.session_state.items_data, pd.DataFrame([new_item])], ignore_index=True)
            else:
                # Si el DataFrame está vacío, simplemente asigna el nuevo ítem
                st.session_state.items_data = pd.DataFrame([new_item])
            
            st.session_state.should_clear_items = True
            st.rerun()

    if mod_clicked and articulo_existe:
        if st.session_state.entregados_input < 1:
            st.error("La cantidad entregada debe ser 1 o mayor.")
        else:
            idx = st.session_state.items_data.index[st.session_state.items_data['Articulo'] == articulo_sel][0]
            articulo_info = articulos_df[articulos_df['nro_articulo'] == articulo_sel].iloc[0]
            st.session_state.items_data.loc[idx, :] = {
                'Articulo': articulo_sel,
                'Descripción': articulo_info['descripcion'],
                'Precio al Público': articulo_info['precio_publico'],
                'Entregados': st.session_state.entregados_input,
                'Observaciones': st.session_state.observaciones_item_input,
                'id_articulo': articulo_info['id']
            }
            st.success("Artículo modificado")
            st.session_state.should_clear_items = True
            st.rerun()

    if del_clicked and articulo_existe:
        st.session_state.items_data = st.session_state.items_data[st.session_state.items_data['Articulo'] != articulo_sel].reset_index(drop=True)
        st.warning("Artículo eliminado")
        st.session_state.should_clear_items = True
        st.rerun()

    #def calcular_ancho_columna(df: pd.DataFrame, columna: str, min_width: int = 40, padding: int = 0) -> int:
    #    # Calcula un ancho aproximado en píxeles para una columna del DataFrame
    #    # basado en la longitud del valor más largo.
    #    if columna in df.columns:
    #        # Convertimos todo a string para contar caracteres
    #        max_chars = max(len(str(x)) for x in df[columna])
    #        max_chars = max(max_chars,len(columna))
    #        
    #        # Estimación: ~8 px por carácter + padding extra
    #       return max(min_width, max_chars * 8 + padding)
    #   else:
    #        return min_width

    st.header("Items actuales del Remito")
    if not st.session_state.items_data.empty:
        st.dataframe(st.session_state.items_data[['Articulo', 'Descripción', 'Entregados', 'Observaciones']],
                    hide_index=True,
                    column_config={
                        "Articulo": st.column_config.Column(width="medium"),
                        "Descripción": st.column_config.Column(width="large"),
                        "Entregados": st.column_config.Column(width="small"),
                        "Observaciones": st.column_config.Column(width="small")
                        }
                    )
    else:
        st.info("Sin items cargados todavía.")

    st.metric("Consignación (Total Entregados)", value=calculate_consignacion(st.session_state.items_data))

    not_client_or_items = False
    remito_guardado = False
    
    col_remito_buttons = st.columns(3,gap="small")

    # Determine the disabled state for the 'Guardar Remito' button
    is_remito_saved = st.session_state.remito_id is not None
    is_guardar_disabled = st.session_state.is_form_disabled

    col_remito_buttons = st.columns(3,gap="small")
    with col_remito_buttons[0]:
        if st.button("Guardar Remito", type="primary", width="stretch", disabled=is_guardar_disabled):
            if is_remito_saved:
                st.warning(f"El Remito #{st.session_state.remito_id} ya ha sido guardado.")
            elif st.session_state.cabecera_data['cliente_id'] is None or st.session_state.items_data.empty:
                st.error("Por favor, seleccione un cliente y agregue al menos un item.")
            else:
                time.sleep(1)
                remito_id = save_remito(
                    st.session_state.cabecera_data['cliente_id'],
                    st.session_state.cabecera_data['fecha_entrega'],
                    st.session_state.cabecera_data['fecha_retiro'],
                    st.session_state.cabecera_data['observaciones'],
                    st.session_state.items_data
                )
                remito_guardado = True
                st.session_state.remito_id = remito_id

    with col_remito_buttons[1]:
        if st.session_state.items_data.empty or is_remito_saved:
            if st.button("Nuevo Remito", width="stretch", disabled=st.session_state.is_form_disabled):
                st.session_state.should_reset_all = True
                st.rerun()
        else:
            if st.button("Nuevo Remito", width="stretch", disabled=st.session_state.is_form_disabled):
                st.session_state.show_confirm_modal = True
                st.rerun()

    with col_remito_buttons[2]:
        is_ready = "remito_id" in st.session_state and st.session_state.remito_id is not None
        imprimir_text = f"Generar Remito #{st.session_state.remito_id}" if is_ready else "Generar Remito"
        if is_ready:
            excel_buffer = gen_remito(st.session_state.remito_id)
            # st.success("Remito generado con éxito. Por favor, guarda el archivo en la carpeta 'Remitos' en tu Escritorio.")
            st.download_button(
                label=f"Descargar Remito #{st.session_state.remito_id}",
                width="stretch",
                data=excel_buffer,
                file_name=f"Remito_{st.session_state.remito_id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.button(imprimir_text, width="stretch", disabled=True)

    # Modal de confirmación para "Nuevo Remito"
    if st.session_state.show_confirm_modal:
        st.warning("Hay artículos cargados en la grilla. ¿Desea continuar y borrar todos los datos del remito?")
        col_confirm, col_cancel = st.columns([2, 4],gap="small")
        with col_confirm:
            if st.button("Sí, continuar con un nuevo Remito"):
                st.session_state.show_confirm_modal = False
                st.session_state.should_reset_all = True
                st.rerun()
        with col_cancel:
            if st.button("Cancelar"):
                st.session_state.show_confirm_modal = False
                st.rerun()

    if not_client_or_items:
        st.error("Por favor, seleccione un cliente y agregue al menos un item.")
    elif remito_guardado:
        st.success(f"Remito #{st.session_state.remito_id} guardado con éxito!")
        st.balloons()
        time.sleep(2)
        # st.session_state.should_reset_all = True
        # st.rerun()

    st.markdown(f"`{config.FOOTER_APP}`")

if __name__ == "__main__":
    remitos()