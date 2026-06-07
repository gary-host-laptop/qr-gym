# 1. agregar al import de database:
#    obtener_datos_inicio

# 2. agregar esta ruta (antes del if __name__ == "__main__":)

@app.route("/inicio")
@requiere_login
def inicio():
    """Página de inicio / dashboard"""
    from datetime import datetime
    datos = obtener_datos_inicio()
    meses_es = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
                'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    hoy = datetime.now()
    dias_es = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
    fecha_hoy = f"{dias_es[hoy.weekday()]} {hoy.day} de {meses_es[hoy.month]} de {hoy.year}"
    return render_template("inicio.html", datos=datos, fecha_hoy=fecha_hoy)

# 3. cambiar el redirect del login para que vaya a inicio en vez de listar_clientes_html:
#    return redirect(url_for("inicio"))
