"""
acceso.py — Punto de entrada del sistema de control de acceso.

Orquesta los módulos:
  - scanner.py    → captura y decodifica códigos QR
  - cerradura.py  → controla la cerradura via Arduino/serial
  - database.py   → consultas a la base de datos gym.db
"""

import re
import time
import cv2

from scanner import ScannerQR
from cerradura import ControlCerradura
from database import get_cliente_por_id, obtener_clientes_vencidos

# ========== CONFIGURACIÓN ==========
SERIAL_PORT = "COM3"
DEBOUNCE_SEGUNDOS = 2   # Tiempo mínimo entre dos escaneos del mismo QR


# ========== LÓGICA DE ACCESO ==========

def extraer_cliente_id(codigo_qr):
    """
    Extrae el ID del cliente del contenido del QR.
    Soporta el formato: 'Cliente ID: 5\\nNombre: Juan'
    También acepta QRs que contengan solo un número.
    Devuelve el ID como entero, o None si no pudo extraerlo.
    """
    match = re.search(r'ID[:\s]*(\d+)', codigo_qr, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Fallback: si el QR es solo un número
    numeros = re.findall(r'\d+', codigo_qr)
    if numeros:
        return int(numeros[0])

    return None


def verificar_acceso(cliente_id):
    """
    Consulta la base de datos y determina si el cliente puede entrar.
    Devuelve (permitido: bool, mensaje: str).
    """
    cliente = get_cliente_por_id(cliente_id)
    if not cliente:
        return False, f"Cliente ID {cliente_id} no encontrado"

    nombre = cliente['nombre']
    vencimiento = cliente.get('vencimiento') or 'Sin fecha'

    vencidos = obtener_clientes_vencidos()
    ids_vencidos = {c['id'] for c in vencidos}

    if cliente_id in ids_vencidos:
        return False, f"ACCESO DENEGADO — {nombre} (vencido: {vencimiento})"

    return True, f"ACCESO PERMITIDO — {nombre} (vence: {vencimiento})"


def procesar_qr(codigo_qr, cerradura):
    """
    Procesa un código QR escaneado:
      1. Extrae el ID del cliente
      2. Verifica si tiene acceso
      3. Abre la cerradura si corresponde
    """
    cliente_id = extraer_cliente_id(codigo_qr)
    if cliente_id is None:
        print("❌ Formato QR inválido")
        return

    permitido, mensaje = verificar_acceso(cliente_id)
    print(f"{'✅' if permitido else '⛔'} {mensaje}")

    if permitido:
        if cerradura.abrir_cerradura():
            print("🔓 Cerradura activada")
        else:
            print("⚠️  No se pudo activar la cerradura")


# ========== BUCLE PRINCIPAL ==========

def main():
    print("=" * 50)
    print("  SISTEMA DE CONTROL DE ACCESO — GIMNASIO")
    print("=" * 50)
    print(f"Puerto serial : {SERIAL_PORT}")
    print("Teclas        : [q] salir  |  [r] reconectar cerradura")
    print("-" * 50)

    scanner = ScannerQR()
    cerradura = ControlCerradura(puerto=SERIAL_PORT)

    if not scanner.iniciar():
        print("❌ No se pudo iniciar la cámara. Saliendo.")
        return

    cerradura.conectar()

    ultimo_codigo = ""
    ultimo_tiempo = 0
    escaneos = 0

    try:
        while True:
            codigo = scanner.escanear()

            # Controlar teclas
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                print("🔄 Reconectando cerradura...")
                cerradura.conectar()

            if codigo:
                ahora = time.time()
                mismo_qr = (codigo == ultimo_codigo)
                dentro_del_debounce = (ahora - ultimo_tiempo < DEBOUNCE_SEGUNDOS)

                if mismo_qr and dentro_del_debounce:
                    continue  # Ignorar lectura duplicada

                ultimo_codigo = codigo
                ultimo_tiempo = ahora
                escaneos += 1

                print(f"\n🎯 Escaneo #{escaneos}")
                procesar_qr(codigo, cerradura)

    except KeyboardInterrupt:
        print("\n⚠️  Interrumpido por el usuario")
    finally:
        scanner.cerrar()
        cerradura.desconectar()
        print("✅ Sistema cerrado correctamente")


if __name__ == "__main__":
    main()
