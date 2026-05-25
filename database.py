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
                telefono TEXT,
                vencimiento TEXT
            )
        """)

def get_all_clientes():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes')
        return cursor.fetchall()

def get_cliente_por_id(cliente_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
        cliente = cursor.fetchone()
        return dict(cliente) if cliente else None

def cliente_tiene_acceso(cliente_id):
    """
    Devuelve True si el cliente existe y su vencimiento es hoy o futuro.
    Una sola consulta SQL, sin traer nada a memoria.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM clientes
            WHERE id = ?
            AND (vencimiento IS NULL OR vencimiento >= date('now'))
        """, (cliente_id,))
        return cursor.fetchone() is not None

def crear_cliente(nombre, telefono=None, vencimiento=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO clientes (nombre, telefono, vencimiento) VALUES (?, ?, ?)',
            (nombre, telefono, vencimiento)
        )
        return cursor.lastrowid

def actualizar_cliente(cliente_id, nombre=None, telefono=None, vencimiento=None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        campos, valores = [], []

        if nombre is not None:
            campos.append("nombre = ?")
            valores.append(nombre)
        if telefono is not None:
            campos.append("telefono = ?")
            valores.append(telefono)
        if vencimiento is not None:
            campos.append("vencimiento = ?")
            valores.append(vencimiento)

        if campos:
            valores.append(cliente_id)
            cursor.execute(
                f"UPDATE clientes SET {', '.join(campos)} WHERE id = ?",
                valores
            )
            return True
        return False

def eliminar_cliente(cliente_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
        return cursor.rowcount > 0

def obtener_vencimientos_proximos(dias=7):
    """Clientes cuyo vencimiento cae entre hoy y los próximos X días."""
    limite = (datetime.now().date() + timedelta(days=dias)).isoformat()
    hoy = datetime.now().date().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM clientes
            WHERE vencimiento IS NOT NULL
            AND vencimiento BETWEEN ? AND ?
            ORDER BY vencimiento ASC
        """, (hoy, limite))
        return [dict(row) for row in cursor.fetchall()]

def obtener_clientes_vencidos():
    """Clientes cuyo vencimiento ya pasó."""
    hoy = datetime.now().date().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM clientes
            WHERE vencimiento IS NOT NULL
            AND vencimiento < ?
            ORDER BY vencimiento DESC
        """, (hoy,))
        return [dict(row) for row in cursor.fetchall()]
