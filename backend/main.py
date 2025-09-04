import os
from pathlib import Path
import base64
import uuid
import time
from typing import Optional, Dict, Any

import numpy as np
import cv2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware

from .database.db_insertion_data import connect, disconnect, insert_video, insert_detection

# =============================
# Constantes y utilidades
# =============================
load_dotenv()

# Inicializa la aplicación FastAPI una sola vez.
app = FastAPI(title="Brand Logo Detector API", version="1.0.0")

# Configurar CORS para el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),  # Permite todos los dominios si no hay .env
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta para uploads
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# Persistencia en DB
# =============================
def persist_results(*, vtype: str, name: str, fps: float, total_secs: float, summary: dict):
    """
    Guarda el video o imagen y sus detecciones en la base de datos.
    Si no hay detecciones, inserta un placeholder.
    """
    from database.db_io import connect, disconnect, insert_video, insert_detection
    
    conn = connect()
    try:
        id_video = insert_video(conn, vtype=vtype, name=name, total_secs=total_secs)
        inserted = 0
        if summary:
            for label, info in summary.items():
                insert_detection(
                    conn,
                    id_video=id_video,
                    label_name=label,
                    qty_frames_detected=int(info.get("frames", 0)),
                    fps=fps,
                    percent=float(info.get("percentage", 0.0)),
                )
                inserted += 1
        else:
            # Insert placeholder si no hay detecciones
            insert_detection(
                conn,
                id_video=id_video,
                label_name="(ninguno)",
                qty_frames_detected=0,
                fps=fps,
                percent=0.0,
            )
            inserted = 1
        if hasattr(conn, "commit"):
            conn.commit()
        print(f"[persist] OK video={id_video} type={vtype} name={name} total_secs={total_secs:.3f} fps={fps:.2f} rows={inserted}")
        return id_video
    except Exception as e:
        try:
            if hasattr(conn, "rollback"):
                conn.rollback()
        except Exception:
            pass
        print(f"[persist] ERROR: {e}")
        raise
    finally:
        disconnect(conn)

# =============================
# Endpoint base
# =============================
@app.get("/")
def health():
    return {"status": "ok"}

# Endpoint directo para status para asegurar que siempre esté disponible
@app.get("/status/{job_id}")
async def get_status_endpoint(job_id: str):
    # Importar aquí para evitar problemas de importación circular
    from .routes.upload_videos import get_job_status
    return await get_job_status(job_id)

# =============================
# Routers separados
# =============================
from .routes.youtube_video import router as youtube_router
from .routes.upload_image import router as upload_image_router
from .routes.upload_videos import router as upload_videos_router

# Incluir routers sin colisiones
app.include_router(upload_image_router, prefix="")      # Imagenes
app.include_router(upload_videos_router, prefix="")     # Videos locales
app.include_router(youtube_router, prefix="")           # Videos de YouTube

# =============================
# Endpoints de status separados
# =============================

# Status genérico para uploads (imagen o video local)
@app.get("/status/{job_id}")
async def get_upload_status(job_id: str):
    """
    Proxy para redirigir a la función de estado de upload_videos.
    Esto solo aplica a videos subidos.
    """
    from .routes.upload_videos import get_job_status
    return await get_job_status(job_id)

# Status específico para jobs de YouTube
@app.get("/status/youtube/{job_id}")
async def get_youtube_status(job_id: str):
    """
    Proxy para redirigir a la función de estado de youtube_video.
    Esto solo aplica a jobs de YouTube.
    """
    from .routes.youtube_video import get_job_status
    return get_job_status(job_id)
