# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
from datetime import timedelta
import config

from models import (
    get_all_clientes,
    save_new_cliente,
    update_existing_cliente,
    delete_existing_cliente,
    check_client_in_remitos,
    get_all_vendedores
)

def clear_inputs():
    """Reinicia los valores de los inputs del formulario."""
    try:
        st.session_state.razon_social_final = ""
        st.session_state.boca_final = 0
        st.session_state.direccion_final = ""
        st.session_state.localidad_final = ""
        st.session_state.telefono_final = ""
        st.session_state.email_final = ""
        st.session_state.porc_dto_final = 0.0
        st.session_state.selected_cliente_id = None
        st.session_state.boca_exists = False
        st.session_state.selected_vendedor = config.VENDEDOR_DEFAULT
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
    if not isinstance(st.session_state.boca_final, int):
        set_status_message("❌ El 'Número de Boca' debe ser un número entero.", "error")
    elif st.session_state.boca_final <= 0:
        set_status_message("❌ El 'Número de Boca' debe ser mayor a cero.", "error")
    elif not st.session_state.razon_social_final:
        set_status_message("❌ La 'Razón Social' no puede estar vacía.", "error")
    elif st.session_state.porc_dto_final <= 0:
        set_status_message("❌ El 'Porcentaje de Descuento' no puede ser negativo o cero.", "error")
    else:
        valida = True
    return valida

def on_add_click():
    if valida_datos():
        try:
            vendedor_id = st.session_state.vendedores_df[st.session_state.vendedores_df['nombre'] == st.session_state.selected_vendedor]['id'].iloc[0] if st.session_state.selected_vendedor else None

            save_new_cliente(
                st.session_state.razon_social_final,
                st.session_state.boca_final,
                st.session_state.direccion_final,
                st.session_state.localidad_final,
                st.session_state.telefono_final,
                st.session_state.email_final,
                st.session_state.porc_dto_final,
                int(vendedor_id)
            )
            set_status_message(f"➕ Cliente '{st.session_state.razon_social_final}' agregado con éxito.", "success")
            config.init_clientes_articulos()
            clear_inputs()
        except Exception as e:
            set_status_message(f"❌ Error al agregar el cliente: {e}", "error")
    # elif not st.session_state.selected_cliente_id:
    #     set_status_message("❌ No se puede agregar un cliente si ya existe uno con el mismo Número de Boca.", "error")
    # else:
    #    pass

    st.session_state.was_aggregated = True

def on_mod_click():
    if valida_datos() and st.session_state.selected_cliente_id:
        try:
            vendedor_id = st.session_state.vendedores_df[st.session_state.vendedores_df['nombre'] == st.session_state.selected_vendedor]['id'].iloc[0] if st.session_state.selected_vendedor else None

            update_existing_cliente(
                st.session_state.selected_cliente_id,
                st.session_state.razon_social_final,
                st.session_state.boca_final,
                st.session_state.direccion_final,
                st.session_state.localidad_final,
                st.session_state.telefono_final,
                st.session_state.email_final,
                st.session_state.porc_dto_final,
                int(vendedor_id)
            )
            set_status_message(f"✍️ Cliente '{st.session_state.razon_social_final}' modificado con éxito.", "success")
            st.session_state.do_filter = True # Obligo a refrescar la grilla
            config.init_clientes_articulos()
            clear_inputs()
            st.session_state.view_grilla = True
        except Exception as e:
            set_status_message(f"❌ Error al modificar el cliente: {e}", "error")

    st.session_state.was_modificated = True

def on_del_click():
    if st.session_state.selected_cliente_id:
        if not check_client_in_remitos(st.session_state.selected_cliente_id):
            st.session_state.show_delete_modal = True
        else:
            set_status_message("❌ No se puede eliminar el cliente, ya está asociado a un remito.", "error")


def clientes_crud():

    st.set_page_config(
        layout="wide"
    )

    st.title(config.TITULO_APP)

    if not "view_grilla" in st.session_state:
        st.session_state.view_grilla = True
    
    st.header("Gestión de Clientes")
    st.markdown(f"`Seleccione la primera columna de la grilla inferior para modificar o eliminar`")

    if not "clientes_df" in st.session_state:
        st.session_state.clientes_df = get_all_clientes()
    if not "vendedores_df" in st.session_state:
        st.session_state.vendedores_df = get_all_vendedores()
    if not "clientes_dict" in st.session_state:
        st.session_state.clientes_dict = {
            row['boca']: row
            for _, row in st.session_state.clientes_df.iterrows()
        }

    # Inicializar los estados para los mensajes y el vendedor
    if not 'status_message' in st.session_state:
        st.session_state.status_message = None
        st.session_state.status_type = None
    if not 'show_delete_modal' in st.session_state:
        st.session_state.show_delete_modal = False
    if not 'selected_vendedor' in st.session_state:
        st.session_state.selected_vendedor = config.VENDEDOR_DEFAULT

    # Banderas para modificaciones y altas
    if not "was_modificated" in st.session_state:
        st.session_state.was_modificated = False
    if not "was_aggregated" in st.session_state:
        st.session_state.was_aggregated = False
    if not "was_eliminated" in st.session_state:
        st.session_state.was_eliminated = False
    if not "frase_filtrada" in st.session_state:    
        st.session_state.frase_filtrada =""


    if st.session_state.was_modificated or \
        st.session_state.was_aggregated or \
        st.session_state.was_eliminated:

        st.session_state.clientes_df = get_all_clientes()
        st.session_state.clientes_dict = {
            row['boca']: row
            for _, row in st.session_state.clientes_df.iterrows()
        }
        st.session_state.was_modificated = False
        st.session_state.was_aggregated = False
        st.session_state.was_eliminated = False
        if st.session_state.selected_vendedor == "": 
            st.session_state.selected_vendedor = config.VENDEDOR_DEFAULT

    vendedor_options = st.session_state.vendedores_df['nombre'].tolist()
    filter_term = ""

    if 'selected_cliente_id' not in st.session_state:
        clear_inputs()

    def update_form_with_client_data():
        current_boca = st.session_state.boca_final
        if current_boca in st.session_state.clientes_dict:
            found_cliente = st.session_state.clientes_dict[current_boca]
            st.session_state.boca_exists = True
            st.session_state.selected_cliente_id = found_cliente['id']
            st.session_state.razon_social_final = found_cliente['razon_social']
            st.session_state.direccion_final = found_cliente['direccion']
            st.session_state.localidad_final = found_cliente['localidad']
            st.session_state.telefono_final = found_cliente['telefono']
            st.session_state.email_final = found_cliente['email']
            st.session_state.porc_dto_final = float(found_cliente['porc_dto']) if found_cliente['porc_dto'] else 0.0

            if found_cliente['nombre_vendedor']:
                st.session_state.selected_vendedor = found_cliente['nombre_vendedor']
        else:
            st.session_state.boca_exists = False
            st.session_state.selected_cliente_id = None
            st.session_state.razon_social_final = ""
            st.session_state.direccion_final = ""
            st.session_state.localidad_final = ""
            st.session_state.telefono_final = ""
            st.session_state.email_final = ""
            st.session_state.porc_dto_final = 0.0
            st.session_state.selected_vendedor = config.VENDEDOR_DEFAULT

    col1, col2, col3 = st.columns([1, 2, 1],gap="small")

    # Pop temporal para no repetir en el siguiente rerun
    client_data = st.session_state.pop("selected_client_data", {})
    if client_data:
        if not client_data.get("boca") == None:
            st.session_state.boca_final = int(float(client_data.get("boca"))) if client_data.get("boca") else 0
        if client_data.get("razon_social") != "":
            st.session_state.razon_social_final = client_data.get("razon_social")
        if client_data.get("direccion") != "":
            st.session_state.direccion_final = client_data.get("direccion")
        if client_data.get("localidad") != "":
            st.session_state.localidad_final = client_data.get("localidad")
        if client_data.get("telefono") != "":
            st.session_state.telefono_final = client_data.get("telefono")
        if client_data.get("email") != "":
            st.session_state.email_final = client_data.get("email")
        if not client_data.get("porc_dto") == None:
            st.session_state.porc_dto_final = float(client_data.get("porc_dto")) if client_data.get("porc_dto") else 0.0
        if client_data.get("nombre_vendedor") != "":
            st.session_state.selected_vendedor = client_data.get("nombre_vendedor")

    with col1:
        st.number_input(
            "Número de Boca",
            key="boca_final",
            min_value=0,
            step=1,
            help="Ingrese un número de boca existente para editar o uno nuevo para agregar.",
            on_change=update_form_with_client_data
        )

    with col2:
        st.text_input(
            "Razón Social",
            key="razon_social_final",
        )

    with col3:
        try:
            default_index = vendedor_options.index(st.session_state.selected_vendedor)
        except ValueError:
            default_index = 0

        st.selectbox(
            "Repositor",
            options=vendedor_options,
            key="selected_vendedor",
            placeholder="Seleccione un repositor...",
            disabled=False
        )

    col4, col5 = st.columns(2, gap="small")

    with col4:
        st.text_input(
            "Dirección",
            key="direccion_final",
        )

    with col5:
        st.text_input(
            "Localidad",
            key="localidad_final",
        )

    col6, col7, col8 = st.columns([1.5, 2, 1],gap="small")
    with col6:
        st.text_input(
            "Teléfono",
            key="telefono_final",
        )
    with col7:
        st.text_input(
            "Email",
            key="email_final",
        )
    with col8:
        st.number_input(
            "Porcentaje de Descuento",
            key="porc_dto_final",
            step=0.5,
            min_value=0.00
        )

    client_data = None

    with st.form("cliente_form", clear_on_submit=False, border=False):
        is_add_disabled = st.session_state.boca_exists or st.session_state.boca_final == 0
        is_mod_del_disabled = not st.session_state.boca_exists or st.session_state.boca_final == 0

        is_add_disabled = (
                st.session_state.boca_exists 
                or not st.session_state.boca_final
                or st.session_state.show_delete_modal
            )
        is_mod_del_disabled = (
            not st.session_state.boca_exists 
            or not st.session_state.boca_final
            or st.session_state.show_delete_modal
        )
        is_clear_disabled = st.session_state.show_delete_modal

        col_add, col_mod, col_del, col_clear = st.columns(4,gap="small")
        with col_add:
            st.form_submit_button(
                "Agregar Cliente ➕",
                disabled=is_add_disabled,
                on_click=on_add_click, width="stretch"
            )
        with col_mod:
            st.form_submit_button(
                "Modificar Cliente ✍️",
                disabled=is_mod_del_disabled,
                on_click=on_mod_click, width="stretch"
            )
        with col_del:
            st.form_submit_button(
                "Eliminar Cliente 🗑️",
                disabled=is_mod_del_disabled,
                on_click=on_del_click, width="stretch"
            )
        with col_clear:
            if st.form_submit_button("Limpiar Formulario 🔄", width="stretch"):
                del st.session_state.selected_cliente_id
                st.session_state.view_grilla = True
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
        st.warning("⚠️ ¿Está seguro que desea eliminar este cliente? Esta acción no se puede deshacer.")
        col_confirm_del, col_cancel_del, _, _ = st.columns(4,gap="small")
        with col_confirm_del:
            if st.button("Confirmar Eliminación", type="primary", width="stretch"):
                try:
                    delete_existing_cliente(st.session_state.selected_cliente_id)
                    set_status_message(f"🗑️ Cliente '{st.session_state.razon_social_final}' eliminado con éxito.", "success")
                    del st.session_state.selected_cliente_id
                    st.session_state.show_delete_modal = False
                    st.session_state.was_eliminated = True
                    st.session_state.do_filter = True # Obligo a refrescar la grilla
                    st.session_state.view_grilla = True
                    config.init_clientes_articulos()
                    st.rerun()
                except Exception as e:
                    set_status_message(f"❌ Error al eliminar el cliente: {e}", "error")
                    st.rerun()

        with col_cancel_del:
            if st.button("Cancelar Eliminación ❌", width="stretch"):
                st.session_state.show_delete_modal = False
                st.rerun()

    # --- Seccion del filtro personalizado ---
    st.subheader("Filtrar Clientes")
    col_input, col_btn = st.columns([3.5, 1],gap="small")

    with col_input:
        filter_term = st.text_input(
            "Buscar por Boca o Razón Social",
            key="filter_term",
            placeholder="Ingrese un número de boca, una razón social o parte de ellas...",
            label_visibility="collapsed",
            width="stretch",
            value=st.session_state.frase_filtrada,
            disabled=not st.session_state.view_grilla
        )

    with col_btn:
        if st.button("Filtrar", 
                     type="primary", 
                     width="stretch",
                     disabled=not st.session_state.view_grilla):
            # Guardar el texto actual como filtro activo
            st.session_state.frase_filtrada = filter_term.strip()
            st.session_state.do_filter = True
            st.rerun()

    # Lógica de filtrado
    estado_grilla = "totales"
    # Si hay una frase filtrada previa, usarla aunque no se haya presionado el botón
    if st.session_state.frase_filtrada.strip():
        active_filter = st.session_state.frase_filtrada.lower()
        st.session_state.filtered_df = st.session_state.clientes_df[
            st.session_state.clientes_df['boca'].astype(str).str.contains(active_filter, na=False) |
            st.session_state.clientes_df['razon_social'].str.lower().str.contains(active_filter, na=False)
        ]
        estado_grilla = "filtrados"
    else:
        st.session_state.filtered_df = st.session_state.clientes_df.copy()

    if "filtered_df" not in st.session_state:
        st.session_state.filtered_df = st.session_state.clientes_df.copy()

    if st.session_state.view_grilla:

        st.header(f"Maestro de Clientes ({len(st.session_state.filtered_df)} {estado_grilla})")
        if not st.session_state.filtered_df.empty:

            # --- Parámetros de configuración ---
            max_filas_a_mostrar = 20
            alto_del_encabezado = 36
            alto_de_la_fila = 35

            # --- Lógica para ajustar la altura ---
            # Calculamos el número de filas reales a mostrar
            num_filas_a_mostrar = min(len(st.session_state.filtered_df), max_filas_a_mostrar)

            # Calculamos la altura final
            alto_df = alto_del_encabezado + alto_de_la_fila * num_filas_a_mostrar

            # Rellena los valores nulos para las columnas de texto en una sola operación
            # Crea un diccionario con las columnas de texto y su valor de relleno
            values_to_fill = {
                'boca': '',
                'razon_social': '',
                'nombre_vendedor': '',
                'direccion': '',
                'localidad': '',
                'telefono': '',
                'email': ''
            }
            st.session_state.filtered_df = st.session_state.filtered_df.fillna(value=values_to_fill)

            # Eliminamos valores None en porc_dto
            try:
                st.session_state.filtered_df['porc_dto'] = st.session_state.filtered_df['porc_dto'].fillna(0.0)
            except:
                pass

            # --- Preparar una copia y agregar la columna temporal 'Seleccionado' ---
            df_to_show = st.session_state.filtered_df.copy().reset_index(drop=True)

            # Insertamos la columna temporal "Seleccionado" solo si no existe
            if "Seleccionado" not in df_to_show.columns:
                df_to_show.insert(0, "Seleccionado", False)

            # Columnas que dejaremos NO editables (todas salvo la columna Seleccionado)
            disabled_cols = [c for c in df_to_show.columns if c != "Seleccionado"]

            # Se Cambia la key del data_editor cada vez por posibles selecciones de registro
            editor_key = f"clientes_grid_{st.session_state.get('grid_version', 0)}"

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
                    'Seleccionado', 'boca', 'razon_social', 'nombre_vendedor', 'direccion', 'localidad', 'telefono', 'porc_dto', 'email', 'fecha_mod'
                ],
                column_config={
                    "Seleccionado": st.column_config.CheckboxColumn("✔",
                                    help="Marque alguna de estas casillas de verificación para editar el cliente.",
                                    width=50),
                    "boca": st.column_config.NumberColumn("Boca",
                                    width=calcular_ancho_columna(df_to_show,"boca")),
                    "razon_social": st.column_config.TextColumn("Razón Social",
                                                            width=calcular_ancho_columna(df_to_show,"razon_social")),
                    "nombre_vendedor": st.column_config.TextColumn("Vendedor", width="small"),
                    "direccion": st.column_config.TextColumn("Dirección",
                                    width=calcular_ancho_columna(df_to_show,"direccion")),
                    "localidad": st.column_config.TextColumn("Localidad",
                                    width=calcular_ancho_columna(df_to_show,"localidad")),
                    "telefono": st.column_config.TextColumn("Teléfono",
                                    width=calcular_ancho_columna(df_to_show,"telefono")),
                    "porc_dto": st.column_config.NumberColumn(
                        "Dto. %",
                        width=calcular_ancho_columna(df_to_show,"porc_dto"),
                        format="%.2f"
                    ),
                    "email": st.column_config.TextColumn("Email",
                                    width=calcular_ancho_columna(df_to_show,"email")),
                    "fecha_mod": st.column_config.DatetimeColumn(
                        "Última Modificación",
                        width=calcular_ancho_columna(df_to_show,"fecha_mod")
                    )
                }
            )

            # --- Detectar selección(s) y cargar el cliente en el form ---
            selected_idxs = edited_df.index[edited_df["Seleccionado"] == True].tolist()

            if selected_idxs:
                # Tomo la primera selección
                idx = selected_idxs[0]
                selected_row = edited_df.loc[idx]

                # Guardamos todos los datos de interés en un diccionario temporal
                st.session_state.selected_client_data = {
                    "boca": selected_row["boca"],
                    "razon_social": selected_row["razon_social"],
                    "direccion": selected_row["direccion"],
                    "localidad": selected_row["localidad"],
                    "telefono": selected_row["telefono"],
                    "email": selected_row["email"],
                    "porc_dto": float(selected_row["porc_dto"]) if selected_row["porc_dto"] else None,
                    "nombre_vendedor": selected_row["nombre_vendedor"]
                }

                st.session_state.boca_exists = True
                st.session_state.selected_cliente_id = int(selected_row["id"])
                st.session_state.grid_version = st.session_state.get('grid_version', 0) + 1

                st.session_state.view_grilla = False
                st.rerun()

            else:
                st.session_state.selected_client_data = {
                    "boca": None,
                    "razon_social": "",
                    "direccion": "",
                    "localidad": "",
                    "telefono": "",
                    "email": "",
                    "porc_dto": None,
                    "nombre_vendedor": ""
                }

        else:
            st.info("No hay clientes registrados.")
    else:
        message_caption = "ATENCIÓN: La Grilla de Datos para visualización y búsquedas se habilitará "
        message_caption += "cuando Modifique, Elimine o Limpie el formulario."
        st.write( "✋ " + message_caption)

    st.markdown(f"`{config.FOOTER_APP}`")

if __name__ == "__main__":
    clientes_crud()