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
    st.set_page_config(layout="wide")
    st.title(config.TITULO_APP)
    st.header("Remitos - Devoluciones y Ventas")

    # Inicializamos la variable de estado para los botones de confirmación
    if "confirmar_nuevo" not in st.session_state:
        st.session_state["confirmar_nuevo"] = False

    if  st.session_state["confirmar_nuevo"]:
        st.session_state["input_remito"] = 1

    if "remito_grabado" not in st.session_state:
        st.session_state.remito_grabado = False
    if "error_grabacion" not in st.session_state:
        st.session_state.error_grabacion = False

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
                
                # Agregar columnas editables
                # items_df["Devueltos"] = 0
                # items_df["Observaciones"] = ""
                
                st.session_state[f"remito_{remito_id}_cab"] = items
                st.session_state[f"remito_{remito_id}_items"] = items_df
                st.session_state["remito_activo"] = remito_id
                st.session_state["carga_exitosa"] = True
            else:
                st.session_state["carga_exitosa"] = False

    with col1:
        remito_id = st.number_input(
            label="Ingrese el número de Remito:",
            min_value=1, 
            step=1, 
            key="input_remito",
            on_change=cargar_remito_auto,
            help="Ingrese un Remito existente para editar."
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
                    value=date.today(),
                    format="DD/MM/YYYY",
                    key=f"fecha_retiro_{remito_id}"
                )

            with col_der:
                nuevas_observaciones = st.text_area(
                    "Observaciones del Remito  ( notas privadas )",
                    value=cab.get("observaciones") or "",
                    key=f"obs_remito_{remito_id}",
                    height=150
                )

            #   st.divider()
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
                    disabled=["nro_articulo", "descripcion", "entregados"],
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
                    # vendidos_valores = df_editado["entregados"] - df_editado["devueltos"]
                    # vendidos_valores = df_editado["devueltos"] if df_editado["devueltos"] == 0 else df_editado["entregados"] - df_editado["devueltos"]
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

            # --- Botones de acción ---
            col_g, col_n, col_i = st.columns(3)

            with col_g:
                # Verificar que no haya errores de validación antes de guardar
                items_invalidos = df_editado[df_editado["devueltos"] > df_editado["entregados"]]
                tiene_errores = not items_invalidos.empty
                
                if st.button("Guardar Remito", type="primary", width="stretch", key=f"btn_guardar_{remito_id}", disabled=tiene_errores):
                    try:
                        update_remito_data(
                            remito_id=remito_id,
                            fecha_retiro=nueva_fecha_retiro,
                            observaciones_cabecera=nuevas_observaciones,
                            items_df=df_editado
                        )
                        # st.success("✅ Remito actualizado con éxito.")
                        st.session_state.remito_grabado = True

                    except Exception as e:
                        # st.error(f"❌ Error al guardar: {str(e)}")
                        st.session_state.error_grabacion = True
                        
                if tiene_errores:
                    st.caption("⚠️ Botón deshabilitado por errores de validación")

            with col_n:
                # Este botón solo activa la variable de estado
                if st.button("Nuevo Remito", width="stretch", key=f"btn_nuevo_{remito_id}"):
                    # st.session_state["confirmar_nuevo"] = True
                    keys_to_clear = ["remito_cab", "remito_items", "remito_activo"]
                    for k in keys_to_clear:
                        st.session_state.pop(k, None)

                    st.session_state["confirmar_nuevo"] = False
                    st.toast("¡Acción completada con éxito!", icon="👍")
                    # time.sleep(0.5)
                    st.rerun()
                """    
                # Esta condición se encarga de mostrar los botones de confirmación
                if st.session_state["confirmar_nuevo"]:
                    #  st.warning("⚠️ Se perderán los cambios ¿Está seguro?")
                    #  col_confirm_nuevo, col_espacio, col_cancelar = st.columns([1, 4, 1])
                    col_confirm_nuevo, col_cancelar = st.columns([1, 1])
                    with col_confirm_nuevo:
                        if st.button("Confirmar", type="primary", 
                                     key="btn_confirmar_nuevo", 
                                     width="stretch", 
                                     help="Se perderán los cambios ¿Está seguro?"):
                            # Limpiar session state
                            keys_to_clear = ["remito_cab", "remito_items", "remito_activo"]
                            for k in keys_to_clear:
                                st.session_state.pop(k, None)

                            st.session_state["confirmar_nuevo"] = False
                            st.toast("¡Acción completada con éxito!", icon="👍")
                            # time.sleep(0.5)
                            st.rerun()

                    with col_cancelar:
                        if st.button("Cancelar", key="btn_cancelar_nuevo", width="stretch"):
                            st.session_state["confirmar_nuevo"] = False
                            st.rerun()
                """
            with col_i:
                if st.button("Imprimir Remito", width="stretch", key=f"btn_imprimir_{remito_id}"):
                    try:
                        # Aquí iría la lógica de gen_remito
                        pdf_data = gen_remito(remito_id, df_editado)
                        st.download_button(
                            "📄 Descargar Remito",
                            data=pdf_data,
                            file_name=f"Remito_{remito_id}_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            width="stretch",
                            key=f"btn_download_{remito_id}"
                        )
                    except Exception as e:
                        st.error(f"❌ Error al generar el remito: {str(e)}")

            if st.session_state.remito_grabado:
                st.balloons()
                st.success("✅ Remito actualizado con éxito.")
            if st.session_state.error_grabacion:
                st.error(f"❌ Error al guardar: {str(e)}")

            st.session_state.remito_grabado = False
            st.session_state.error_grabacion = False

if __name__ == "__main__":
    remitos_ventas()