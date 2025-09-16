# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from datetime import timedelta
import config

from models import (
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
        st.session_state.rubro_final = config.RUBRO_DEFAULT
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

def valida_datos():
    valida = False
    if len(st.session_state.nro_articulo_final) > 11:
        set_status_message("❌ Muchos caracteres para el 'Número de artículo'. El máximo es 11.", "error")
    elif st.session_state.precio_real_final == 0:
        set_status_message("❌ No se puede agregar o modificar un artículo dejando el 'Precio Real al Público' en cero.", "error")
    # elif st.session_state.precio_publico_final == 0:
    #     set_status_message("❌ No se puede agregar o modificar un artículo dejando el 'Precio al Público' en cero.", "error")
    else:
        valida = True
    return valida

def on_add_click():
    if valida_datos() and st.session_state.selected_articulo_id:
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
    if valida_datos() and st.session_state.selected_articulo_id:
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
            st.session_state.do_filter = True # Obligo a refrescar la grilla
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


def articulos_crud():
    
    st.set_page_config(
        layout="wide"
    )
        
    st.title(config.TITULO_APP)
    st.header("Gestión de Artículos")

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
        st.session_state.rubro_final = config.RUBRO_DEFAULT
    
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
        if st.session_state.rubro_final == "": 
            st.session_state.rubro_final = config.RUBRO_DEFAULT

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
                pass
        else:
            st.session_state.nro_articulo_exists = False
            st.session_state.selected_articulo_id = None
            st.session_state.descripcion_final = ""
            st.session_state.costo_final = 0.0
            st.session_state.precio_publico_final = 0.0
            st.session_state.precio_real_final = 0.0
            st.session_state.rubro_final = config.RUBRO_DEFAULT # rubro_options[0] if rubro_options else ""

    nro_articulo_col, desc_col = st.columns([1, 2],gap="small")
        
    # Pop temporal para no repetir en el siguiente rerun
    article_data = st.session_state.pop("selected_article_data", {})
    if article_data:
        if article_data.get("descripcion") != "":
            st.session_state.descripcion_final = article_data.get("descripcion")
        if not article_data.get("costo") == None:
            st.session_state.costo_final = article_data.get("costo")
        if not article_data.get("precio_real") == None:
            st.session_state.precio_real_final = article_data.get("precio_real")
        if not article_data.get("precio_publico") == None:
            st.session_state.precio_publico_final = article_data.get("precio_publico")
        if article_data.get("nombre_rubro") != "":
            st.session_state.rubro_final = article_data.get("nombre_rubro")
        if article_data.get("nro_articulo") != "":
            st.session_state.nro_articulo_final = article_data.get("nro_articulo")

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
        )
    
    col1, col2, col3, col4 = st.columns(4,gap="small")
    with col1:
        st.number_input(
            "Costo",
            key="costo_final",
            step=500.00,
            min_value=0.00,
            on_change=update_precio_publico
        )
    with col2:
        st.number_input(
            "Real al Público",
            key="precio_real_final",
            step=500.00,
            min_value=0.00
        )

    with col3:
        st.number_input(
            "Precio al Público",
            key="precio_publico_final",
            step=500.00,
            min_value=0.00
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
            placeholder="Seleccione un rubro...",
            disabled=False
        )

    article_data = None
    
    with st.form("articulo_form", clear_on_submit=False, border=False):
        is_add_disabled = st.session_state.nro_articulo_exists or not st.session_state.nro_articulo_final
        is_mod_del_disabled = not st.session_state.nro_articulo_exists or not st.session_state.nro_articulo_final

        col_add, col_mod, col_del, col_clear = st.columns(4,gap="small")
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
        col_confirm_del, col_cancel_del = st.columns(2,gap="small")
        with col_confirm_del:
            if st.button("Confirmar Eliminación", type="primary"):
                try:
                    delete_existing_articulo(st.session_state.selected_articulo_id)
                    set_status_message(f"🗑️ Artículo '{st.session_state.nro_articulo_final}' eliminado con éxito.", "success")
                    del st.session_state.selected_articulo_id 
                    st.session_state.show_delete_modal = False
                    st.session_state.was_eliminated = True
                    st.session_state.do_filter = True # Obligo a refrescar la grilla
                    st.rerun()
                except Exception as e:
                    set_status_message(f"❌ Error al eliminar el artículo: {e}", "error")
                    st.rerun()

        with col_cancel_del:
            if st.button("Cancelar"):
                st.session_state.show_delete_modal = False
                st.rerun()
    
    # --- Seccion del filtro personalizado ---
    st.subheader("Filtrar Artículos")
    col_input, col_btn = st.columns([3.5, 1],gap="small")

    with col_input:
        filter_term = st.text_input(
            "Buscar por Artículo o Descripción",
            key="filter_term",
            placeholder="Ingrese un código, una descripción o parte de ellas...",
            label_visibility="collapsed",
            width="stretch"
        )
    with col_btn:
        if st.button("Filtrar", type="primary", width="stretch"):
            st.session_state.do_filter = True
            st.rerun()
    
    # Lógica de filtrado
    estado_grilla = "totales"
    if "do_filter" in st.session_state and st.session_state.do_filter:
        if filter_term.strip():
            search_term_lower = filter_term.lower().strip()
            st.session_state.filtered_df = st.session_state.articulos_df[
                st.session_state.articulos_df['nro_articulo'].str.lower().str.contains(search_term_lower, na=False) | 
                st.session_state.articulos_df['descripcion'].str.lower().str.contains(search_term_lower, na=False)
            ]
            estado_grilla = "filtrados"
        else:
            # Si el usuario presiona el boton con el campo vacio, se muestra la grilla completa
            st.session_state.filtered_df = st.session_state.articulos_df.copy()

    if "filtered_df" not in st.session_state:
        st.session_state.filtered_df = st.session_state.articulos_df.copy()

    st.header(f"Maestro de Artículos ({len(st.session_state.filtered_df)} {estado_grilla})")
    if not st.session_state.filtered_df.empty:

        # --- Parámetros de configuración ---
        max_filas_a_mostrar = 20
        alto_del_encabezado = 35
        alto_de_la_fila = 35

        # --- Lógica para ajustar la altura ---
        # Calculamos el número de filas reales a mostrar
        num_filas_a_mostrar = min(len(st.session_state.filtered_df), max_filas_a_mostrar)

        # Calculamos la altura final
        alto_df = alto_del_encabezado + alto_de_la_fila * num_filas_a_mostrar

        # Eliminamos valores None en nombre_rubro
        st.session_state.filtered_df.loc[:, 'nombre_rubro'] = st.session_state.filtered_df['nombre_rubro'].fillna('')

        # --- Preparar una copia y agregar la columna temporal 'Seleccionado' ---
        df_to_show = st.session_state.filtered_df.copy().reset_index(drop=True)

        # Insertamos la columna temporal "Seleccionado" solo si no existe
        if "Seleccionado" not in df_to_show.columns:
            df_to_show.insert(0, "Seleccionado", False)

        # Columnas que dejaremos NO editables (todas salvo la columna Seleccionado)
        disabled_cols = [c for c in df_to_show.columns if c != "Seleccionado"]

        # Se Cambia la key del data_editor cada vez por posibles selecciones de registro
        editor_key = f"articulos_grid_{st.session_state.get('grid_version', 0)}"

        def calcular_ancho_columna(df: pd.DataFrame, columna: str, min_width: int = 40, padding: int = 0) -> int:
            # Calcula un ancho aproximado en píxeles para una columna del DataFrame
            # basado en la longitud del valor más largo.
            if columna in df.columns:
                # Convertimos todo a string para contar caracteres
                max_chars = max(len(str(x)) for x in df[columna])
                max_chars = max(max_chars,len(columna))
                
                # Estimación: ~8 px por carácter + padding extra
                return max(min_width, max_chars * 8 + padding)
            else:
                return min_width

        # Usar column_config para el formateo de la tabla
        edited_df = st.data_editor(
            df_to_show, # <-- Filtrado o no
            key=editor_key,
            width="stretch",
            height=alto_df,
            hide_index=True,
            disabled=disabled_cols,
            column_order=[
                'Seleccionado', 'nro_articulo', 'descripcion', 'nombre_rubro', 'costo', 'precio_real', 'precio_publico', 'fecha_mod'
            ],
            column_config={
                "Seleccionado": st.column_config.CheckboxColumn("✔", 
                                help="Marque alguna de estas casillas de verificación para editar el artículo.",
                                width=calcular_ancho_columna(df_to_show,"Seleccionado")),
                "nro_articulo": st.column_config.TextColumn("Artículo",
                                width=calcular_ancho_columna(df_to_show,"nro_articulo")),
                "descripcion": st.column_config.TextColumn("Descripción", 
                                                           width=calcular_ancho_columna(df_to_show,"descripcion"),
                                                           disabled=True),
                "nombre_rubro": st.column_config.TextColumn("Rubro",
                                                            width=calcular_ancho_columna(df_to_show,"nombre_rubro")),
                "costo": st.column_config.NumberColumn(
                    "Costo",
                    width=calcular_ancho_columna(df_to_show,"costo"),
                    format="$ %.2f"
                ),
                "precio_real": st.column_config.NumberColumn(
                    "Real al Público",
                    width=calcular_ancho_columna(df_to_show,"precio_real"),
                    format="$ %.2f"
                ),
                "precio_publico": st.column_config.NumberColumn(
                    "Precio al Público",
                    width=calcular_ancho_columna(df_to_show,"precio_publico"),
                    format="$ %.2f"
                ),
                "fecha_mod": st.column_config.DatetimeColumn(
                    "Última Modificación",
                     width=calcular_ancho_columna(df_to_show,"fecha_mod") #,
                    # format="DD/MM/YYYY HH:MM:SS"
                )
            }
        )

        # --- Detectar selección(s) y cargar el artículo en el form ---
        # edited_df es el DataFrame resultante con el checkbox actualizado
        selected_idxs = edited_df.index[edited_df["Seleccionado"] == True].tolist()

        if selected_idxs:
            # Tomo la primera selección
            idx = selected_idxs[0]
            selected_row = edited_df.loc[idx]
            
            # Guardamos todos los datos de interés en un diccionario temporal
            st.session_state.selected_article_data = {
                "nro_articulo": selected_row["nro_articulo"],
                "descripcion": selected_row["descripcion"],
                "costo": float(selected_row["costo"]) if selected_row["costo"] > 0 else None,
                "precio_real": float(selected_row["precio_real"]) if selected_row["precio_real"] > 0 else None,
                "precio_publico": float(selected_row["precio_publico"]) if selected_row["precio_publico"] > 0 else None,
                "nombre_rubro": selected_row["nombre_rubro"]
            }

            st.session_state.nro_articulo_exists = True
            st.session_state.selected_articulo_id = int(selected_row["id"])
            st.session_state.grid_version = st.session_state.get('grid_version', 0) + 1

            st.rerun()

        else:
            st.session_state.selected_article_data = {
                "nro_articulo": "",
                "descripcion": "",
                "costo": None,
                "precio_real": None,
                "precio_publico": None,
                "nombre_rubro": ""
            }

    else:
        st.info("No hay artículos registrados.")

if __name__ == "__main__":
    articulos_crud()