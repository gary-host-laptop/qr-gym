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
        clientes = cursor.fetchall()
        return clientes

# --- NUEVAS FUNCIONES PARA EDITAR/CREAR ---

def get_cliente_por_id(cliente_id):
    """Obtiene un cliente por su ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
        cliente = cursor.fetchone()
        return dict(cliente) if cliente else None

def crear_cliente(nombre, telefono=None, vencimiento=None):
    """Crea un nuevo cliente en la base de datos"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO clientes (nombre, telefono, vencimiento) VALUES (?, ?, ?)',
            (nombre, telefono, vencimiento)
        )
        return cursor.lastrowid  # Devuelve el ID del nuevo cliente

def actualizar_cliente(cliente_id, nombre=None, telefono=None, vencimiento=None):
    """Actualiza los datos de un cliente existente"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Construir query dinámica solo con los campos proporcionados
        campos = []
        valores = []
        
        if nombre is not None:
            campos.append("nombre = ?")
            valores.append(nombre)
        if telefono is not None:
            campos.append("telefono = ?")
            valores.append(telefono)
        if vencimiento is not None:
            campos.append("vencimiento = ?")
            valores.append(vencimiento)
        
        if campos:  # Solo actualizar si hay campos para cambiar
            valores.append(cliente_id)
            query = f"UPDATE clientes SET {', '.join(campos)} WHERE id = ?"
            cursor.execute(query, valores)
            return True
        return False

def eliminar_cliente(cliente_id):
    """Elimina un cliente por su ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
        return cursor.rowcount > 0  # True si se eliminó, False si no

def obtener_vencimientos_proximos(dias=7):
    """Obtiene clientes cuyo vencimiento está próximo (en los próximos X días)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes WHERE vencimiento IS NOT NULL')
        todos = cursor.fetchall()
        
        # Filtrar por fecha (esto sería más eficiente en SQL, pero por simplicidad)
        hoy = datetime.now().date()
        limite = hoy + timedelta(days=dias)
        
        proximos = []
        for cliente in todos:
            if cliente['vencimiento']:
                try:
                    fecha_venc = datetime.strptime(cliente['vencimiento'], '%Y-%m-%d').date()
                    if hoy <= fecha_venc <= limite:
                        proximos.append(dict(cliente))
                except ValueError:
                    continue
        return proximos

def obtener_clientes_vencidos():
    """Obtiene clientes cuya fecha de vencimiento ya pasó"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes WHERE vencimiento IS NOT NULL')
        todos = cursor.fetchall()
        
        hoy = datetime.now().date()
        vencidos = []
        for cliente in todos:
            try:
                fecha_venc = datetime.strptime(cliente['vencimiento'], '%Y-%m-%d').date()
                if fecha_venc < hoy:
                    vencidos.append(dict(cliente))
            except ValueError:
                continue
        return vencidos