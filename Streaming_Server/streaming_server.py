import time
import cv2
import mss
import numpy as np
from flask import Flask, Response, render_template_string

# --- CONFIGURACIÓN ---
# IP '0.0.0.0' permite que otros en la red se conecten
HOST_IP = '0.0.0.0'
PORT = 5000

# Reducir la resolución mejora el rendimiento en la red
# 1.0 = Tamaño original, 0.5 = Mitad de tamaño
SCALE_FACTOR = 1.0

# Calidad de compresión JPEG (0-100). Menor = Más rápido y menos lag
JPEG_QUALITY = 99

app = Flask(__name__)

# NOTA: Hemos eliminado la instancia global de 'sct' para evitar errores de hilos en Windows.
# La instancia se creará dentro de la función generadora.

def generate_frames():
    """
    Genera el flujo de video capturando la pantalla frame a frame.
    """
    # IMPORTANTE: Inicializamos mss() DENTRO del loop para que sea thread-safe.
    # El 'with' asegura que se cierre correctamente si se desconecta el cliente.
    with mss.mss() as sct:
        # Seleccionamos el monitor principal (el número 1) dentro del contexto
        monitor = sct.monitors[1]
        
        while True:
            start_time = time.time()

            # 1. Capturar la pantalla
            # sct.grab devuelve un objeto raw, lo convertimos a numpy array
            try:
                img_raw = sct.grab(monitor)
            except Exception as e:
                print(f"Error capturando pantalla: {e}")
                break
                
            img_np = np.array(img_raw)

            # 2. Procesamiento de imagen
            # Convertir de BGRA (formato de pantalla) a BGR (formato de OpenCV estándar)
            frame = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

            # 3. Redimensionar para reducir consumo de ancho de banda
            width = int(frame.shape[1] * SCALE_FACTOR)
            height = int(frame.shape[0] * SCALE_FACTOR)
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

            # 4. Codificar a JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)
            
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            # 5. Entregar el frame en formato Multipart (MJPEG Standard)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Control básico de FPS (opcional, descomentar si va demasiado rápido)
            # time.sleep(0.01) 

@app.route('/')
def index():
    """
    Página web simple para ver el stream desde un navegador.
    """
    html_template = """
    <html>
      <head>
        <title>Servidor de Streaming CS:GO</title>
        <style>
          body { background-color: #1a1a1a; color: white; text-align: center; font-family: sans-serif; }
          h1 { margin-top: 20px; }
          img { border: 5px solid #444; max-width: 90%; height: auto; box-shadow: 0 0 20px black; }
        </style>
      </head>
      <body>
        <h1>Transmisión en Vivo: Servidor Python</h1>
        <p>Viendo topología de red - Nodo Streaming</p>
        <!-- La imagen carga la ruta del video -->
        <img src="{{ url_for('video_feed') }}">
      </body>
    </html>
    """
    return render_template_string(html_template)

@app.route('/video_feed')
def video_feed():
    """
    Ruta que utiliza VLC o el navegador para obtener el video.
    """
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print(f"--- Servidor de Streaming Iniciado ---")
    print(f"1. Para ver en navegador: http://localhost:{PORT}")
    print(f"2. Para ver en VLC: Medio > Abrir ubicación de red > http://<TU_IP>:{PORT}/video_feed")
    print(f"--------------------------------------")
    
    # threaded=True es vital para permitir múltiples clientes sin bloquearse
    app.run(host=HOST_IP, port=PORT, threaded=True, debug=False)