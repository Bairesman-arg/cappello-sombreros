# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import date, datetime
from models import get_remito_completo, delete_remito
import config
import time

def remitos_anulaciones():
    st.set_page_config(layout="wide")
    st.title(config.TITULO_APP)
    st.header("Anulación de Remitos")

    # Inicializar variables de estado
    if "show_confirm_modal" not in st.session_state:
        st.session_state.show_confirm_modal = False
    if "is_form_disabled" not in st.session_state:
        st.session_state.is_form_disabled = False
    if "should_reset_all" not in st.session_state:
        st.session_state.should_reset_all = False
    if "remito_deleted" not in st.session_state:
        st.session_state.remito_deleted = False
    if "delete_success_shown" not in st.session_state:
        st.session_state.delete_success_shown = False

    # Manejo de flags de rerun
    if st.session_state.should_reset_all:
        # Limpiar session state
        keys_to_clear = ["remito_activo"] + [k for k in st.session_state.keys() if k.startswith("remito_")]
        for k in keys_to_clear:
            st.session_state.pop(k, None)
        st.session_state.should_reset_all = False
        st.session_state.show_confirm_modal = False
        st.session_state.is_form_disabled = False
        st.session_state.remito_deleted = False
        st.session_state.delete_success_shown = False
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
                st.session_state.remito_deleted = False
                st.session_state.delete_success_shown = False
            else:
                st.session_state["carga_exitosa"] = False

    with col1:
        remito_id = st.number_input(
            label="Número de Remito a Anular:",
            min_value=1, 
            step=1, 
            key="input_remito",
            on_change=cargar_remito_auto,
            help="Ingrese un Remito existente para anular.",
            disabled=st.session_state.is_form_disabled or st.session_state.remito_deleted
        )

    # Mostrar mensajes después de cualquier carga
    if "carga_exitosa" in st.session_state:
        if not st.session_state["carga_exitosa"]:
            st.error("No se encontró el remito.")
            st.stop()
        # Limpiar el flag
        del st.session_state["carga_exitosa"]

    # --- Mostrar formulario si hay remito activo ---
    if "remito_activo" in st.session_state and not st.session_state.remito_deleted:
        remito_id = st.session_state["remito_activo"]
        cab_key = f"remito_{remito_id}_cab"
        items_key = f"remito_{remito_id}_items"
        
        if cab_key in st.session_state and items_key in st.session_state:
            cab = st.session_state[cab_key]
            items_df = st.session_state[items_key]
            
            # Mostrar información de cabecera (solo lectura)
            st.subheader(f"Remito #{remito_id} - VISTA PREVIA PARA ANULACIÓN")
            
            # Información del cliente
            st.info(f"**Cliente:** {cab['razon_social']} (Boca {cab['boca']})")

            col_izq, col_der = st.columns(2, gap="small")

            with col_izq:
                st.date_input(
                    "Fecha de Entrega", 
                    value=cab["fecha_entrega"], 
                    format="DD/MM/YYYY", 
                    disabled=True,
                    key=f"fecha_entrega_{remito_id}"
                )
                
                # Mostrar fecha de retiro si existe
                fecha_retiro_value = cab.get("fecha_retiro")
                if fecha_retiro_value:
                    st.date_input(
                        "Fecha de Retiro",
                        value=fecha_retiro_value,
                        format="DD/MM/YYYY",
                        disabled=True,
                        key=f"fecha_retiro_{remito_id}"
                    )
                else:
                    st.text_input(
                        "Fecha de Retiro",
                        value="No registrada",
                        disabled=True,
                        key=f"fecha_retiro_text_{remito_id}"
                    )

            with col_der:
                observaciones_value = cab.get("observaciones") or "Sin observaciones"
                st.text_area(
                    "Observaciones del Remito",
                    value=observaciones_value,
                    key=f"obs_remito_{remito_id}",
                    height=150,
                    disabled=True
                )

            # --- Mostrar items (solo lectura) ---
            st.subheader("Items del Remito")

            if not items_df.empty:
                # Calcular totales
                total_entregados = int(items_df["entregados"].sum()) if "entregados" in items_df.columns else 0
                total_devueltos = int(items_df["devueltos"].sum()) if "devueltos" in items_df.columns else 0
                total_vendidos = total_entregados - total_devueltos

                items_df['observaciones'] = items_df['observaciones'].fillna('')

                # Mostrar dataframe de items (solo lectura)
                st.dataframe(
                    items_df,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "nro_articulo": st.column_config.TextColumn("Artículo", width="small"),
                        "descripcion": st.column_config.TextColumn("Descripción", width="medium"),
                        "precio_real": st.column_config.NumberColumn("Precio Real", format="$%.2f", width="medium"),
                        "entregados": st.column_config.NumberColumn("Entregados", width="small"),
                        "devueltos": st.column_config.NumberColumn("Devueltos", width="small") if "devueltos" in items_df.columns else None,
                        "observaciones": st.column_config.TextColumn("Observaciones", width="medium"),
                    }
                )

                # Mostrar totales
                c1, c2, c3 = st.columns(3, gap="small")
                c1.metric("Total Entregados", total_entregados)
                if "devueltos" in items_df.columns:
                    c2.metric("Total Devueltos", total_devueltos)
                    c3.metric("Total Vendidos", total_vendidos)
                else:
                    c2.metric("Estado", "Solo Entrega")
                    c3.metric("Items Únicos", len(items_df))
            else:
                st.info("El remito no tiene items registrados.")

            # === BOTONES DE ACCIÓN ===
            st.header("Acciones de Anulación")

            col_buttons = st.columns([2, 1, 2], gap="small")

            # Botón de Anular Remito
            with col_buttons[1]:
                if st.button("🗑️ ANULAR REMITO", 
                           type="secondary", 
                           width="stretch",
                           disabled=st.session_state.is_form_disabled):
                    st.session_state.show_confirm_modal = True
                    st.rerun()

            # Botón Nuevo Remito
            with col_buttons[0]:
                if st.button("Consultar Otro Remito", 
                           width="stretch",
                           disabled=st.session_state.is_form_disabled):
                    st.session_state.should_reset_all = True
                    st.rerun()

            # Espacio para simetría visual
            with col_buttons[2]:
                st.empty()

    # Mostrar mensaje de éxito si se eliminó el remito
    if st.session_state.remito_deleted and not st.session_state.get('delete_success_shown', False):
        st.success(f"✅ Remito #{st.session_state.get('deleted_remito_id', 'N/A')} anulado exitosamente!")
        st.balloons()
        st.session_state.delete_success_shown = True

    # === MODAL DE CONFIRMACIÓN ===
    if st.session_state.show_confirm_modal:
        st.warning(f"¿Está COMPLETAMENTE SEGURO que desea anular el Remito #{st.session_state['remito_activo']}?")
        col_confirm, col_cancel = st.columns(2, gap="small")

        with col_confirm:
            if st.button("🗑️ SÍ, ANULAR DEFINITIVAMENTE", 
                        type="primary",
                        width="stretch"):
                # Ejecutar la eliminación
                remito_id = st.session_state["remito_activo"]
                success = delete_remito(remito_id)
                
                if success:
                    st.session_state.remito_deleted = True
                    st.session_state.deleted_remito_id = remito_id
                    st.session_state.show_confirm_modal = False
                    st.session_state.delete_success_shown = False
                    # Resetear automáticamente después de anular
                    st.session_state.should_reset_all = True
                    st.toast('El Remito ha sido eliminado!', icon='🗑️')
                    time.sleep(0.75)
                    st.rerun()
                else:
                    st.error("Error al anular el remito. Intente nuevamente.")

        with col_cancel:
            if st.button("❌ Cancelar", 
                        width="stretch"):
                st.session_state.show_confirm_modal = False
                st.rerun()

    # Footer
    st.markdown(f"`{config.FOOTER_APP}`")

if __name__ == "__main__":
    remitos_anulaciones()