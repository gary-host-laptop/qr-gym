from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import qrcode
from io import BytesIO
from database import (
    get_all_clientes, 
    get_cliente_por_id, 
    crear_cliente, 
    actualizar_cliente,
    eliminar_cliente,
    obtener_vencimientos_proximos,
    obtener_clientes_vencidos
)
from datetime import datetime

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
app.secret_key = 'clave_secreta_para_mensajes_flash'  # Necesario para usar flash()

@app.route('/')
def listar_clientes_html():
    clientes = get_all_clientes()
    clientes_lista = [dict(cliente) for cliente in clientes]
    
    # Obtener vencimientos próximos
    proximos_vencimientos = obtener_vencimientos_proximos(7)
    ids_proximos = [c['id'] for c in proximos_vencimientos]
    
    # Obtener clientes vencidos
    vencidos = obtener_clientes_vencidos()
    ids_vencidos = [c['id'] for c in vencidos]
    
    return render_template('clientes.html', 
                         clientes=clientes_lista,
                         ids_proximos=ids_proximos,
                         ids_vencidos=ids_vencidos)

@app.route('/editar/<int:cliente_id>', methods=['GET', 'POST'])
def editar_cliente(cliente_id):
    """Edita un cliente existente"""
    
    if request.method == 'GET':
        # Mostrar formulario con datos actuales
        cliente = get_cliente_por_id(cliente_id)
        if not cliente:
            flash('Cliente no encontrado', 'error')
            return redirect(url_for('listar_clientes_html'))
        
        return render_template('editar_cliente.html', cliente=cliente)
    
    elif request.method == 'POST':
        # Procesar formulario de edición
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        vencimiento = request.form.get('vencimiento')
        
        # Validar que al menos el nombre esté presente
        if not nombre:
            flash('El nombre es obligatorio', 'error')
            return redirect(url_for('editar_cliente', cliente_id=cliente_id))
        
        # Actualizar en la base de datos
        actualizar_cliente(
            cliente_id=cliente_id,
            nombre=nombre,
            telefono=telefono,
            vencimiento=vencimiento if vencimiento else None
        )
        
        flash('Cliente actualizado correctamente', 'success')
        return redirect(url_for('listar_clientes_html'))

@app.route('/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    """Crea un nuevo cliente"""
    
    if request.method == 'GET':
        # Mostrar formulario vacío
        return render_template('nuevo_cliente.html')
    
    elif request.method == 'POST':
        # Procesar formulario de creación
        nombre = request.form.get('nombre')
        telefono = request.form.get('telefono')
        vencimiento = request.form.get('vencimiento')
        
        # Validaciones básicas
        if not nombre:
            flash('El nombre es obligatorio', 'error')
            return redirect(url_for('nuevo_cliente'))
        
        # Crear en la base de datos
        nuevo_id = crear_cliente(
            nombre=nombre,
            telefono=telefono,
            vencimiento=vencimiento if vencimiento else None
        )
        
        flash(f'Cliente creado correctamente con ID: {nuevo_id}', 'success')
        return redirect(url_for('listar_clientes_html'))

@app.route('/eliminar/<int:cliente_id>', methods=['POST'])
def eliminar_cliente_route(cliente_id):
    """Elimina un cliente (solo POST para seguridad)"""
    if eliminar_cliente(cliente_id):
        flash('Cliente eliminado correctamente', 'success')
    else:
        flash('No se pudo eliminar el cliente', 'error')
    
    return redirect(url_for('listar_clientes_html'))

@app.route('/vencimientos')
def mostrar_vencimientos():
    """Muestra solo los clientes con vencimientos próximos"""
    proximos = obtener_vencimientos_proximos(30)  # Próximos 30 días
    
    hoy = datetime.now().date()
    for cliente in proximos:
        if cliente['vencimiento']:
            fecha_venc = datetime.strptime(cliente['vencimiento'], '%Y-%m-%d').date()
            dias_restantes = (fecha_venc - hoy).days
            cliente['dias_restantes'] = dias_restantes
    
    return render_template('vencimientos.html', clientes=proximos)

@app.route('/descargar_qr/<int:cliente_id>')
def descargar_qr(cliente_id):
    """Descarga el código QR de un cliente específico"""
    cliente = get_cliente_por_id(cliente_id)
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('listar_clientes_html'))
    
    # Generar el QR
    buffer = generar_qr_descarga(cliente_id, cliente['nombre'])
    
    # Enviar el archivo para descarga
    return send_file(
        buffer,
        mimetype='image/png',
        as_attachment=True,  # Esto fuerza la descarga
        download_name=f'cliente_{cliente_id}_{cliente["nombre"]}.png'
    )
# Ruta para actualizar solo la fecha de vencimiento (más simple)
@app.route('/actualizar_vencimiento/<int:cliente_id>', methods=['GET', 'POST'])
def actualizar_vencimiento(cliente_id):
    """Actualiza solo la fecha de vencimiento de un cliente"""
    
    cliente = get_cliente_por_id(cliente_id)
    if not cliente:
        flash('Cliente no encontrado', 'error')
        return redirect(url_for('listar_clientes_html'))
    
    if request.method == 'GET':
        return render_template('actualizar_vencimiento.html', cliente=cliente)
    
    elif request.method == 'POST':
        nueva_fecha = request.form.get('vencimiento')
        
        if actualizar_cliente(cliente_id, vencimiento=nueva_fecha if nueva_fecha else None):
            flash('Fecha de vencimiento actualizada', 'success')
        else:
            flash('Error al actualizar la fecha', 'error')
        
        return redirect(url_for('listar_clientes_html'))

@app.route('/vencidos')
def mostrar_vencidos():
    """Muestra solo los clientes vencidos"""
    vencidos = obtener_clientes_vencidos()
    
    hoy = datetime.now().date()
    for cliente in vencidos:
        if cliente['vencimiento']:
            fecha_venc = datetime.strptime(cliente['vencimiento'], '%Y-%m-%d').date()
            dias_pasados = (hoy - fecha_venc).days
            cliente['dias_pasados'] = dias_pasados
    
    return render_template('vencidos.html', clientes=vencidos)

if __name__ == '__main__':
    app.run(debug=True)