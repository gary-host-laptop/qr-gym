import cv2


class ScannerQR:
    def __init__(self, cam_index=0, resolucion=(640, 480), skip_frames=2):
        self.cam_index = cam_index
        self.resolucion = resolucion
        self.skip_frames = skip_frames
        self.cam = None
        self.detector = cv2.QRCodeDetector()
        self.frame_count = 0

    def iniciar(self):
        """Abre la cámara y la configura."""
        self.cam = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
        ancho, alto = self.resolucion
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
        self.cam.set(cv2.CAP_PROP_FPS, 15)

        if not self.cam.isOpened():
            print("❌ No se pudo abrir la cámara")
            return False

        print("📷 Cámara iniciada")
        return True

    def escanear(self):
        """
        Captura un frame y busca un código QR.
        Devuelve el contenido del QR como string, o None si no encontró nada.
        """
        if not self.cam or not self.cam.isOpened():
            return None

        self.frame_count += 1

        # Saltar frames para no sobrecargar la CPU
        if self.frame_count % self.skip_frames != 0:
            self.cam.grab()
            return None

        ret, frame = self.cam.read()
        if not ret:
            return None

        # Procesar en resolución reducida para mayor velocidad
        small = cv2.resize(frame, (320, 240))
        data, vertices, _ = self.detector.detectAndDecode(small)

        if data:
            self._dibujar_deteccion(frame, vertices, data)
            cv2.imshow("Control de Acceso - Escaner QR", frame)
            cv2.waitKey(500)
            return data

        cv2.imshow("Control de Acceso - Escaner QR", frame)
        return None

    def _dibujar_deteccion(self, frame, vertices, data):
        """Dibuja el contorno del QR y un texto en el frame."""
        if vertices is not None:
            # Escalar coordenadas al tamaño original del frame
            scale_x = frame.shape[1] / 320
            scale_y = frame.shape[0] / 240
            pts = (vertices[0] * [scale_x, scale_y]).astype(int)
            for i in range(4):
                cv2.line(frame, tuple(pts[i]), tuple(pts[(i + 1) % 4]), (0, 255, 0), 2)

        cv2.putText(frame, "QR DETECTADO", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, data[:40], (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    def cerrar(self):
        """Libera la cámara y cierra las ventanas."""
        if self.cam and self.cam.isOpened():
            self.cam.release()
        cv2.destroyAllWindows()
        print("📷 Cámara cerrada")
