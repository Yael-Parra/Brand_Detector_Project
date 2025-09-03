import os
import cv2
import yt_dlp
from ultralytics import YOLO
from fastapi.responses import StreamingResponse

# ===============================
# 1. Definir ruta al modelo YOLO
# ===============================

# Ruta absoluta del proyecto (backend/ está dentro de este directorio)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Como el modelo está fuera de backend/, subimos un nivel
MODEL_PATH = os.path.join(PROJECT_ROOT, "..", "best_v5.pt")

# Normalizamos la ruta
MODEL_PATH = os.path.abspath(MODEL_PATH)

# ===============================
# 2. Cargar modelo solo una vez
# ===============================
model = YOLO(MODEL_PATH)


# ===============================
# 3. Obtener stream directo de YouTube
# ===============================
def get_youtube_stream(url: str):
    """Devuelve la URL directa del stream de YouTube usando yt-dlp"""
    ydl_opts = {"format": "best"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info["url"]


# ===============================
# 4. Procesar video frame a frame
# ===============================
def generate_frames(url: str):
    """Genera frames procesados en tiempo real desde un video de YouTube"""
    stream_url = get_youtube_stream(url)
    cap = cv2.VideoCapture(stream_url)

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        # 🔹 Detección con YOLO
        results = model(frame)

        # Dibujar detecciones
        annotated_frame = results[0].plot()

        # Convertir a JPEG
        _, buffer = cv2.imencode(".jpg", annotated_frame)
        frame_bytes = buffer.tobytes()

        # Streaming tipo MJPEG
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

    cap.release()


# ===============================
# 5. Integración con FastAPI
# ===============================
def stream_youtube(url: str):
    """Devuelve un StreamingResponse listo para FastAPI"""
    return StreamingResponse(
        generate_frames(url),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

