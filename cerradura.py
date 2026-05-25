# 0.3/core/cerradura.py
import time
try:
    import serial
    import serial.tools.list_ports
    SERIAL_DISPONIBLE = True
except ImportError:
    SERIAL_DISPONIBLE = False
    print("⚠️  PySerial no está instalado. Usando modo simulación.")

class ControlCerradura:
    def __init__(self, puerto=None, baudios=9600, modo_simulacion=False):
        self.puerto = puerto
        self.baudios = baudios
        self.conexion = None
        self.modo_simulacion = modo_simulacion
        
    def detectar_puertos(self):
        """Detecta puertos seriales disponibles"""
        if self.modo_simulacion or not SERIAL_DISPONIBLE:
            print("🔍 Modo simulación: simulando puertos COM3 y COM4")
            return [
                {'dispositivo': 'COM3', 'descripcion': 'Arduino Uno (Simulado)', 'hwid': 'SIMULADO'},
                {'dispositivo': 'COM4', 'descripcion': 'Arduino Mega (Simulado)', 'hwid': 'SIMULADO'}
            ]
        else:
            puertos = []
            for puerto in serial.tools.list_ports.comports():
                puertos.append({
                    'dispositivo': puerto.device,
                    'descripcion': puerto.description,
                    'hwid': puerto.hwid
                })
            return puertos
    
    def conectar(self, puerto=None):
        """Establece conexión con Arduino (o simula)"""
        if self.modo_simulacion or not SERIAL_DISPONIBLE:
            print(f"🔗 [SIM] Conectado a {puerto or self.puerto} a {self.baudios} baudios")
            self.conexion = True
            return True
        
        try:
            if puerto:
                self.puerto = puerto
            
            if not self.puerto:
                print("⚠️ No se especificó puerto")
                return False
                
            self.conexion = serial.Serial(
                port=self.puerto,
                baudrate=self.baudios,
                timeout=2
            )
            time.sleep(2)  # Esperar inicialización
            print(f"✅ Conectado a {self.puerto} a {self.baudios} baudios")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando: {e}")
            return False
    
    def abrir_cerradura(self, tiempo_segundos=3):
        """Envía comando para abrir cerradura"""
        if self.modo_simulacion or not SERIAL_DISPONIBLE:
            print(f"🔓 [SIM] Enviado comando 'A' a Arduino (abrir por {tiempo_segundos}s)")
            print(f"⏳ [SIM] Esperando {tiempo_segundos} segundos...")
            time.sleep(tiempo_segundos)
            print("✅ [SIM] Cerradura abierta y cerrada automáticamente")
            return True
        
        if not self.conexion or not self.conexion.is_open:
            if not self.conectar():
                return False
        
        try:
            # Comando: 'A' para abrir
            self.conexion.write(b'A')
            print(f"🔓 Enviado comando ABRIR a Arduino")
            
            # Leer respuesta (opcional)
            time.sleep(0.5)
            if self.conexion.in_waiting:
                respuesta = self.conexion.readline().decode().strip()
                print(f"📥 Arduino responde: {respuesta}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error enviando comando: {e}")
            return False
    
    def cerrar_cerradura(self):
        """Envía comando para cerrar cerradura (si aplica)"""
        if self.modo_simulacion or not SERIAL_DISPONIBLE:
            print("🔒 [SIM] Enviado comando 'C' a Arduino (cerrar)")
            return True
        
        if not self.conexion or not self.conexion.is_open:
            return False
        
        try:
            self.conexion.write(b'C')
            print("🔒 Enviado comando CERRAR a Arduino")
            return True
        except:
            return False
    
    def probar_conexion(self):
        """Prueba la conexión enviando un ping"""
        if self.modo_simulacion or not SERIAL_DISPONIBLE:
            print("📡 [SIM] Enviado ping 'P' a Arduino")
            print("📡 [SIM] Arduino responde: OK")
            return True
        
        if not self.conexion or not self.conexion.is_open:
            return False
        
        try:
            self.conexion.write(b'P')
            time.sleep(0.5)
            if self.conexion.in_waiting:
                respuesta = self.conexion.readline().decode().strip()
                return respuesta == "OK"
        except:
            return False
    
    def desconectar(self):
        """Cierra la conexión serial"""
        if self.modo_simulacion or not SERIAL_DISPONIBLE:
            print("🔌 [SIM] Conexión serial cerrada")
            return
        
        if self.conexion and self.conexion.is_open:
            self.conexion.close()
            print("🔌 Conexión serial cerrada")

# Función simple de conveniencia
def abrir_cerradura_simple(puerto="COM3", modo_simulacion=True):
    """
    Función simple para abrir cerradura
    Uso: from core.cerradura import abrir_cerradura_simple
    abrir_cerradura_simple("COM3")
    """
    cerradura = ControlCerradura(puerto, modo_simulacion=modo_simulacion)
    if cerradura.conectar():
        exito = cerradura.abrir_cerradura()
        cerradura.desconectar()
        return exito
    return False

# Para probar directamente
if __name__ == "__main__":
    # Detectar puertos
    cerradura = ControlCerradura(modo_simulacion=True)
    puertos = cerradura.detectar_puertos()
    
    if puertos:
        print("🔍 Puertos detectados:")
        for p in puertos:
            print(f"  - {p['dispositivo']}: {p['descripcion']}")
        
        # Usar primer puerto detectado
        puerto = puertos[0]['dispositivo']
        print(f"\n🔗 Intentando conectar a {puerto}...")
        
        if cerradura.conectar(puerto):
            # Probar conexión
            if cerradura.probar_conexion():
                print("✅ Arduino respondió correctamente")
                # Abrir cerradura por 3 segundos
                cerradura.abrir_cerradura(3)
                time.sleep(3)
            else:
                print("⚠️ Arduino no responde, pero intentando abrir...")
                cerradura.abrir_cerradura(3)
            
            cerradura.desconectar()
    else:
        print("❌ No se detectaron puertos seriales")