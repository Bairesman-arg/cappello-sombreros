# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from datetime import timedelta
import config

st.session_state.rubro_default = "GORRAS"

from models import (
    init_db,
    get_all_articulos,
    save_new_articulo,
    update_existing_articulo,
    delete_existing_articulo,
    check_article_in_remitos,
    get_all_rubros
)

def clear_inputs():
    """Reinicia los valores de los inputs del formulario."""
    try:
        st.session_state.descripcion_final = ""
        st.session_state.costo_final = 0.0
        st.session_state.precio_publico_final = 0.0
        st.session_state.precio_real_final = 0.0
        st.session_state.selected_articulo_id = None
        st.session_state.nro_articulo_exists = False
        st.session_state.nro_articulo_final = ""
        # Aseguramos que el rubro por defecto sea 'GORRAS'
        st.session_state.rubro_final = st.session_state.rubro_default
    except Exception as e:
        pass

def set_status_message(message, message_type):
    """Establece el mensaje de estado en la sesión."""
    st.session_state.status_message = message
    st.session_state.status_type = message_type
    
def clear_status_message():
    """Limpia el mensaje de estado de la sesión."""
    st.session_state.status_message = None
    st.session_state.status_type = None

# --- Callbacks de botones ---

def on_add_click():
    if st.session_state.precio_publico_final == 0:
        set_status_message("❌ No se puede agregar un artículo dejando el 'Precio al Público' en cero.", "error")
    elif st.session_state.precio_real_final == 0:
        set_status_message("❌ No se puede agregar un artículo dejando el 'Precio Real' en cero.", "error")
    elif not st.session_state.descripcion_final.strip():
        set_status_message("❌ La descripción no puede estar en blanco.", "error")
    else:
        try:
            nro_to_save = st.session_state.nro_articulo_final.upper()
            descripcion_to_save = st.session_state.descripcion_final.strip().capitalize()
            rubro_id = st.session_state.rubros_df[st.session_state.rubros_df['nombre_rubro'] == st.session_state.rubro_final]['id'].iloc[0] # <-- Obtener el ID del rubro
            
            save_new_articulo(
                nro_to_save,
                descripcion_to_save, 
                st.session_state.costo_final, 
                st.session_state.precio_publico_final, 
                st.session_state.precio_real_final,
                int(rubro_id) # <-- Pasar el ID del rubro
            )
            set_status_message(f"➕ Artículo '{nro_to_save}' agregado con éxito.", "success")
            clear_inputs()
        except Exception as e:
            set_status_message(f"❌ Error al agregar el artículo: {e}", "error")

    st.session_state.was_aggregated = True

def on_mod_click():
    if st.session_state.precio_publico_final == 0:
        set_status_message("❌ No se puede modificar un artículo dejando el 'Precio al Público' en cero.", "error")
    elif st.session_state.precio_real_final == 0:
        set_status_message("❌ No se puede modificar un artículo dejando el 'Precio Real' en cero.", "error")
    elif st.session_state.selected_articulo_id:
        try:
            rubro_id = st.session_state.rubros_df[st.session_state.rubros_df['nombre_rubro'] == st.session_state.rubro_final]['id'].iloc[0] # <-- Obtener el ID del rubro

            update_existing_articulo(
                st.session_state.selected_articulo_id, 
                st.session_state.nro_articulo_final,
                st.session_state.descripcion_final, 
                st.session_state.costo_final, 
                st.session_state.precio_publico_final, 
                st.session_state.precio_real_final,
                int(rubro_id) # <-- Pasar el ID del rubro
            )
            set_status_message(f"✍️ Artículo '{st.session_state.nro_articulo_final}' modificado con éxito.", "success")
            clear_inputs()
        except Exception as e:
            set_status_message(f"❌ Error al modificar el artículo: {e}", "error")

    st.session_state.was_modificated = True

def on_del_click():
    if st.session_state.selected_articulo_id:
        if not check_article_in_remitos(st.session_state.selected_articulo_id):
            st.session_state.show_delete_modal = True
        else:
            set_status_message("❌ No se puede eliminar el artículo, ya está asociado a un remito.", "error")


def clientes_crud():
    
    st.title(config.TITULO_APP)
    st.header("Gestión de Clientes")

    st.info(f"La funcionalidad del ABM de Clientes está en desarrollo.")
    st.stop()

    if not "articulos_df" in st.session_state: 
        st.session_state.articulos_df = get_all_articulos()
    if not "rubros_df" in st.session_state:
        st.session_state.rubros_df = get_all_rubros()
    if not "articulos_dict" in st.session_state:
        st.session_state.articulos_dict = {
            row['nro_articulo'].upper(): row 
            for _, row in st.session_state.articulos_df.iterrows()
        }

    # Inicializar los estados para los mensajes y el rubro
    if not 'status_message' in st.session_state:
        st.session_state.status_message = None
        st.session_state.status_type = None
    if not 'show_delete_modal' in st.session_state:
        st.session_state.show_delete_modal = False
    if not 'rubro_final' in st.session_state:
        st.session_state.rubro_final = st.session_state.rubro_default

    # Banderas para modificaciones y altas
    if not "was_modificated" in st.session_state: 
        st.session_state.was_modificated = False
    if not "was_aggregated" in st.session_state:
        st.session_state.was_aggregated = False
    if not "was_eliminated" in st.session_state:
        st.session_state.was_eliminated = False

    if st.session_state.was_modificated or \
        st.session_state.was_aggregated or \
        st.session_state.was_eliminated:

        st.session_state.articulos_df = get_all_articulos()
        st.session_state.articulos_dict = {
            row['nro_articulo'].upper(): row 
            for _, row in st.session_state.articulos_df.iterrows()
        }
        st.session_state.was_modificated = False
        st.session_state.was_aggregated = False
        st.session_state.was_eliminated = False
        st.session_state.rubro_final = st.session_state.rubro_default

    else:
        pass

    rubro_options = st.session_state.rubros_df['nombre_rubro'].tolist()
    
    if 'selected_articulo_id' not in st.session_state:
        clear_inputs()
    
    def update_form_with_article_data():
        current_nro = st.session_state.nro_articulo_final.upper()
        if current_nro in st.session_state.articulos_dict:
            found_articulo = st.session_state.articulos_dict[current_nro]
            st.session_state.nro_articulo_exists = True
            st.session_state.selected_articulo_id = found_articulo['id']
            st.session_state.descripcion_final = found_articulo['descripcion']
            st.session_state.costo_final = float(found_articulo['costo']) if found_articulo['costo'] else None 
            st.session_state.precio_publico_final = float(found_articulo['precio_publico']) if found_articulo['precio_publico'] else None
            st.session_state.precio_real_final = float(found_articulo['precio_real'])
            
            if found_articulo['nombre_rubro']:
                st.session_state.rubro_final = found_articulo['nombre_rubro']
            else:
                pass # st.session_state.rubro_final = st.session_state.rubro_default
        else:
            st.session_state.nro_articulo_exists = False
            st.session_state.selected_articulo_id = None
            st.session_state.descripcion_final = ""
            st.session_state.costo_final = 0.0
            st.session_state.precio_publico_final = 0.0
            st.session_state.precio_real_final = 0.0
            st.session_state.rubro_final = st.session_state.rubro_default # rubro_options[0] if rubro_options else ""

    nro_articulo_col, desc_col = st.columns([1, 2])
    
    with nro_articulo_col:
        st.text_input(
            "Número de Artículo",
            key="nro_articulo_final",
            help="Ingrese un código de artículo existente para editar o uno nuevo para agregar.",
            on_change=update_form_with_article_data
        )

    def update_precio_publico():
        new_costo = st.session_state.costo_final
        st.session_state.precio_publico_final = new_costo * 3
        
    with desc_col:
        st.text_input(
            "Descripción",
            key="descripcion_final",
            on_change=lambda: setattr(st.session_state, 'descripcion_final', st.session_state.descripcion_final.strip().capitalize())
        )
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.number_input(
            "Costo",
            key="costo_final",
            step=500,
            on_change=update_precio_publico
        )
    with col2:
        st.number_input(
            "Precio al Público",
            key="precio_publico_final",
            step=500
        )
    with col3:
        st.number_input(
            "Precio Real",
            key="precio_real_final",
            step=500
        )

    with col4:

        try:
            default_index = rubro_options.index(st.session_state.rubro_final)
        except ValueError:
            default_index = 0 # O un valor por defecto seguro si "GORRAS" no se encuentra.

        st.selectbox(
            "Rubro",
            options=rubro_options,
            key="rubro_final",
            # index=default_index,
            placeholder="Seleccione un rubro...",
            disabled=False
        )

    with st.form("articulo_form", clear_on_submit=False, border=True):
        is_add_disabled = st.session_state.nro_articulo_exists or not st.session_state.nro_articulo_final
        is_mod_del_disabled = not st.session_state.nro_articulo_exists or not st.session_state.nro_articulo_final

        col_add, col_mod, col_del, col_clear = st.columns(4)
        with col_add:
            st.form_submit_button(
                "Agregar Artículo ➕",
                disabled=is_add_disabled,
                on_click=on_add_click, width="stretch"
            )
        with col_mod:
            st.form_submit_button(
                "Modificar Artículo ✍️",
                disabled=is_mod_del_disabled,
                on_click=on_mod_click, width="stretch"
            )
        with col_del:
            st.form_submit_button(
                "Eliminar Artículo 🗑️",
                disabled=is_mod_del_disabled,
                on_click=on_del_click, width="stretch"
            )
        with col_clear:
            if st.form_submit_button("Limpiar Formulario 🔄", width="stretch"):
                del st.session_state.selected_articulo_id
                st.rerun()

    # --- Mostrar los mensajes de estado ---
    if st.session_state.status_message:
        if st.session_state.status_type == "success":
            st.success(st.session_state.status_message)
        elif st.session_state.status_type == "error":
            st.error(st.session_state.status_message)
        elif st.session_state.status_type == "warning":
            st.warning(st.session_state.status_message)
        
        clear_status_message()

    if 'show_delete_modal' in st.session_state and st.session_state.show_delete_modal:
        st.warning("⚠️ ¿Está seguro que desea eliminar este artículo? Esta acción no se puede deshacer.")
        col_confirm_del, col_cancel_del = st.columns(2)
        with col_confirm_del:
            if st.button("Confirmar Eliminación", type="primary"):
                try:
                    delete_existing_articulo(st.session_state.selected_articulo_id)
                    set_status_message(f"🗑️ Artículo '{st.session_state.nro_articulo_final}' eliminado con éxito.", "success")
                    del st.session_state.selected_articulo_id 
                    st.session_state.show_delete_modal = False
                    st.session_state.was_eliminated = True
                    st.rerun()
                except Exception as e:
                    set_status_message(f"❌ Error al eliminar el artículo: {e}", "error")
                    st.rerun()

        with col_cancel_del:
            if st.button("Cancelar"):
                st.session_state.show_delete_modal = False
                st.rerun()
    
    st.header(f"Maestro de Artículos ({len(st.session_state.articulos_df)})")
    if not st.session_state.articulos_df.empty:
        # Usar column_config para el formateo de la tabla
        st.dataframe(
            st.session_state.articulos_df,
            width="stretch",
            height=700,
            hide_index=True,
            column_order=[
                'nro_articulo', 'descripcion', 'nombre_rubro', 'costo', 'precio_publico', 'precio_real', 'fecha_mod'
            ],
            column_config={
                "nro_articulo": st.column_config.TextColumn("Artículo"),
                "descripcion": st.column_config.TextColumn("Descripción"),
                "nombre_rubro": st.column_config.TextColumn("Rubro"),
                "costo": st.column_config.NumberColumn(
                    "Costo",
                    format="$ %.2f"
                ),
                "precio_publico": st.column_config.NumberColumn(
                    "Precio al Público",
                    format="$ %.2f"
                ),
                "precio_real": st.column_config.NumberColumn(
                    "Precio Real",
                    format="$ %.2f"
                ),
                "fecha_mod": st.column_config.DatetimeColumn(
                    "Última Modificación" #,
                    # format="DD/MM/YYYY HH:MM:SS"
                )
            }
        )
    else:
        st.info("No hay artículos registrados.")

if __name__ == "__main__":
    clientes_crud()