# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import date, datetime
from models import get_remito_completo, update_remito_data
from gen_remito import gen_remito
import numpy as np
import time
import config

def remitos_ventas():
    # st.set_page_config(layout="wide")
    st.title(config.TITULO_APP)
    st.header("Remitos - Devoluciones y Ventas")

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
        st.session_state["input_remito"] = 1

    if "remito_grabado" not in st.session_state:
        st.session_state.remito_grabado = False
    if "error_grabacion" not in st.session_state:
        st.session_state.error_grabacion = False
    if "success_shown" not in st.session_state:
        st.session_state.success_shown = False
    if "remito_saved" not in st.session_state:
        st.session_state.remito_saved = False

    # Manejo de flags de rerun
    if st.session_state.should_reset_all:
        # Limpiar session state para nuevo remito
        keys_to_clear = ["remito_activo"] + [k for k in st.session_state.keys() if k.startswith("remito_")]
        for k in keys_to_clear:
            st.session_state.pop(k, None)
        st.session_state.should_reset_all = False
        st.session_state.show_confirm_modal = False
        st.session_state.is_form_disabled = False
        st.session_state.success_shown = False
        st.session_state.remito_saved = False
        st.session_state.input_remito = 1
        st.rerun()

    # Control de estado del formulario
    st.session_state.is_form_disabled = st.session_state.show_confirm_modal

    # --- Entrada de número de remito ---
    col1, _ = st.columns([1, 4], gap="small")

    # Función para cargar remito automáticamente
    def cargar_remito_auto():
        if "input_remito" in st.session_state:
            remito_id = st.session_state["input_remito"]
            datos = get_remito_completo(remito_id)
            if datos:
                items = datos["cabecera"]
                items_df = datos["items"].copy()
                                
                st.session_state[f"remito_{remito_id}_cab"] = items
                st.session_state[f"remito_{remito_id}_items"] = items_df
                st.session_state["remito_activo"] = remito_id
                st.session_state["carga_exitosa"] = True
                st.session_state.remito_saved = False  # Reset cuando se carga un nuevo remito
                st.session_state.success_shown = False
            else:
                st.session_state["carga_exitosa"] = False

    with col1:
        remito_id = st.number_input(
            label="Ingrese el número de Remito:",
            min_value=1, 
            step=1, 
            key="input_remito",
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
    if "remito_activo" in st.session_state:
        remito_id = st.session_state["remito_activo"]
        cab_key = f"remito_{remito_id}_cab"
        items_key = f"remito_{remito_id}_items"
        
        if cab_key in st.session_state and items_key in st.session_state:
            cab = st.session_state[cab_key]
            
            st.subheader(f"Remito #{remito_id}  |  Cliente: {cab['razon_social']} (Boca {cab['boca']})")

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

            st.subheader("Items del Remito")

            col_edit, col_calc = st.columns([4, 1], gap="small")
            
            with col_edit:
                st.markdown("#### Editar Devoluciones y Observaciones")
                
                # Grilla editable principal SIN callback
                st.data_editor(
                    st.session_state[items_key],
                    hide_index=True,
                    width="stretch",
                    column_order=["nro_articulo", "descripcion", "entregados", "devueltos", "observaciones"],
                    column_config={
                        "nro_articulo": st.column_config.TextColumn("Artículo", disabled=True, width="small"),
                        "descripcion": st.column_config.TextColumn("Descripción", disabled=True, width="medium"),
                        "entregados": st.column_config.NumberColumn("Entregados", disabled=True, width="small"),
                        "devueltos": st.column_config.NumberColumn(
                            "devueltos", 
                            min_value=0,
                            step=1,
                            width="small"
                        ),
                        "Observaciones": st.column_config.TextColumn("observaciones", width="medium"),
                    },
                    disabled=["nro_articulo", "descripcion", "entregados"] + (["devueltos", "observaciones"] if st.session_state.is_form_disabled else []),
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
            
            # VALIDAR que devueltos no superen entregados
            items_invalidos = pd.DataFrame()
            try:
                if "devueltos" in df_editado.columns and "entregados" in df_editado.columns:
                    items_invalidos = df_editado[df_editado["devueltos"] > df_editado["entregados"]]
                    if not items_invalidos.empty:
                        articulos_problema = items_invalidos["nro_articulo"].tolist()
                        st.warning(f"⚠️ Los artículos {articulos_problema} tienen más devueltos que entregados. Corregir antes de guardar.")
            except Exception as e:
                st.error(f"Error en validación: {str(e)}")

            with col_calc:
                st.markdown("#### Vendidos")
                
                # Calcular vendidos con el DataFrame actualizado
                if "devueltos" in df_editado.columns and "entregados" in df_editado.columns:
                    vendidos_valores = np.where(df_editado["devueltos"] == 0, 0, 
                             df_editado["entregados"] - df_editado["devueltos"])

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

            # --- Totales ---
            if isinstance(df_editado, pd.DataFrame) and "devueltos" in df_editado.columns and "entregados" in df_editado.columns:
                try:
                    total_entregados = int(df_editado["entregados"].sum())
                    total_devueltos = int(df_editado["devueltos"].sum())
                    total_vendidos = total_entregados - total_devueltos
                except:
                    total_entregados = total_devueltos = total_vendidos = 0
            else:
                total_entregados = total_devueltos = total_vendidos = 0

            c1, c2, c3 = st.columns(3, gap="small")
            c1.metric("Total Entregados", total_entregados)
            c2.metric("Total Devueltos", total_devueltos)
            c3.metric("Total Vendidos", total_vendidos)

            # === BOTONES PRINCIPALES (siguiendo la lógica de remitos_entregas.py) ===
            st.header("Acciones del Remito")

            # Verificar que no haya errores de validación
            tiene_errores = not items_invalidos.empty
            is_remito_saved = st.session_state.remito_saved
            can_save = not tiene_errores  # En ventas, solo necesitamos que no haya errores

            col_buttons = st.columns(3, gap="small")

            # Botón Guardar
            say_error = False
            with col_buttons[0]:
                if st.button("Guardar Remito", type="primary", use_container_width=True,
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
                    # Siempre mostrar modal de confirmación en ventas
                    st.session_state.show_confirm_modal = True
                    st.rerun()

            # Botón Generar/Descargar Remito
            with col_buttons[2]:
                if is_remito_saved:
                    try:
                        excel_buffer = gen_remito(remito_id, is_retiro=True)
                        
                        # Crear un contenedor para el botón y manejar la descarga
                        download_clicked = st.download_button(
                            label=f"Descargar Remito #{remito_id}",
                            use_container_width=True,
                            data=excel_buffer,
                            file_name=f"Remito_{remito_id}_Ventas.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_remito_{remito_id}"
                        )
                        
                        # Después de la descarga, resetear automáticamente sin confirmación
                        if download_clicked:
                            st.session_state.should_reset_all = True
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"Error al generar el remito: {str(e)}")
                        if st.button("Generar Remito", use_container_width=True, disabled=True):
                            pass
                else:
                    st.button("Generar Remito", use_container_width=True, disabled=True)

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
                    if st.button("Sí, continuar", width="stretch"):
                        st.session_state.show_confirm_modal = False
                        st.session_state.should_reset_all = True
                        st.rerun()

                with col_cancel:
                    if st.button("Cancelar", width="stretch"):
                        st.session_state.show_confirm_modal = False
                        st.rerun()

    # Footer
    st.markdown(f"`{config.FOOTER_APP}`")

if __name__ == "__main__":
    remitos_ventas()