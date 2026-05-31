import csv
import io
from datetime import datetime
from functools import wraps
from io import BytesIO

import qrcode
from flask import (
    Flask,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from database import (
    actualizar_cliente,
    crear_cliente,
    eliminar_cliente,
    get_all_clientes,
    get_cliente_por_id,
    init_db,
    obtener_historial,
    obtener_vencimientos_proximos,
    registrar_evento,
)

# ========== CONFIGURACIÓN DE LOGIN ==========
USUARIO = "admin"
CONTRASEÑA = "1234"


# ========== DECORADOR PARA PROTEGER RUTAS ==========
def requiere_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logueado" not in session:
            flash("Debes iniciar sesión", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


# --- FUNCIÓN PARA GENERAR QR ---
def generar_qr_descarga(cliente_id, nombre_cliente):
    """Genera un código QR con ID y nombre del cliente"""
    contenido = f"Cliente ID: {cliente_id}\nNombre: {nombre_cliente}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(contenido)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Guardar en memoria (no en disco)
    buffer = BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)

    return buffer


app = Flask(__name__)
app.secret_key = "clave_secreta_para_mensajes_flash_y_sesiones"

with app.app_context():
    init_db()


# ========== RUTAS DE AUTENTICACIÓN ==========


@app.route("/login", methods=["GET", "POST"])
def login():
    """Página de login"""
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contraseña = request.form.get("contraseña")

        if usuario == USUARIO and contraseña == CONTRASEÑA:
            session["logueado"] = True
            registrar_evento(
                tipo="SISTEMA",
                descripcion=f"Inicio de sesión exitoso — usuario: {usuario}",
                resultado="EXITO",
                usuario_admin=usuario,
            )
            flash("¡Bienvenido!", "success")
            return redirect(url_for("listar_clientes_html"))
        else:
            registrar_evento(
                tipo="SISTEMA",
                descripcion=f"Intento de login fallido — usuario: {usuario}",
                resultado="DENEGADO",
                usuario_admin=usuario,
            )
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Cierra la sesión"""
    if "logueado" in session:
        registrar_evento(
            tipo="SISTEMA",
            descripcion="Cierre de sesión",
            resultado="EXITO",
            usuario_admin="admin",
        )
    session.clear()
    flash("Sesión cerrada", "success")
    return redirect(url_for("login"))


# ========== RUTAS PROTEGIDAS ==========


@app.route("/")
@requiere_login
def listar_clientes_html():
    clientes = get_all_clientes()
    clientes_lista = [dict(cliente) for cliente in clientes]

    # Obtener vencimientos próximos
    proximos_vencimientos = obtener_vencimientos_proximos(7)
    ids_proximos = [c["id"] for c in proximos_vencimientos]

    return render_template(
        "clientes.html",
        clientes=clientes_lista,
        ids_proximos=ids_proximos,
        ids_vencidos=[],
    )


@app.route("/editar/<int:cliente_id>", methods=["GET", "POST"])
@requiere_login
def editar_cliente(cliente_id):
    """Edita un cliente existente"""

    if request.method == "GET":
        # Mostrar formulario con datos actuales
        cliente = get_cliente_por_id(cliente_id)
        if not cliente:
            flash("Cliente no encontrado", "error")
            return redirect(url_for("listar_clientes_html"))

        return render_template("editar_cliente.html", cliente=cliente)

    elif request.method == "POST":
        # Procesar formulario de edición
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        telefono = request.form.get("telefono")
        vencimiento = request.form.get("vencimiento")

        # Validar que al menos el nombre esté presente
        if not nombre:
            flash("El nombre es obligatorio", "error")
            return redirect(url_for("editar_cliente", cliente_id=cliente_id))

        # Actualizar en la base de datos
        actualizar_cliente(
            cliente_id=cliente_id,
            nombre=nombre,
            apellido=apellido,
            telefono=telefono,
            vencimiento=vencimiento if vencimiento else None,
        )

        registrar_evento(
            tipo="SISTEMA",
            descripcion=f"Cliente editado — ID {cliente_id}: {nombre}",
            resultado="EXITO",
            cliente_id=cliente_id,
            usuario_admin="admin",
        )
        flash("Cliente actualizado correctamente", "success")
        return redirect(url_for("listar_clientes_html"))


@app.route("/nuevo", methods=["GET", "POST"])
@requiere_login
def nuevo_cliente():
    """Crea un nuevo cliente"""

    if request.method == "GET":
        # Mostrar formulario vacío
        return render_template("nuevo_cliente.html")

    elif request.method == "POST":
        # Procesar formulario de creación
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        telefono = request.form.get("telefono")
        vencimiento = request.form.get("vencimiento")

        # Validaciones básicas
        if not nombre:
            flash("El nombre es obligatorio", "error")
            return redirect(url_for("nuevo_cliente"))

        # Crear en la base de datos
        nuevo_id = crear_cliente(
            nombre=nombre,
            apellido=apellido,
            telefono=telefono,
            vencimiento=vencimiento if vencimiento else None,
        )

        registrar_evento(
            tipo="SISTEMA",
            descripcion=f"Nuevo cliente creado — ID {nuevo_id}: {nombre}",
            resultado="EXITO",
            cliente_id=nuevo_id,
            usuario_admin="admin",
        )
        flash(f"Cliente creado correctamente con ID: {nuevo_id}", "success")
        return redirect(url_for("listar_clientes_html"))


@app.route("/eliminar/<int:cliente_id>", methods=["POST"])
@requiere_login
def eliminar_cliente_route(cliente_id):
    """Elimina un cliente (solo POST para seguridad)"""
    cliente = get_cliente_por_id(cliente_id)
    nombre = cliente["nombre"] if cliente else "desconocido"

    if eliminar_cliente(cliente_id):
        registrar_evento(
            tipo="SISTEMA",
            descripcion=f"Cliente eliminado — ID {cliente_id}: {nombre}",
            resultado="EXITO",
            cliente_id=cliente_id,
            usuario_admin="admin",
        )
        flash("Cliente eliminado correctamente", "success")
    else:
        registrar_evento(
            tipo="SISTEMA",
            descripcion=f"Intento fallido de eliminar cliente ID {cliente_id}",
            resultado="ERROR",
            cliente_id=cliente_id,
            usuario_admin="admin",
        )
        flash("No se pudo eliminar el cliente", "error")

    return redirect(url_for("listar_clientes_html"))


@app.route("/vencimientos")
@requiere_login
def mostrar_vencimientos():
    """Muestra solo los clientes con vencimientos próximos"""
    proximos = obtener_vencimientos_proximos(30)  # Próximos 30 días

    hoy = datetime.now().date()
    for cliente in proximos:
        if cliente["vencimiento"]:
            fecha_venc = datetime.strptime(cliente["vencimiento"], "%Y-%m-%d").date()
            dias_restantes = (fecha_venc - hoy).days
            cliente["dias_restantes"] = dias_restantes

    return render_template("vencimientos.html", clientes=proximos)


@app.route("/descargar_qr/<int:cliente_id>")
@requiere_login
def descargar_qr(cliente_id):
    """Descarga el código QR de un cliente específico"""
    cliente = get_cliente_por_id(cliente_id)
    if not cliente:
        flash("Cliente no encontrado", "error")
        return redirect(url_for("listar_clientes_html"))

    # Generar el QR
    buffer = generar_qr_descarga(cliente_id, cliente["nombre"])

    # Enviar el archivo para descarga
    return send_file(
        buffer,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"cliente_{cliente_id}_{cliente['nombre']}.png",
    )


@app.route("/exportar_csv")
@requiere_login
def exportar_csv():
    """Exporta todos los clientes a CSV"""
    clientes = get_all_clientes()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "nombre", "telefono", "vencimiento"])
    for c in clientes:
        writer.writerow([c["id"], c["nombre"], c["telefono"], c["vencimiento"]])

    response = make_response(buffer.getvalue().encode("utf-8"))
    response.headers["Content-Disposition"] = "attachment; filename=clientes.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response


@app.route("/actividad")
@requiere_login
def mostrar_actividad():
    """Muestra el historial de eventos del sistema"""
    logs = obtener_historial(limite=200)
    return render_template("actividad.html", logs=logs)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
