import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv

from .database.db_io import connect, disconnect, insert_video, insert_detection
from .services.yolo_service import analyze_mp4, analyze_stream_url, analyze_webcam

load_dotenv()

app = FastAPI(title="Brand Logo Detector API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta para subidas
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def persist_results(
    *,
    vtype: str,
    name: str,
    fps: float,
    total_secs: float,
    summary: dict
):
    """
    Crea fila en videos e inserta el conjunto de detecciones.
    """
    conn = connect()
    try:
        id_video = insert_video(conn, vtype=vtype, name=name, total_secs=total_secs)
        for label, info in summary.items():
            insert_detection(
                conn,
                id_video=id_video,
                label_name=label,
                qty_frames_detected=int(info["frames"]),
                fps=fps,
                percent=float(info["percentage"]),
            )
        return id_video
    finally:
        disconnect(conn)

# ---------- Rutas ----------

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict/mp4")
def predict_mp4(file: UploadFile = File(...)):
    """
    Sube un MP4, corre YOLO frame a frame y guarda resultados.
    """
    if not file.filename.lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Se espera un archivo .mp4")

    dest = UPLOAD_DIR / file.filename
    dest.write_bytes(file.file.read())

    try:
        fps, total_secs, summary = analyze_mp4(str(dest))
    except Exception as e:
        # Limpieza básica
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

    id_video = persist_results(
        vtype="mp4",
        name=file.filename,
        fps=fps,
        total_secs=total_secs,
        summary=summary,
    )

    return JSONResponse(
        {
            "id_video": id_video,
            "type": "mp4",
            "name": file.filename,
            "fps": fps,
            "total_video_time_segs": total_secs,
            "detections": summary,
        }
    )

@app.post("/predict/url")
def predict_url(
    url: str = Form(..., description="YouTube/RTSP/HTTP de video"),
    duration_sec: int = Form(15, ge=3, le=120)
):
    """
    Procesa un stream por URL durante 'duration_sec' segundos y guarda resultados.
    """
    try:
        fps, elapsed, summary = analyze_stream_url(url, duration_sec=duration_sec)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    id_video = persist_results(
        vtype="url",
        name=url,
        fps=fps,
        total_secs=elapsed,
        summary=summary,
    )

    return {
        "id_video": id_video,
        "type": "url",
        "name": url,
        "fps_estimated": fps,
        "processed_secs": elapsed,
        "detections": summary,
    }

@app.post("/predict/streaming")
def predict_streaming(
    duration_sec: int = Form(10, ge=3, le=120),
    camera_index: int = Form(0)
):
    """
    Toma frames de la webcam 'camera_index' por 'duration_sec' segundos y guarda resultados.
    """
    try:
        fps, elapsed, summary = analyze_webcam(camera_index=camera_index, duration_sec=duration_sec)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    name = f"camera_{camera_index}"
    id_video = persist_results(
        vtype="streaming",
        name=name,
        fps=fps,
        total_secs=elapsed,
        summary=summary,
    )

    return {
        "id_video": id_video,
        "type": "streaming",
        "name": name,
        "fps_estimated": fps,
        "processed_secs": elapsed,
        "detections": summary,
    }
