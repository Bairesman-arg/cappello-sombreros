# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
import time
import config
from models import (
    get_all_rubros,
    save_new_rubro,
    update_existing_rubro,
    delete_existing_rubro,
    check_rubro_in_use,
    check_rubro_exists
)

def clear_inputs():
    """Reinicia los valores de los inputs del formulario de rubros y habilita la grilla."""
    st.session_state.selected_rubro_id = None
    st.session_state.nombre_rubro_val = ""
    st.session_state.view_grilla = True
    st.session_state.grid_version = st.session_state.get('grid_version', 0) + 1
    new_key = f"nombre_rubro_field_{st.session_state.grid_version}"
    st.session_state[new_key] = ""

def set_status_message(message, message_type):
    """Establece el mensaje de estado en la sesión."""
    st.session_state.rubros_status_message = message
    st.session_state.rubros_status_type = message_type

def clear_status_message():
    """Limpia el mensaje de estado."""
    st.session_state.rubros_status_message = None
    st.session_state.rubros_status_type = None

def on_nombre_change():
    """Convierte el nombre del rubro a mayúsculas automáticamente al perder el foco."""
    grid_v = st.session_state.get('grid_version', 0)
    key = f"nombre_rubro_field_{grid_v}"
    if key in st.session_state and st.session_state[key]:
        val_upper = st.session_state[key].strip().upper()
        st.session_state[key] = val_upper
        st.session_state.nombre_rubro_val = val_upper

def rubros_crud():
    st.set_page_config(layout="wide")
    st.title(config.TITULO_APP)

    # Inicialización de estado
    if "selected_rubro_id" not in st.session_state:
        st.session_state.selected_rubro_id = None
    if "nombre_rubro_val" not in st.session_state:
        st.session_state.nombre_rubro_val = ""
    if "view_grilla" not in st.session_state:
        st.session_state.view_grilla = True
    if "grid_version" not in st.session_state:
        st.session_state.grid_version = 0
    if "rubros_status_message" not in st.session_state:
        st.session_state.rubros_status_message = None
    if "rubros_status_type" not in st.session_state:
        st.session_state.rubros_status_type = None
    if "show_delete_modal_rubro" not in st.session_state:
        st.session_state.show_delete_modal_rubro = False

    input_key = f"nombre_rubro_field_{st.session_state.grid_version}"
    if input_key not in st.session_state:
        st.session_state[input_key] = st.session_state.nombre_rubro_val

    # --- Formulario ---
    st.header("ABM de Rubros")
    
    # Campo de texto a todo el ancho (alineado con la botonera)
    nombre_rubro_input = st.text_input(
        "Nombre del Rubro:",
        placeholder="Ingrese el nombre del rubro...",
        key=input_key,
        on_change=on_nombre_change
    )

    # --- Botones de acción ---
    col_b1, col_b2, col_b3, col_b4 = st.columns([1, 1, 1, 1], gap="small")

    modo_edicion = st.session_state.selected_rubro_id is not None

    with col_b1:
        add_clicked = st.button("Agregar Rubro ➕", use_container_width=True, disabled=modo_edicion)
    with col_b2:
        mod_clicked = st.button("Modificar Rubro ✍️", use_container_width=True, disabled=not modo_edicion)
    with col_b3:
        del_clicked = st.button("Eliminar Rubro 🗑️", use_container_width=True, disabled=not modo_edicion)
    with col_b4:
        clear_clicked = st.button("Limpiar Formulario 🧹", use_container_width=True)

    if clear_clicked:
        clear_inputs()
        clear_status_message()
        st.rerun()

    # --- Lógica de operaciones ---
    if add_clicked:
        clear_status_message()
        nombre_clean = nombre_rubro_input.strip().upper()
        if not nombre_clean:
            set_status_message("❌ Debe ingresar un nombre para el rubro.", "error")
        elif check_rubro_exists(nombre_clean):
            set_status_message(f"⚠️ El rubro '{nombre_clean}' ya existe. No se puede dar de alta.", "warning")
        else:
            try:
                save_new_rubro(nombre_clean)
                clear_inputs()
                set_status_message(f"➕ Rubro '{nombre_clean}' agregado con éxito.", "success")
                config.init_clientes_articulos()
                st.rerun()
            except Exception as e:
                set_status_message(f"❌ Error al agregar el rubro: {e}", "error")

    if mod_clicked and modo_edicion:
        clear_status_message()
        nombre_clean = nombre_rubro_input.strip().upper()
        if not nombre_clean:
            set_status_message("❌ Debe ingresar un nombre para el rubro.", "error")
        elif check_rubro_exists(nombre_clean, ignore_id=st.session_state.selected_rubro_id):
            set_status_message(f"⚠️ Ya existe otro rubro con el nombre '{nombre_clean}'.", "warning")
        else:
            try:
                rubro_id_mod = st.session_state.selected_rubro_id
                update_existing_rubro(rubro_id_mod, nombre_clean)
                clear_inputs()
                set_status_message(f"✍️ Rubro ID {rubro_id_mod} modificado a '{nombre_clean}' con éxito.", "success")
                config.init_clientes_articulos()
                st.rerun()
            except Exception as e:
                set_status_message(f"❌ Error al modificar el rubro: {e}", "error")

    if del_clicked and modo_edicion:
        clear_status_message()
        if check_rubro_in_use(st.session_state.selected_rubro_id):
            set_status_message("❌ No se puede eliminar el rubro porque tiene artículos asociados.", "error")
        else:
            st.session_state.show_delete_modal_rubro = True

    # Modal de confirmación de eliminación
    if st.session_state.show_delete_modal_rubro:
        clear_status_message()
        st.warning(f"¿Está seguro que desea eliminar el rubro ID {st.session_state.selected_rubro_id}?")
        col_c1, col_c2, _ = st.columns([1, 1, 2], gap="small")
        with col_c1:
            if st.button("Sí, eliminar ⚠️", use_container_width=True):
                try:
                    rubro_id_del = st.session_state.selected_rubro_id
                    delete_existing_rubro(rubro_id_del)
                    st.session_state.show_delete_modal_rubro = False
                    clear_inputs()
                    set_status_message(f"🗑️ Rubro ID {rubro_id_del} eliminado con éxito.", "warning")
                    config.init_clientes_articulos()
                    st.rerun()
                except Exception as e:
                    st.session_state.show_delete_modal_rubro = False
                    set_status_message(f"❌ Error al eliminar el rubro: {e}", "error")
                    st.rerun()
        with col_c2:
            if st.button("Cancelar ❌", use_container_width=True):
                st.session_state.show_delete_modal_rubro = False
                clear_status_message()
                st.rerun()

    # Mostrar mensajes de estado sólo si no hay modal activo
    if st.session_state.rubros_status_message and not st.session_state.show_delete_modal_rubro:
        msg_type = st.session_state.rubros_status_type
        if msg_type == "success":
            st.success(st.session_state.rubros_status_message)
        elif msg_type == "warning":
            st.warning(st.session_state.rubros_status_message)
        elif msg_type == "error":
            st.error(st.session_state.rubros_status_message)

    # --- Grilla de Rubros (Maestro) ---
    rubros_df = get_all_rubros()
    total_rubros = len(rubros_df)

    if st.session_state.view_grilla:
        st.header(f"Maestro de Rubros ({total_rubros} totales)")

        if not rubros_df.empty:
            df_to_show = rubros_df.copy()
            df_to_show['Seleccionado'] = False
            if 'fecha_mod' in df_to_show.columns:
                df_to_show['fecha_mod'] = pd.to_datetime(df_to_show['fecha_mod']).dt.strftime('%Y-%m-%d %H:%M:%S')

            edited_df = st.data_editor(
                df_to_show,
                key=f"rubros_grid_{st.session_state.grid_version}",
                use_container_width=True,
                height=390,
                hide_index=True,
                disabled=['id', 'nombre_rubro', 'fecha_mod'],
                column_order=['Seleccionado', 'id', 'nombre_rubro', 'fecha_mod'],
                column_config={
                    "Seleccionado": st.column_config.CheckboxColumn(
                        "✔",
                        help="Marque alguna de estas casillas de verificación para editar el rubro.",
                        width=50
                    ),
                    "id": st.column_config.NumberColumn("ID", format="%d", width=70),
                    "nombre_rubro": st.column_config.TextColumn("Nombre del Rubro", width=300),
                    "fecha_mod": st.column_config.TextColumn("Última Modificación", width=200)
                }
            )

            # Detectar selección de casilla
            selected_idxs = edited_df.index[edited_df["Seleccionado"] == True].tolist()
            if selected_idxs:
                idx = selected_idxs[0]
                selected_row = edited_df.loc[idx]
                st.session_state.selected_rubro_id = int(selected_row['id'])
                upper_name = str(selected_row['nombre_rubro']).upper()
                st.session_state.nombre_rubro_val = upper_name
                st.session_state.grid_version = st.session_state.get('grid_version', 0) + 1
                new_key = f"nombre_rubro_field_{st.session_state.grid_version}"
                st.session_state[new_key] = upper_name
                st.session_state.view_grilla = False
                clear_status_message()
                st.rerun()
        else:
            st.info("No hay rubros registrados actualmente.")
    else:
        st.write("✋ ATENCIÓN: La Grilla de Datos para visualización y búsquedas se habilitará cuando Modifique, Elimine o Limpie el formulario.")

    st.markdown(f"`{config.FOOTER_APP}`")

if __name__ == "__main__":
    rubros_crud()
