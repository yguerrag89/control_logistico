from __future__ import annotations

import streamlit as st

from modules.session import sidebar_user_context, require_admin

from modules.navigation import run_legacy_page
from modules.operational_quality import repair_all_route_statuses, refresh_fuel_quality, route_state_inconsistencies, route_time_inconsistencies
from modules.traceability import normalize_existing_evidence_paths
from modules.db import DB_PATH

ctx = require_admin()
ctx = sidebar_user_context()
usuario = ctx["usuario"]

st.title("🧾 Auditoría y correcciones")
st.caption("Centro de trazabilidad: auditoría, reparación de estados, calidad de combustible y normalización de evidencias.")

section = st.radio(
    "Sección",
    ["Pendientes y reparación", "Auditoría detallada"],
    horizontal=True,
)

if section == "Auditoría detallada":
    run_legacy_page("14_Auditoria_y_Correcciones.py")
    st.stop()

st.subheader("Reparaciones controladas")
st.write("Estas acciones no borran datos; actualizan estados calculados o normalizan rutas con auditoría.")

c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Recalcular estados de rutas", use_container_width=True):
        n = repair_all_route_statuses(usuario=usuario)
        st.success(f"Estados recalculados para {n} rutas.")
with c2:
    if st.button("Recalcular calidad de combustible", use_container_width=True):
        n = refresh_fuel_quality(usuario=usuario)
        st.success(f"Calidad actualizada en {n} cargas.")
with c3:
    if st.button("Normalizar rutas de evidencias", use_container_width=True):
        n = normalize_existing_evidence_paths(usuario=usuario)
        st.success(f"Rutas de evidencias normalizadas: {n}.")



st.divider()
st.subheader("Respaldo de base de datos")
st.caption("En Streamlit Cloud, SQLite sirve para desarrollo, pero los cambios del archivo local no se guardan de forma confiable después de reinicios/redeploys. Descarga respaldos frecuentes mientras migramos a una base externa.")
try:
    db_bytes = DB_PATH.read_bytes()
    st.download_button(
        "⬇️ Descargar respaldo SQLite actual",
        data=db_bytes,
        file_name="fuel_control_respaldo.db",
        mime="application/octet-stream",
        use_container_width=True,
        key="download_sqlite_backup_v17",
    )
except Exception as exc:
    st.warning(f"No se pudo preparar el respaldo de la base: {exc}")

st.divider()
st.subheader("Inconsistencias detectadas")

incons_hora = route_time_inconsistencies()
if incons_hora.empty:
    st.success("No hay entregas con hora fuera del intervalo de ruta.")
else:
    st.warning("Entregas con hora de llegada fuera del intervalo de ruta.")
    st.dataframe(incons_hora, use_container_width=True, hide_index=True)

incons_estado = route_state_inconsistencies()
if incons_estado.empty:
    st.success("No hay rutas con estado de conciliación incoherente.")
else:
    st.warning("Rutas con estado de conciliación incoherente.")
    st.dataframe(incons_estado, use_container_width=True, hide_index=True)
