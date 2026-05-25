"""
acceso.py — Punto de entrada del sistema de control de acceso.

Orquesta los módulos:
  - scanner.py    → captura y decodifica códigos QR
  - cerradura.py  → controla la cerradura via GPIO o serial
  - database.py   → consultas a la base de datos gym.db
"""

import re
import time
import cv2

from scanner import ScannerQR
from cerradura import ControlCerradura
from database import get_cliente_por_id, cliente_tiene_acceso

# ========== CONFIGURACIÓN ==========
SERIAL_PORT = "COM3"
DEBOUNCE_SEGUNDOS = 2


# ========== LÓGICA DE ACCESO ==========

def extraer_cliente_id(codigo_qr):
    """
    Extrae el ID del cliente del contenido del QR.
    Soporta el formato: 'Cliente ID: 5\nNombre: Juan'
    También acepta QRs que contengan solo un número.
    """
    match = re.search(r'ID[:\s]*(\d+)', codigo_qr, re.IGNORECASE)
    if match:
        return int(match.group(1))

    numeros = re.findall(r'\d+', codigo_qr)
    if numeros:
        return int(numeros[0])

    return None


def verificar_acceso(cliente_id):
    """
    Verifica si el cliente puede entrar con una sola consulta SQL.
    Devuelve (permitido: bool, mensaje: str).
    """
    cliente = get_cliente_por_id(cliente_id)
    if not cliente:
        return False, f"Cliente ID {cliente_id} no encontrado"

    nombre = cliente['nombre']
    vencimiento = cliente.get('vencimiento') or 'Sin fecha'

    if not cliente_tiene_acceso(cliente_id):
        return False, f"ACCESO DENEGADO — {nombre} (vencido: {vencimiento})"

    return True, f"ACCESO PERMITIDO — {nombre} (vence: {vencimiento})"


def procesar_qr(codigo_qr, cerradura):
    """
    Procesa un código QR escaneado:
      1. Extrae el ID del cliente
      2. Verifica acceso con una consulta directa a la BD
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

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                print("🔄 Reconectando cerradura...")
                cerradura.conectar()

            if codigo:
                ahora = time.time()
                if codigo == ultimo_codigo and ahora - ultimo_tiempo < DEBOUNCE_SEGUNDOS:
                    continue

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
