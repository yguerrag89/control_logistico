from __future__ import annotations

import sqlite3
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "fuel_control.db"
TICKETS_DIR = DATA_DIR / "tickets"
EXPORTS_DIR = DATA_DIR / "exports"
EVIDENCIAS_DIR = DATA_DIR / "evidencias"
GPS_UPLOADS_DIR = DATA_DIR / "gps_uploads"


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCIAS_DIR.mkdir(parents=True, exist_ok=True)
    GPS_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS unidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placas TEXT UNIQUE NOT NULL,
                marca TEXT,
                modelo TEXT,
                color TEXT,
                tipo_unidad TEXT,
                combustible_preferido TEXT,
                tipo_carga TEXT,
                carga_garrafones TEXT,
                periodo_habil TEXT,
                limite_litros REAL,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS checklist_unidad (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unidad_id INTEGER NOT NULL,
                item TEXT NOT NULL,
                valor TEXT,
                FOREIGN KEY (unidad_id) REFERENCES unidades(id)
            );

            CREATE TABLE IF NOT EXISTS conductores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS cargas_combustible (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unidad_id INTEGER NOT NULL,
                conductor_id INTEGER,
                fecha_carga TEXT NOT NULL,
                hora_carga TEXT,
                gasolinera TEXT,
                estacion_direccion TEXT,
                ticket_folio TEXT,
                tipo_combustible TEXT,
                precio_litro REAL NOT NULL,
                litros REAL NOT NULL,
                importe_total REAL NOT NULL,
                kilometraje INTEGER,
                metodo_pago TEXT,
                observaciones TEXT,
                imagen_ticket_path TEXT,
                ocr_texto TEXT,
                origen_registro TEXT DEFAULT 'manual',
                estado_validacion TEXT DEFAULT 'VALIDADO',
                alerta_resumen TEXT,
                tipo_carga_combustible TEXT DEFAULT 'No especificada',
                calidad_registro TEXT,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT,
                FOREIGN KEY (unidad_id) REFERENCES unidades(id),
                FOREIGN KEY (conductor_id) REFERENCES conductores(id)
            );


            CREATE TABLE IF NOT EXISTS destinos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_normalizado TEXT NOT NULL,
                alias TEXT,
                tipo_destino TEXT,
                cliente_asociado TEXT,
                direccion_texto TEXT,
                latitud REAL,
                longitud REAL,
                validado INTEGER NOT NULL DEFAULT 0,
                fuente TEXT DEFAULT 'captura_manual',
                observaciones TEXT,
                excluir_alertas_inactividad INTEGER NOT NULL DEFAULT 0,
                radio_metros REAL DEFAULT 100,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT
            );

            CREATE TABLE IF NOT EXISTS rutas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                unidad_id INTEGER NOT NULL,
                conductor_id INTEGER NOT NULL,
                hora_salida_reportada TEXT,
                hora_regreso_reportada TEXT,
                estado_ruta TEXT NOT NULL DEFAULT 'Abierta',
                observaciones_generales TEXT,
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT,
                FOREIGN KEY (unidad_id) REFERENCES unidades(id),
                FOREIGN KEY (conductor_id) REFERENCES conductores(id)
            );

            CREATE TABLE IF NOT EXISTS ruta_entregas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ruta_id INTEGER NOT NULL,
                cliente_nombre TEXT NOT NULL,
                destino_nombre TEXT NOT NULL,
                destino_id INTEGER,
                hora_llegada_reportada TEXT NOT NULL,
                hora_captura_sistema TEXT DEFAULT CURRENT_TIMESTAMP,
                estatus_entrega TEXT NOT NULL,
                motivo_no_entrega TEXT,
                observaciones TEXT,
                orden_calculado INTEGER,
                estado_conciliacion_gps TEXT NOT NULL DEFAULT 'Pendiente de GPS',
                activo INTEGER NOT NULL DEFAULT 1,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                actualizado_en TEXT,
                FOREIGN KEY (ruta_id) REFERENCES rutas(id)
            );

            CREATE TABLE IF NOT EXISTS ruta_entrega_evidencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entrega_id INTEGER NOT NULL,
                ruta_archivo TEXT NOT NULL,
                tipo_evidencia TEXT,
                comentario TEXT,
                estado_evidencia TEXT DEFAULT 'activo',
                motivo_anulacion TEXT,
                anulado_en TEXT,
                anulado_por TEXT,
                fecha_captura TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entrega_id) REFERENCES ruta_entregas(id)
            );

            CREATE TABLE IF NOT EXISTS gps_importaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                archivo TEXT NOT NULL,
                hoja TEXT NOT NULL,
                unidad_id INTEGER,
                placas TEXT,
                mes INTEGER,
                anio INTEGER,
                tipo_hoja TEXT,
                km_resumen REAL,
                km_calculados REAL,
                diferencia_km REAL,
                tiempo_resumen_seg INTEGER,
                tiempo_calculado_seg INTEGER,
                diferencia_tiempo_seg INTEGER,
                movimientos_detectados INTEGER,
                inmovilizaciones_detectadas INTEGER,
                hash_movimientos TEXT,
                estado_validacion TEXT,
                activo INTEGER NOT NULL DEFAULT 1,
                motivo_anulacion TEXT,
                anulado_en TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unidad_id) REFERENCES unidades(id)
            );

            CREATE TABLE IF NOT EXISTS gps_movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                importacion_id INTEGER NOT NULL,
                unidad_id INTEGER,
                placas TEXT,
                fecha TEXT,
                secuencia INTEGER,
                inicio_datetime TEXT,
                fin_datetime TEXT,
                km REAL,
                duracion_reportada_seg INTEGER,
                duracion_calculada_seg INTEGER,
                diferencia_duracion_seg INTEGER,
                velocidad_promedio_kmh REAL,
                origen TEXT,
                destino TEXT,
                flags_calidad TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (importacion_id) REFERENCES gps_importaciones(id),
                FOREIGN KEY (unidad_id) REFERENCES unidades(id)
            );

            CREATE TABLE IF NOT EXISTS gps_paradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                importacion_id INTEGER NOT NULL,
                movimiento_anterior_id INTEGER,
                unidad_id INTEGER,
                placas TEXT,
                fecha TEXT,
                inicio_gps TEXT,
                fin_gps TEXT,
                duracion_seg INTEGER,
                direccion_gps TEXT,
                latitud REAL,
                longitud REAL,
                clasificacion_inicial TEXT,
                requiere_revision INTEGER DEFAULT 0,
                es_previa_al_primer_movimiento INTEGER DEFAULT 0,
                texto_original TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (importacion_id) REFERENCES gps_importaciones(id),
                FOREIGN KEY (movimiento_anterior_id) REFERENCES gps_movimientos(id),
                FOREIGN KEY (unidad_id) REFERENCES unidades(id)
            );

            CREATE TABLE IF NOT EXISTS entrega_gps_match (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entrega_id INTEGER NOT NULL,
                gps_parada_id INTEGER NOT NULL,
                tipo_match TEXT NOT NULL,
                diferencia_min REAL,
                confianza REAL,
                hora_salida_inferida TEXT,
                tiempo_en_cliente_seg INTEGER,
                validado INTEGER DEFAULT 0,
                validado_por TEXT,
                validado_en TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entrega_id) REFERENCES ruta_entregas(id),
                FOREIGN KEY (gps_parada_id) REFERENCES gps_paradas(id)
            );

            CREATE TABLE IF NOT EXISTS gps_paradas_clasificacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gps_parada_id INTEGER NOT NULL,
                clasificacion TEXT NOT NULL,
                comentario TEXT,
                clasificado_por TEXT,
                clasificado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                activo INTEGER NOT NULL DEFAULT 1,
                motivo_anulacion TEXT,
                anulado_en TEXT,
                anulado_por TEXT,
                FOREIGN KEY (gps_parada_id) REFERENCES gps_paradas(id)
            );

            CREATE TABLE IF NOT EXISTS archivos_adjuntos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla_origen TEXT NOT NULL,
                registro_id INTEGER NOT NULL,
                tipo_archivo TEXT NOT NULL,
                ruta_archivo TEXT NOT NULL,
                estado_archivo TEXT NOT NULL DEFAULT 'activo',
                motivo TEXT,
                comentario TEXT,
                usuario TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                anulado_en TEXT,
                anulado_por TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_rutas_fecha_unidad ON rutas(fecha, unidad_id);
            CREATE INDEX IF NOT EXISTS idx_entregas_ruta ON ruta_entregas(ruta_id);
            CREATE INDEX IF NOT EXISTS idx_gps_mov_unidad_fecha ON gps_movimientos(unidad_id, fecha);
            CREATE INDEX IF NOT EXISTS idx_gps_paradas_unidad_fecha ON gps_paradas(unidad_id, fecha);
            CREATE INDEX IF NOT EXISTS idx_gps_hash ON gps_importaciones(hash_movimientos);

            CREATE TABLE IF NOT EXISTS auditoria_eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla TEXT NOT NULL,
                registro_id INTEGER NOT NULL,
                accion TEXT NOT NULL,
                detalle TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS auditoria_cambios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tabla TEXT NOT NULL,
                registro_id INTEGER NOT NULL,
                campo TEXT,
                valor_anterior TEXT,
                valor_nuevo TEXT,
                accion TEXT NOT NULL,
                motivo TEXT,
                comentario TEXT,
                usuario TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP
            );
            '''
        )
        _migrate_optional_kilometraje(conn)
        _migrate_gps_import_status(conn)
        _migrate_destination_control_fields(conn)
        _migrate_v15_traceability(conn)
        _migrate_v16_operations(conn)


def _migrate_optional_kilometraje(conn: sqlite3.Connection) -> None:
    """Allow cargas_combustible.kilometraje to be NULL in existing SQLite DBs.

    Older MVP versions created this column as NOT NULL. SQLite cannot drop a
    NOT NULL constraint with ALTER COLUMN, so we rebuild only this table when
    needed. Existing records are preserved.
    """
    cols = conn.execute("PRAGMA table_info(cargas_combustible)").fetchall()
    if not cols:
        return
    km_col = next((dict(c) for c in cols if c["name"] == "kilometraje"), None)
    if not km_col or int(km_col.get("notnull", 0)) == 0:
        return

    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.executescript(
        '''
        CREATE TABLE IF NOT EXISTS cargas_combustible_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            unidad_id INTEGER NOT NULL,
            conductor_id INTEGER,
            fecha_carga TEXT NOT NULL,
            hora_carga TEXT,
            gasolinera TEXT,
            estacion_direccion TEXT,
            ticket_folio TEXT,
            tipo_combustible TEXT,
            precio_litro REAL NOT NULL,
            litros REAL NOT NULL,
            importe_total REAL NOT NULL,
            kilometraje INTEGER,
            metodo_pago TEXT,
            observaciones TEXT,
            imagen_ticket_path TEXT,
            ocr_texto TEXT,
            origen_registro TEXT DEFAULT 'manual',
            estado_validacion TEXT DEFAULT 'VALIDADO',
            alerta_resumen TEXT,
            activo INTEGER NOT NULL DEFAULT 1,
            creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TEXT,
            FOREIGN KEY (unidad_id) REFERENCES unidades(id),
            FOREIGN KEY (conductor_id) REFERENCES conductores(id)
        );

        INSERT INTO cargas_combustible_new (
            id, unidad_id, conductor_id, fecha_carga, hora_carga, gasolinera,
            estacion_direccion, ticket_folio, tipo_combustible, precio_litro,
            litros, importe_total, kilometraje, metodo_pago, observaciones,
            imagen_ticket_path, ocr_texto, origen_registro, estado_validacion,
            alerta_resumen, activo, creado_en, actualizado_en
        )
        SELECT
            id, unidad_id, conductor_id, fecha_carga, hora_carga, gasolinera,
            estacion_direccion, ticket_folio, tipo_combustible, precio_litro,
            litros, importe_total, NULLIF(kilometraje, 0), metodo_pago, observaciones,
            imagen_ticket_path, ocr_texto, origen_registro, estado_validacion,
            alerta_resumen, activo, creado_en, actualizado_en
        FROM cargas_combustible;

        DROP TABLE cargas_combustible;
        ALTER TABLE cargas_combustible_new RENAME TO cargas_combustible;
        '''
    )
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.commit()



def _migrate_gps_import_status(conn: sqlite3.Connection) -> None:
    """Add soft-annulment columns to existing GPS import tables."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(gps_importaciones)").fetchall()}
    if "activo" not in cols:
        conn.execute("ALTER TABLE gps_importaciones ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")
    if "motivo_anulacion" not in cols:
        conn.execute("ALTER TABLE gps_importaciones ADD COLUMN motivo_anulacion TEXT")
    if "anulado_en" not in cols:
        conn.execute("ALTER TABLE gps_importaciones ADD COLUMN anulado_en TEXT")
    conn.commit()


def _migrate_destination_control_fields(conn: sqlite3.Connection) -> None:
    """Add destination fields used to filter/control abnormal inactivity alerts."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(destinos)").fetchall()}
    if "excluir_alertas_inactividad" not in cols:
        conn.execute("ALTER TABLE destinos ADD COLUMN excluir_alertas_inactividad INTEGER NOT NULL DEFAULT 0")
    if "radio_metros" not in cols:
        conn.execute("ALTER TABLE destinos ADD COLUMN radio_metros REAL DEFAULT 100")
    conn.commit()


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def _migrate_v15_traceability(conn: sqlite3.Connection) -> None:
    """Additive migrations for v1.5 operational traceability."""
    _add_column_if_missing(conn, "cargas_combustible", "tipo_carga_combustible", "tipo_carga_combustible TEXT DEFAULT 'No especificada'")
    _add_column_if_missing(conn, "cargas_combustible", "calidad_registro", "calidad_registro TEXT")
    _add_column_if_missing(conn, "ruta_entregas", "destino_id", "destino_id INTEGER")
    for col, ddl in [
        ("estado_evidencia", "estado_evidencia TEXT DEFAULT 'activo'"),
        ("motivo_anulacion", "motivo_anulacion TEXT"),
        ("anulado_en", "anulado_en TEXT"),
        ("anulado_por", "anulado_por TEXT"),
    ]:
        _add_column_if_missing(conn, "ruta_entrega_evidencias", col, ddl)
    for col, ddl in [
        ("activo", "activo INTEGER NOT NULL DEFAULT 1"),
        ("motivo_anulacion", "motivo_anulacion TEXT"),
        ("anulado_en", "anulado_en TEXT"),
        ("anulado_por", "anulado_por TEXT"),
    ]:
        _add_column_if_missing(conn, "gps_paradas_clasificacion", col, ddl)
    conn.execute("""CREATE TABLE IF NOT EXISTS archivos_adjuntos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tabla_origen TEXT NOT NULL,
        registro_id INTEGER NOT NULL,
        tipo_archivo TEXT NOT NULL,
        ruta_archivo TEXT NOT NULL,
        estado_archivo TEXT NOT NULL DEFAULT 'activo',
        motivo TEXT,
        comentario TEXT,
        usuario TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        anulado_en TEXT,
        anulado_por TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_archivos_origen ON archivos_adjuntos(tabla_origen, registro_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gps_clasificacion_activa ON gps_paradas_clasificacion(gps_parada_id, activo)")
    conn.commit()


def _migrate_v16_operations(conn: sqlite3.Connection) -> None:
    """Additive migrations for v1.6 operational roles, route closing and cost control."""
    # Destination fields for a stronger catalog.
    for col, ddl in [
        ("cliente_comercial", "cliente_comercial TEXT"),
        ("contacto", "contacto TEXT"),
        ("horario_recepcion", "horario_recepcion TEXT"),
        ("requiere_cita", "requiere_cita INTEGER NOT NULL DEFAULT 0"),
        ("tiempo_promedio_servicio_min", "tiempo_promedio_servicio_min REAL"),
    ]:
        _add_column_if_missing(conn, "destinos", col, ddl)

    conn.execute("""CREATE TABLE IF NOT EXISTS gastos_operativos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        unidad_id INTEGER,
        ruta_id INTEGER,
        tipo_gasto TEXT NOT NULL,
        proveedor TEXT,
        folio TEXT,
        importe REAL NOT NULL,
        metodo_pago TEXT,
        descripcion TEXT,
        estado_validacion TEXT DEFAULT 'PENDIENTE_VALIDACION',
        activo INTEGER NOT NULL DEFAULT 1,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT,
        FOREIGN KEY (unidad_id) REFERENCES unidades(id),
        FOREIGN KEY (ruta_id) REFERENCES rutas(id)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gastos_fecha_unidad ON gastos_operativos(fecha, unidad_id)")
    conn.commit()
