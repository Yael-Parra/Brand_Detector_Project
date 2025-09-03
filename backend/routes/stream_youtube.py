from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from ultralytics import YOLO
import cv2
from yt_dlp import YoutubeDL
import threading
import time
from pathlib import Path
import uuid
import os


# Get the directory of the current script
current_dir = Path(__file__).resolve().parent

# Construct the absolute path to the model file
model_path = current_dir / "best_v5.pt"

print(f"Buscando el modelo en: {model_path}")

# Load the model once
try:
    model = YOLO(model_path)
    print("Modelo cargado exitosamente.")
except Exception as e:
    print(f"Error al cargar el modelo: {e}")
    # Consider raising an error here if the model is critical
    model = None 

# Carga el modelo una sola vez, a nivel global en el módulo
model = YOLO(model_path)

router = APIRouter()

def process_and_stream(video_url, job_id, video_name):
    """
    Función que descarga, procesa y transmite el video.
    Esta función se ejecuta en segundo plano.
    """
    ydl_opts = {
        'format': 'best',
        'noplaylist': True,
        'quiet': True,
        'force_generic_extractor': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        url = info['url']
        
    cap = cv2.VideoCapture(url)

    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="No se pudo abrir el stream de YouTube.")

    def generate_frames():
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            results = model(frame)
            annotated_frame = results[0].plot() 
            
            (flag, encodedImage) = cv2.imencode(".jpg", annotated_frame)
            if not flag:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        
        cap.release()

    return generate_frames()

@router.get("/youtube/live/{video_id}")
async def stream_youtube(video_id: str, background_tasks: BackgroundTasks):
    """
    Endpoint que inicia y transmite un video de YouTube en tiempo real con detecciones.
    """
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    
    job_id = str(uuid.uuid4())
    
    frames_generator = process_and_stream(youtube_url, job_id, video_id)

    return StreamingResponse(frames_generator, media_type="multipart/x-mixed-replace; boundary=frame")