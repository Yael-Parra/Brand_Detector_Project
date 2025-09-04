import os
from pathlib import Path
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.core.logging import app_logger, get_logger
from backend.core.exceptions import setup_exception_handlers, DatabaseError
from backend.core.middleware import (
    LoggingMiddleware, 
    SecurityHeadersMiddleware, 
    RequestSizeLimitMiddleware,
    EnhancedCORSMiddleware,
    ErrorHandlingMiddleware,
    RateLimitMiddleware
)
from backend.database.db_insertion_data import connect, disconnect, insert_video, insert_detection

# =============================
# Configuración de la aplicación
# =============================
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Crear directorio de uploads
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Upload directory created: {upload_path.absolute()}")
    
    # Verificar conexión a base de datos
    try:
        conn = connect()
        disconnect(conn)
        logger.info("Database connection verified successfully")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise DatabaseError("Failed to connect to database", operation="startup", details={"error": str(e)})
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Configurar manejo de errores
setup_exception_handlers(app)

# Middleware setup (orden importante: de más específico a más general)
app.add_middleware(LoggingMiddleware)  # Primero para loggear todo
app.add_middleware(ErrorHandlingMiddleware)  # Manejo de errores
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)  # Rate limiting
app.add_middleware(SecurityHeadersMiddleware)  # Headers de seguridad
app.add_middleware(RequestSizeLimitMiddleware)  # Límite de tamaño
app.add_middleware(
    EnhancedCORSMiddleware,
    allowed_origins=settings.cors_origins,
    allowed_methods=settings.cors_methods,
    allowed_headers=settings.cors_headers
)

# Carpeta para uploads (usando configuración centralizada)
UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# Persistencia en DB
# =============================
def persist_results(*, vtype: str, name: str, fps: float, total_secs: float, summary: dict):
    """
    Guarda el video o imagen y sus detecciones en la base de datos.
    Si no hay detecciones, inserta un placeholder.
    """
    db_logger = get_logger("database")
    conn = None
    
    try:
        conn = connect()
        db_logger.debug(f"Connected to database for persisting results: {name}")
        
        id_video = insert_video(conn, vtype=vtype, name=name, total_secs=total_secs)
        db_logger.info(f"Video inserted with ID: {id_video}")
        
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
                db_logger.debug(f"Detection inserted: {label} - {info.get('frames', 0)} frames")
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
            db_logger.info("No detections found, inserted placeholder")
        
        if hasattr(conn, "commit"):
            conn.commit()
            
        db_logger.info(
            f"Results persisted successfully",
            extra={
                "video_id": id_video,
                "type": vtype,
                "name": name,
                "total_seconds": round(total_secs, 3),
                "fps": round(fps, 2),
                "detections_inserted": inserted
            }
        )
        return id_video
        
    except Exception as e:
        db_logger.error(
            f"Failed to persist results for {name}",
            extra={
                "error": str(e),
                "type": vtype,
                "name": name,
                "total_seconds": total_secs,
                "fps": fps
            }
        )
        
        if conn:
            try:
                if hasattr(conn, "rollback"):
                    conn.rollback()
                    db_logger.debug("Database transaction rolled back")
            except Exception as rollback_error:
                db_logger.error(f"Failed to rollback transaction: {rollback_error}")
        
        raise DatabaseError(
            f"Failed to persist results for {name}",
            operation="persist_results",
            details={"original_error": str(e), "file_name": name, "file_type": vtype}
        )
        
    finally:
        if conn:
            try:
                disconnect(conn)
                db_logger.debug("Database connection closed")
            except Exception as disconnect_error:
                db_logger.error(f"Failed to close database connection: {disconnect_error}")

# =============================
# Endpoint base
# =============================
@app.get("/")
def health():
    """Endpoint de salud de la aplicación"""
    api_logger = get_logger("api")
    api_logger.debug("Health check requested")
    
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }

# =============================
# Routers separados
# =============================
from .routes.youtube_video import router as youtube_router
from .routes.upload_image import router as upload_image_router
from .routes.upload_videos import router as upload_videos_router
from .routes.health import router as health_router

# Incluir routers
app.include_router(health_router, prefix="", tags=["Health"])  # Health checks
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
