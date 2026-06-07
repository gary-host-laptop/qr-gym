import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_NAME = "gym.db"


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellido TEXT,
                telefono TEXT,
                vencimiento TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                resultado TEXT NOT NULL,
                cliente_id INTEGER,
                usuario_admin TEXT
            )
        """)


def registrar_evento(tipo, descripcion, resultado, cliente_id=None, usuario_admin=None):
    """Registra un evento en la tabla logs. Transacción atómica e independiente."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        fecha = datetime.now().isoformat(sep=" ", timespec="seconds")
        cursor.execute(
            """INSERT INTO logs
               (fecha, tipo, descripcion, resultado, cliente_id, usuario_admin)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (fecha, tipo, descripcion, resultado, cliente_id, usuario_admin),
        )
        return cursor.lastrowid


def obtener_historial(limite=100):
    """Devuelve los últimos N eventos ordenados por fecha descendente."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs ORDER BY fecha DESC LIMIT ?", (limite,))
        return [dict(row) for row in cursor.fetchall()]


def get_all_clientes():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes")
        return cursor.fetchall()


def get_cliente_por_id(cliente_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
        cliente = cursor.fetchone()
        return dict(cliente) if cliente else None


def cliente_tiene_acceso(cliente_id):
    """
    Devuelve True si el cliente existe y su vencimiento es hoy o futuro.
    Una sola consulta SQL, sin traer nada a memoria.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id FROM clientes
            WHERE id = ?
            AND (vencimiento IS NULL OR vencimiento >= date('now'))
        """,
            (cliente_id,),
        )
        return cursor.fetchone() is not None


def crear_cliente(nombre, apellido=None, telefono=None, vencimiento=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO clientes (nombre, apellido, telefono, vencimiento) VALUES (?, ?, ?, ?)",
            (nombre, apellido, telefono, vencimiento),
        )
        return cursor.lastrowid


def actualizar_cliente(
    cliente_id, nombre=None, apellido=None, telefono=None, vencimiento=None
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        campos, valores = [], []
        if nombre is not None:
            campos.append("nombre = ?")
            valores.append(nombre)
        if apellido is not None:
            campos.append("apellido = ?")
            valores.append(apellido)
        if telefono is not None:
            campos.append("telefono = ?")
            valores.append(telefono)
        if vencimiento is not None:
            campos.append("vencimiento = ?")
            valores.append(vencimiento)
        if campos:
            valores.append(cliente_id)
            cursor.execute(
                f"UPDATE clientes SET {', '.join(campos)} WHERE id = ?", valores
            )
            return True
        return False


def eliminar_cliente(cliente_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        return cursor.rowcount > 0


def obtener_vencimientos_proximos(dias=7):
    """Clientes cuyo vencimiento cae entre hoy y los próximos X días."""
    limite = (datetime.now().date() + timedelta(days=dias)).isoformat()
    hoy = datetime.now().date().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM clientes
            WHERE vencimiento IS NOT NULL
            AND vencimiento BETWEEN ? AND ?
            ORDER BY vencimiento ASC
        """,
            (hoy, limite),
        )
        return [dict(row) for row in cursor.fetchall()]


def obtener_clientes_vencidos():
    """Clientes cuyo vencimiento ya pasó."""
    hoy = datetime.now().date().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM clientes
            WHERE vencimiento IS NOT NULL
            AND vencimiento < ?
            ORDER BY vencimiento DESC
        """,
            (hoy,),
        )
        return [dict(row) for row in cursor.fetchall()]


def obtener_estadisticas():
    """Devuelve datos agregados para la página de estadísticas."""
    from datetime import datetime, timedelta

    hoy = datetime.now().date()
    mes_inicio = hoy.replace(day=1).isoformat()
    hoy_iso = hoy.isoformat()

    with get_db_connection() as conn:
        cur = conn.cursor()

        # totales simples
        total_clientes = cur.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]

        accesos_hoy = cur.execute(
            """
            SELECT COUNT(*) FROM logs
            WHERE tipo='ACCESO' AND resultado='EXITO'
            AND fecha >= ? || ' 00:00:00'
        """,
            (hoy_iso,),
        ).fetchone()[0]

        accesos_mes = cur.execute(
            """
            SELECT COUNT(*) FROM logs
            WHERE tipo='ACCESO' AND resultado='EXITO'
            AND fecha >= ? || ' 00:00:00'
        """,
            (mes_inicio,),
        ).fetchone()[0]

        denegados_mes = cur.execute(
            """
            SELECT COUNT(*) FROM logs
            WHERE tipo='ACCESO' AND resultado='DENEGADO'
            AND fecha >= ? || ' 00:00:00'
        """,
            (mes_inicio,),
        ).fetchone()[0]

        clientes_vencidos = cur.execute(
            """
            SELECT COUNT(*) FROM clientes
            WHERE vencimiento IS NOT NULL AND vencimiento < ?
        """,
            (hoy_iso,),
        ).fetchone()[0]

        # hora pico histórica
        hora_pico_row = cur.execute("""
            SELECT substr(fecha, 12, 2) as hora, COUNT(*) as cnt
            FROM logs WHERE tipo='ACCESO' AND resultado='EXITO'
            GROUP BY hora ORDER BY cnt DESC LIMIT 1
        """).fetchone()
        hora_pico = (hora_pico_row[0] + ":00") if hora_pico_row else "--"

        # accesos por día de semana (0=lun ... 6=dom)
        dias_rows = cur.execute("""
            SELECT strftime('%w', fecha) as dow, COUNT(*) as cnt
            FROM logs WHERE tipo='ACCESO' AND resultado='EXITO'
            GROUP BY dow
        """).fetchall()
        dias_map = {r[0]: r[1] for r in dias_rows}
        # SQLite: 0=domingo, reordenamos a lun-dom
        dias_semana_labels = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
        dias_semana_data = [dias_map.get(str(i), 0) for i in range(7)]

        # accesos por hora
        horas_rows = cur.execute("""
            SELECT substr(fecha, 12, 2) as hora, COUNT(*) as cnt
            FROM logs WHERE tipo='ACCESO' AND resultado='EXITO'
            GROUP BY hora ORDER BY hora
        """).fetchall()
        horas_labels = [r[0] + ":00" for r in horas_rows]
        horas_data = [r[1] for r in horas_rows]

        # top 10 clientes por accesos este mes
        top_rows = cur.execute(
            """
            SELECT c.nombre || ' ' || COALESCE(c.apellido, '') as nombre, COUNT(*) as cnt
            FROM logs l JOIN clientes c ON l.cliente_id = c.id
            WHERE l.tipo='ACCESO' AND l.resultado='EXITO'
            AND l.fecha >= ? || ' 00:00:00'
            GROUP BY l.cliente_id ORDER BY cnt DESC LIMIT 10
        """,
            (mes_inicio,),
        ).fetchall()
        top_clientes_nombres = [r[0].strip() for r in top_rows]
        top_clientes_counts = [r[1] for r in top_rows]

        # resultados torta
        res_rows = cur.execute(
            """
            SELECT resultado, COUNT(*) FROM logs
            WHERE tipo='ACCESO'
            AND fecha >= ? || ' 00:00:00'
            GROUP BY resultado
        """,
            (mes_inicio,),
        ).fetchall()
        resultados_labels = [r[0] for r in res_rows]
        resultados_data = [r[1] for r in res_rows]

        # línea últimos 14 días
        linea = []
        for i in range(13, -1, -1):
            dia = (hoy - timedelta(days=i)).isoformat()
            cnt = cur.execute(
                """
                SELECT COUNT(*) FROM logs
                WHERE tipo='ACCESO' AND resultado='EXITO'
                AND fecha >= ? || ' 00:00:00' AND fecha < ? || ' 23:59:59'
            """,
                (dia, dia),
            ).fetchone()[0]
            linea.append((dia[5:], cnt))  # MM-DD
        linea_labels = [l[0] for l in linea]
        linea_data = [l[1] for l in linea]

    import calendar

    meses_es = [
        "",
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]

    return {
        "stats": {
            "total_clientes": total_clientes,
            "accesos_hoy": accesos_hoy,
            "accesos_mes": accesos_mes,
            "denegados_mes": denegados_mes,
            "clientes_vencidos": clientes_vencidos,
            "hora_pico": hora_pico,
            "fecha_hoy": hoy.strftime("%d/%m/%Y"),
            "mes_actual": meses_es[hoy.month],
        },
        "datos": {
            "dias_semana_labels": dias_semana_labels,
            "dias_semana_data": dias_semana_data,
            "horas_labels": horas_labels,
            "horas_data": horas_data,
            "top_clientes_nombres": top_clientes_nombres,
            "top_clientes_counts": top_clientes_counts,
            "resultados_labels": resultados_labels,
            "resultados_data": resultados_data,
            "linea_labels": linea_labels,
            "linea_data": linea_data,
        },
    }


def obtener_datos_inicio():
    """Datos resumidos para la página de inicio."""
    hoy = datetime.now().date().isoformat()
    mes_inicio = datetime.now().date().replace(day=1).isoformat()
    with get_db_connection() as conn:
        cur = conn.cursor()
        total_clientes = cur.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
        accesos_hoy = cur.execute("""
            SELECT COUNT(*) FROM logs
            WHERE tipo='ACCESO' AND resultado='EXITO'
            AND fecha >= ? || ' 00:00:00'
        """, (hoy,)).fetchone()[0]
        denegados_hoy = cur.execute("""
            SELECT COUNT(*) FROM logs
            WHERE tipo='ACCESO' AND resultado='DENEGADO'
            AND fecha >= ? || ' 00:00:00'
        """, (hoy,)).fetchone()[0]
        vencimientos_proximos = cur.execute("""
            SELECT COUNT(*) FROM clientes
            WHERE vencimiento IS NOT NULL
            AND vencimiento BETWEEN ? AND date(?, '+30 days')
        """, (hoy, hoy)).fetchone()[0]
        clientes_vencidos = cur.execute("""
            SELECT COUNT(*) FROM clientes
            WHERE vencimiento IS NOT NULL AND vencimiento < ?
        """, (hoy,)).fetchone()[0]
    return {
        "total_clientes": total_clientes,
        "accesos_hoy": accesos_hoy,
        "denegados_hoy": denegados_hoy,
        "vencimientos_proximos": vencimientos_proximos,
        "clientes_vencidos": clientes_vencidos,
    }
