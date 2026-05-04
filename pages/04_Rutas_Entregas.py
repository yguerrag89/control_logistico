from __future__ import annotations

from datetime import datetime

import streamlit as st

from modules.gps_matcher import reconcile_route_with_gps, route_gps_reconciliation_view
from modules.logistics_repository import (
    add_delivery_evidence,
    create_delivery,
    create_route,
    get_route,
    list_deliveries,
    list_routes,
    save_evidence_file,
    validate_delivery_time_against_route,
)
from modules.operations import finalize_route, route_closure_snapshot
from modules.repository import list_conductors, list_units
from modules.session import sidebar_user_context
from modules.navigation import run_legacy_page

ctx = sidebar_user_context()
usuario = ctx["usuario"]
rol = ctx["rol"]
conductor_id_sesion = ctx.get("conductor_id")

st.title("🚚 Rutas y entregas")

if rol == "Chofer":
    st.caption("Modo móvil para chofer: captura solo tu ruta, entregas, evidencias y cierre.")
    section = "Modo chofer"
else:
    st.caption("Captura operativa, modo chofer, cierre de ruta y conciliación GPS en un solo flujo.")
    sections = ["Modo chofer", "Panel de rutas", "Cierre operativo", "Conciliación GPS", "Administración avanzada"]
    section = st.radio("Sección", sections, index=1, horizontal=True)
    st.divider()

units = list_units(active_only=True)
conductors = list_conductors(active_only=True)
unit_options = {u["id"]: u["placas"] for u in units}
conductor_options = {c["id"]: c["nombre"] for c in conductors}

if section == "Modo chofer":
    st.subheader("📱 Modo chofer")

    if rol == "Chofer":
        if not conductor_id_sesion:
            st.error("Tu usuario de chofer no está vinculado a un conductor activo. Pide al administrador revisar Catálogos > Usuarios.")
            st.stop()
        selected_conductor = int(conductor_id_sesion)
        st.info(f"Chofer: **{ctx.get('conductor_nombre') or usuario}**")
    else:
        st.caption("Administrador probando el modo chofer.")
        if conductor_options:
            selected_conductor = st.selectbox("Chofer", options=list(conductor_options.keys()), format_func=lambda x: conductor_options[x])
        else:
            st.error("No hay conductores activos.")
            st.stop()

    fecha = st.date_input("Fecha de ruta", value=datetime.now().date())
    routes = list_routes({"fecha_desde": str(fecha), "fecha_hasta": str(fecha), "conductor_id": selected_conductor})

    if routes.empty:
        st.warning("No tienes ruta creada para esta fecha. Crea una ruta rápida antes de registrar entregas.")
        with st.form("quick_route_form", border=True):
            if not unit_options:
                st.error("No hay unidades activas.")
                st.stop()
            unidad_id = st.selectbox("Unidad", options=list(unit_options.keys()), format_func=lambda x: unit_options[x])
            salida = st.time_input("Hora de salida", value=datetime.now().time().replace(second=0, microsecond=0))
            obs = st.text_area("Observaciones iniciales", value="", placeholder="Opcional")
            submit = st.form_submit_button("✅ Crear ruta", use_container_width=True, type="primary")
        if submit:
            route_id = create_route({
                "fecha": str(fecha),
                "unidad_id": int(unidad_id),
                "conductor_id": int(selected_conductor),
                "hora_salida_reportada": salida.strftime("%H:%M"),
                "hora_regreso_reportada": None,
                "estado_ruta": "Abierta",
                "observaciones_generales": obs.strip(),
            }, motivo="Alta rápida chofer", comentario="Ruta creada desde modo chofer", usuario=usuario)
            st.success(f"Ruta #{route_id} creada y guardada en la base de datos.")
            st.rerun()
        st.stop()

    routes["label"] = routes.apply(
        lambda r: f"#{r['id']} | {r['placas']} | salida {r.get('hora_salida_reportada') or '-'} | {r['estado_ruta']}",
        axis=1,
    )
    route_id = st.selectbox("Ruta del día", options=routes["id"].tolist(), format_func=lambda x: routes.loc[routes["id"] == x, "label"].iloc[0])
    route = get_route(int(route_id))
    if not route:
        st.error("No se encontró la ruta seleccionada.")
        st.stop()

    st.success(f"Ruta #{route_id} | Unidad {route['placas']} | Estado: {route['estado_ruta']}")

    st.markdown("### Registrar entrega / visita")
    with st.form("quick_delivery_form", border=True):
        cliente = st.text_input("Cliente", placeholder="Ej. Inova")
        destino = st.text_input("Destino / punto operativo", placeholder="Ej. Naucalpan / Tresguerras / CEDIS")
        hora_llegada = st.time_input("Hora de llegada", value=datetime.now().time().replace(second=0, microsecond=0))
        estatus = st.selectbox(
            "Estatus",
            ["Entregado completo", "Entregado parcial", "No entregado", "Rechazado", "Cliente cerrado", "Reprogramado", "Entregado en paquetería", "Visita sin entrega"],
        )
        motivo = None
        if estatus != "Entregado completo":
            motivo = st.selectbox(
                "Motivo",
                ["Cliente cerrado", "No recibió por horario", "Producto incompleto", "Producto incorrecto", "Producto dañado", "Falta de documentación", "Dirección incorrecta", "No había cita", "Rechazo del cliente", "No dio tiempo", "Otro"],
            )
        foto = st.file_uploader("Foto de evidencia", type=["jpg", "jpeg", "png"], accept_multiple_files=False)
        observaciones = st.text_area("Observaciones", value="", placeholder="Opcional")
        save = st.form_submit_button("💾 Guardar entrega", use_container_width=True, type="primary")
    if save:
        h = hora_llegada.strftime("%H:%M")
        errs = []
        if not cliente.strip():
            errs.append("Captura el cliente.")
        if not destino.strip():
            errs.append("Captura el destino.")
        errs.extend(validate_delivery_time_against_route(route, h))
        if errs:
            for e in errs:
                st.error(e)
        else:
            delivery_id = create_delivery({
                "ruta_id": int(route_id),
                "cliente_nombre": cliente.strip(),
                "destino_nombre": destino.strip(),
                "destino_id": None,
                "hora_llegada_reportada": h,
                "estatus_entrega": estatus,
                "motivo_no_entrega": motivo,
                "observaciones": observaciones.strip(),
                "estado_conciliacion_gps": "Pendiente de GPS",
            }, motivo="Captura chofer", comentario="Entrega registrada en modo chofer", usuario=usuario)
            if foto is not None:
                path = save_evidence_file(foto, route, delivery_id)
                if path:
                    add_delivery_evidence(delivery_id, path, "Evidencia ruta", observaciones.strip(), usuario=usuario)
            st.success(f"Entrega #{delivery_id} guardada correctamente en la base de datos.")
            st.rerun()

    st.markdown("### Entregas capturadas")
    deliveries = list_deliveries(route_id=int(route_id))
    if deliveries.empty:
        st.info("Todavía no hay entregas capturadas.")
    else:
        cols = ["orden_calculado", "cliente_nombre", "destino_nombre", "hora_llegada_reportada", "estatus_entrega", "estado_conciliacion_gps"]
        st.dataframe(deliveries[cols], use_container_width=True, hide_index=True)

    st.markdown("### Cerrar ruta")
    with st.form("close_route_driver", border=True):
        regreso = st.time_input("Hora de regreso", value=datetime.now().time().replace(second=0, microsecond=0))
        comentario = st.text_area("Observación de cierre", value="", placeholder="Opcional")
        close = st.form_submit_button("🏁 Cerrar ruta", use_container_width=True)
    if close:
        from modules.logistics_repository import update_route
        payload = route.copy()
        payload.update({
            "hora_regreso_reportada": regreso.strftime("%H:%M"),
            "estado_ruta": "Cerrada pendiente de GPS",
            "observaciones_generales": (route.get("observaciones_generales") or "") + ("\n" + comentario if comentario else ""),
        })
        update_route(int(route_id), payload, motivo="Cierre chofer", comentario=comentario, usuario=usuario)
        st.success("Ruta cerrada y guardada. Queda pendiente de GPS/validación administrativa.")
        st.rerun()

elif section == "Panel de rutas":
    st.subheader("Panel de rutas")
    st.caption("Vista de supervisión: rutas, entregas, evidencias y estados.")
    run_legacy_page("07_Rutas.py")
    st.divider()
    run_legacy_page("08_Entregas_Ruta.py")

elif section == "Cierre operativo":
    st.subheader("Cierre operativo de ruta")
    routes = list_routes({"fecha_desde": "2026-01-01"})
    if routes.empty:
        st.info("No hay rutas para cerrar.")
        st.stop()
    routes["label"] = routes.apply(lambda r: f"#{r['id']} | {r['fecha']} | {r['placas']} | {r['conductor_nombre']} | {r['estado_ruta']} | {r['entregas_capturadas']} entregas", axis=1)
    route_id = st.selectbox("Ruta", options=routes["id"].tolist(), format_func=lambda x: routes.loc[routes["id"] == x, "label"].iloc[0])
    snapshot = route_closure_snapshot(int(route_id))
    if not snapshot:
        st.error("No se encontró la ruta.")
        st.stop()
    route = snapshot["route"]
    st.info(f"Ruta #{route['id']} | {route['fecha']} | {route['placas']} | {route['conductor_nombre']} | Estado actual: {route['estado_ruta']}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Entregas", snapshot["entregas"])
    m2.metric("Con GPS", snapshot["entregas_con_gps"])
    m3.metric("Sin evidencia", snapshot["entregas_sin_evidencia"])
    m4.metric("Paradas GPS no asociadas", snapshot["paradas_gps_no_asociadas"])
    m5, m6, m7 = st.columns(3)
    m5.metric("Pendientes GPS", snapshot["entregas_pendientes_gps"])
    m6.metric("Incidencias entrega", snapshot["entregas_con_incidencia"])
    m7.metric("Fuera de horario", snapshot["entregas_fuera_horario"])

    if st.button("Ejecutar conciliación GPS", type="primary"):
        try:
            result = reconcile_route_with_gps(int(route_id))
            st.success(f"Conciliación ejecutada. Estado: {result.get('estado_ruta_resultante')}")
            st.json(result)
        except Exception as exc:
            st.error(f"No se pudo conciliar: {exc}")

    view = route_gps_reconciliation_view(int(route_id))
    if not view.empty:
        st.markdown("### Entregas conciliadas")
        cols = ["entrega_id", "cliente_nombre", "destino_nombre", "hora_llegada_reportada", "estatus_entrega", "estado_conciliacion_gps", "inicio_gps", "fin_gps", "tiempo_en_cliente_seg", "direccion_gps"]
        st.dataframe(view[[c for c in cols if c in view.columns]], use_container_width=True, hide_index=True)

    st.markdown("### Validación final")
    recommended = "Validada completa" if snapshot["entregas"] and snapshot["entregas_pendientes_gps"] == 0 and snapshot["entregas_fuera_horario"] == 0 else "Validada con incidencias"
    final_status = st.selectbox("Estado final", ["Validada completa", "Validada con incidencias", "Pendiente de corrección", "Pendiente de GPS", "Anulada"], index=["Validada completa", "Validada con incidencias", "Pendiente de corrección", "Pendiente de GPS", "Anulada"].index(recommended))
    comentario = st.text_area("Comentario de cierre obligatorio", value="")
    confirm = st.checkbox("Confirmo que revisé entregas, evidencias y GPS disponibles.")
    if st.button("Guardar cierre operativo"):
        if not comentario.strip():
            st.error("El comentario de cierre es obligatorio.")
        elif not confirm:
            st.error("Confirma la revisión antes de cerrar.")
        else:
            finalize_route(int(route_id), final_status, comentario.strip(), usuario=usuario)
            st.success("Cierre operativo guardado con auditoría.")

elif section == "Conciliación GPS":
    run_legacy_page("10_Conciliacion_GPS.py")

else:
    st.subheader("Administración avanzada")
    st.caption("Acceso a páginas técnicas heredadas para correcciones detalladas.")
    tab1, tab2 = st.tabs(["Rutas", "Entregas"])
    with tab1:
        run_legacy_page("07_Rutas.py")
    with tab2:
        run_legacy_page("08_Entregas_Ruta.py")
