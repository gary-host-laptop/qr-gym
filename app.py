import csv
import io
from datetime import datetime
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
    url_for,
)

from database import (
    actualizar_cliente,
    crear_cliente,
    eliminar_cliente,
    get_all_clientes,
    get_cliente_por_id,
    init_db,
    obtener_clientes_vencidos,
    obtener_vencimientos_proximos,
)


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
app.secret_key = "clave_secreta_para_mensajes_flash"  # Necesario para usar flash()

with app.app_context():
    init_db()


@app.route("/")
def listar_clientes_html():
    clientes = get_all_clientes()
    clientes_lista = [dict(cliente) for cliente in clientes]

    # Obtener vencimientos próximos
    proximos_vencimientos = obtener_vencimientos_proximos(7)
    ids_proximos = [c["id"] for c in proximos_vencimientos]

    # Obtener clientes vencidos
    vencidos = obtener_clientes_vencidos()
    ids_vencidos = [c["id"] for c in vencidos]

    return render_template(
        "clientes.html",
        clientes=clientes_lista,
        ids_proximos=ids_proximos,
        ids_vencidos=ids_vencidos,
    )


@app.route("/editar/<int:cliente_id>", methods=["GET", "POST"])
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
            telefono=telefono,
            vencimiento=vencimiento if vencimiento else None,
        )

        flash("Cliente actualizado correctamente", "success")
        return redirect(url_for("listar_clientes_html"))


@app.route("/nuevo", methods=["GET", "POST"])
def nuevo_cliente():
    """Crea un nuevo cliente"""

    if request.method == "GET":
        # Mostrar formulario vacío
        return render_template("nuevo_cliente.html")

    elif request.method == "POST":
        # Procesar formulario de creación
        nombre = request.form.get("nombre")
        telefono = request.form.get("telefono")
        vencimiento = request.form.get("vencimiento")

        # Validaciones básicas
        if not nombre:
            flash("El nombre es obligatorio", "error")
            return redirect(url_for("nuevo_cliente"))

        # Crear en la base de datos
        nuevo_id = crear_cliente(
            nombre=nombre,
            telefono=telefono,
            vencimiento=vencimiento if vencimiento else None,
        )

        flash(f"Cliente creado correctamente con ID: {nuevo_id}", "success")
        return redirect(url_for("listar_clientes_html"))


@app.route("/eliminar/<int:cliente_id>", methods=["POST"])
def eliminar_cliente_route(cliente_id):
    """Elimina un cliente (solo POST para seguridad)"""
    if eliminar_cliente(cliente_id):
        flash("Cliente eliminado correctamente", "success")
    else:
        flash("No se pudo eliminar el cliente", "error")

    return redirect(url_for("listar_clientes_html"))


@app.route("/vencimientos")
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
        as_attachment=True,  # Esto fuerza la descarga
        download_name=f"cliente_{cliente_id}_{cliente['nombre']}.png",
    )


@app.route("/exportar_csv")
def exportar_csv():
    import csv
    import io

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


@app.route("/vencidos")
def mostrar_vencidos():
    """Muestra solo los clientes vencidos"""
    vencidos = obtener_clientes_vencidos()

    hoy = datetime.now().date()
    for cliente in vencidos:
        if cliente["vencimiento"]:
            fecha_venc = datetime.strptime(cliente["vencimiento"], "%Y-%m-%d").date()
            dias_pasados = (hoy - fecha_venc).days
            cliente["dias_pasados"] = dias_pasados

    return render_template("vencidos.html", clientes=vencidos)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
