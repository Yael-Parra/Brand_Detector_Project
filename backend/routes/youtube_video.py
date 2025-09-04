# =======================================================
# Endpoint para procesar YouTube desde frontend o Swagger
# =======================================================

from fastapi import APIRouter, BackgroundTasks
import subprocess
import sys
import os
import uuid
import json
import importlib.util
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from models import YoutubeRequest, PredictUrlRequest
from fastapi import HTTPException
from main import persist_results
from services.youtube_detection_service import YouTubeDetectionService
from services.detection_service_factory import DetectionServiceFactory
from core.logging import get_logger
import yt_dlp
from pathlib import Path
from .upload_videos import process_video_in_background, video_job_status, video_job_status_lock

logger = get_logger(__name__)


router = APIRouter()

# Diccionario global para almacenar el estado de los trabajos de YouTube
job_status: Dict[str, Dict] = {}
job_status_lock = threading.Lock()

# Cargar estado de trabajos desde archivo al iniciar
try:
    if os.path.exists('youtube_job_status.json'):
        with open('youtube_job_status.json', 'r') as f:
            loaded_data = json.load(f)
            job_status.update(loaded_data)
        logger.info(f"Cargados {len(job_status)} trabajos de YouTube desde archivo")
except Exception as e:
    logger.error(f"Error al cargar estado de trabajos de YouTube desde archivo: {e}")

def save_job_status():
    """Guarda el estado de los trabajos en archivo JSON"""
    try:
        with open('youtube_job_status.json', 'w') as f:
            json.dump({k: v for k, v in job_status.items()}, f, indent=2)
    except Exception as e:
        logger.error(f"Error al guardar estado de trabajos de YouTube: {e}")

def download_youtube_video(url: str, job_id: str) -> str:
    """Descarga un video de YouTube y retorna la ruta del archivo temporal."""
    try:
        # Crear directorio temporal para descargas de YouTube
        download_dir = Path("backend/temp_videos/youtube")
        download_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de yt-dlp
        ydl_opts = {
            'outtmpl': str(download_dir / f'{job_id}.%(ext)s'),
            'format': 'mp4/best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        logger.info(f"Iniciando descarga de YouTube: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Obtener información del video
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'Unknown')
            
            # Actualizar estado con información del video
            with job_status_lock:
                if job_id in job_status:
                    job_status[job_id]['video_title'] = video_title
                    job_status[job_id]['status'] = 'downloading'
                save_job_status()
            
            # Descargar el video
            ydl.download([url])
            
            # Encontrar el archivo descargado
            downloaded_files = list(download_dir.glob(f'{job_id}.*'))
            if not downloaded_files:
                raise Exception("No se pudo encontrar el archivo descargado")
            
            video_path = str(downloaded_files[0])
            logger.info(f"Video descargado exitosamente: {video_path}")
            
            return video_path
            
    except Exception as e:
        logger.error(f"Error descargando video de YouTube: {e}")
        raise e

def check_and_cancel_stuck_jobs():
    """Verifica y cancela jobs que estén atascados en 0% por más de 5 minutos"""
    timeout_minutes = 5
    current_time = datetime.now()
    
    with job_status_lock:
        jobs_to_cancel = []
        for job_id, job_data in job_status.items():
            if (job_data.get('status') == 'processing' and 
                job_data.get('progress', 0) == 0 and 
                'start_time' in job_data):
                
                try:
                    start_time = datetime.fromisoformat(job_data['start_time'])
                    elapsed_time = current_time - start_time
                    
                    if elapsed_time > timedelta(minutes=timeout_minutes):
                        jobs_to_cancel.append(job_id)
                        logger.warning(f"Job {job_id} atascado en 0% por {elapsed_time.total_seconds():.1f} segundos, cancelando...")
                except Exception as e:
                    logger.error(f"Error verificando tiempo para job {job_id}: {e}")
        
        # Cancelar jobs atascados
        for job_id in jobs_to_cancel:
            job_status[job_id].update({
                'status': 'error',
                'error': f'Job cancelado automáticamente: sin progreso por más de {timeout_minutes} minutos',
                'end_time': current_time.isoformat(),
                'progress': 0
            })
        
        if jobs_to_cancel:
            save_job_status()
            logger.info(f"Cancelados {len(jobs_to_cancel)} jobs atascados: {jobs_to_cancel}")

# Hilo para monitorear jobs atascados
def start_job_monitor():
    """Inicia el monitor de jobs atascados en un hilo separado"""
    def monitor_loop():
        while True:
            try:
                check_and_cancel_stuck_jobs()
                time.sleep(60)  # Verificar cada minuto
            except Exception as e:
                logger.error(f"Error en monitor de jobs: {e}")
                time.sleep(60)
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    logger.info("Monitor de jobs atascados iniciado")

# Iniciar el monitor al cargar el módulo
start_job_monitor()

@router.post("/process/youtube")
def process_youtube(data: YoutubeRequest, background_tasks: BackgroundTasks):
    job_id = f"youtube-job-{int(datetime.now().timestamp() * 1000)}"
    
    # Inicializar estado del trabajo
    with job_status_lock:
        job_status[job_id] = {
            "status": "initializing",
            "url": data.url,
            "start_time": datetime.now().isoformat(),
            "detections": 0,
            "frame_count": 0,
            "progress": 0,
            "total_frames": 0,
            "video_title": "",
            "source": "youtube"
        }
        save_job_status()

    def process_youtube_video():
        try:
            logger.info(f"Iniciando procesamiento de YouTube: {data.url}")
            
            # Paso 1: Descargar el video de YouTube
            video_path = download_youtube_video(data.url, job_id)
            
            # Paso 2: Registrar el job en el sistema de videos normal
            with video_job_status_lock:
                video_job_status[job_id] = {
                    "status": "processing",
                    "file_name": f"YouTube: {job_status[job_id].get('video_title', 'Unknown')}",
                    "start_time": datetime.now().isoformat(),
                    "detections": 0,
                    "frame_count": 0,
                    "progress": 0,
                    "total_frames": 0,
                    "video_path": video_path,
                    "source": "youtube",
                    "original_url": data.url
                }
            
            # Actualizar estado de YouTube
            with job_status_lock:
                if job_id in job_status:
                    job_status[job_id]["status"] = "processing"
                    job_status[job_id]["video_path"] = video_path
                save_job_status()
            
            # Paso 3: Usar la funcionalidad existente de procesamiento de videos
            logger.info(f"Procesando video descargado con funcionalidad de video normal: {video_path}")
            process_video_in_background(
                video_path, 
                job_id, 
                f"YouTube: {job_status[job_id].get('video_title', 'Unknown')}"
            )
            
            # El estado final será actualizado por process_video_in_background
            # Solo necesitamos sincronizar el estado entre los dos sistemas
            def sync_status():
                """Sincroniza el estado del procesamiento de video con el estado de YouTube"""
                while True:
                    time.sleep(2)  # Verificar cada 2 segundos
                    
                    with video_job_status_lock:
                        if job_id in video_job_status:
                            video_status = video_job_status[job_id]
                            
                            with job_status_lock:
                                if job_id in job_status:
                                    # Sincronizar estados
                                    job_status[job_id].update({
                                        "status": video_status["status"],
                                        "progress": video_status["progress"],
                                        "frame_count": video_status["frame_count"],
                                        "total_frames": video_status["total_frames"],
                                        "detections": video_status["detections"]
                                    })
                                    
                                    # Si el procesamiento terminó, agregar información específica de YouTube
                                    if video_status["status"] in ["completed", "error"]:
                                        job_status[job_id]["end_time"] = datetime.now().isoformat()
                                        if "processed_video_path" in video_status:
                                            job_status[job_id]["processed_video_path"] = video_status["processed_video_path"]
                                        
                                        # Limpiar archivo temporal después del procesamiento
                                        try:
                                            if os.path.exists(video_path):
                                                os.remove(video_path)
                                                logger.info(f"Archivo temporal eliminado: {video_path}")
                                        except Exception as e:
                                            logger.warning(f"No se pudo eliminar archivo temporal {video_path}: {e}")
                                        
                                        save_job_status()
                                        logger.info(f"Procesamiento de YouTube completado para job {job_id}")
                                        break
                                    
                                    save_job_status()
                        else:
                            # Si el job no existe en video_job_status, algo salió mal
                            with job_status_lock:
                                if job_id in job_status:
                                    job_status[job_id]["status"] = "error"
                                    job_status[job_id]["error"] = "Error en el procesamiento del video"
                                    save_job_status()
                            break
            
            # Ejecutar sincronización en un hilo separado
            sync_thread = threading.Thread(target=sync_status)
            sync_thread.daemon = True
            sync_thread.start()
            
        except Exception as e:
            logger.error(f"Error procesando YouTube URL {data.url}: {e}")
            with job_status_lock:
                if job_id in job_status:
                    job_status[job_id].update({
                        "status": "error",
                        "error": str(e),
                        "end_time": datetime.now().isoformat()
                    })
                    save_job_status()

    background_tasks.add_task(process_youtube_video)
    return {"job_id": job_id, "status": "processing"}


@router.get("/status/{job_id}")
def get_job_status(job_id: str):
    """
    Obtiene el estado actual de un trabajo de procesamiento.
    Verifica tanto en memoria como en el archivo JSON.
    """
    # Primero verificar en memoria
    if job_id in job_status:
        return job_status[job_id]
    
    # Si no está en memoria, verificar en el archivo JSON
    try:
        if os.path.exists('youtube_job_status.json'):
            with open('youtube_job_status.json', 'r') as f:
                saved_data = json.load(f)
                if job_id in saved_data:
                    # Cargar el job en memoria para futuras consultas
                    with job_status_lock:
                        job_status[job_id] = saved_data[job_id]
                    logger.info(f"Job {job_id} cargado desde archivo JSON")
                    return saved_data[job_id]
    except Exception as e:
        logger.error(f"Error leyendo archivo de estado: {e}")
    
    # Si no se encuentra en ningún lado
    return {
        "status": "not_found",
        "error": "Job not found or expired",
        "message": "El trabajo de procesamiento no fue encontrado. Esto puede ocurrir si el servidor se reinició. Por favor, inicia un nuevo procesamiento.",
        "job_id": job_id
    }

@router.get("/video/{job_id}")
def get_youtube_video_url(job_id: str, force_original: bool = False, force_processed: bool = False):
    """Obtiene la URL del video de YouTube para reproducción durante el procesamiento.
    
    Args:
        job_id: ID del trabajo de procesamiento de YouTube
        force_original: Si es True, fuerza el uso del video original (no disponible para YouTube)
        force_processed: Si es True, fuerza el uso del video procesado
    """
    from fastapi.responses import JSONResponse
    from fastapi import HTTPException
    
    # Verificar si el job existe
    if job_id not in job_status:
        # Intentar cargar desde archivo
        try:
            if os.path.exists('youtube_job_status.json'):
                with open('youtube_job_status.json', 'r') as f:
                    saved_data = json.load(f)
                    if job_id in saved_data:
                        with job_status_lock:
                            job_status[job_id] = saved_data[job_id]
        except Exception as e:
            logger.error(f"Error cargando job desde archivo: {e}")
    
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_data = job_status[job_id]
    
    # Para videos de YouTube, solo podemos ofrecer el video procesado
    # ya que el original se descarga temporalmente y se elimina
    if "processed_video_path" in job_data and os.path.exists(job_data["processed_video_path"]):
        video_path = job_data["processed_video_path"]
        return {
            "video_url": f"/static/temp_videos/{os.path.basename(video_path)}",
            "video_type": "processed",
            "status": job_data["status"],
            "message": "Video procesado disponible"
        }
    else:
        return JSONResponse(
            status_code=202,
            content={
                "message": "Video aún en procesamiento o no disponible",
                "status": job_data["status"],
                "progress": job_data.get("progress", 0)
            }
        )

def run_detection_script(url: str, job_id: str):
    """
    Ejecuta el script de detección en segundo plano y actualiza el estado del trabajo.
    Ahora usa el módulo directamente en lugar de un subproceso.
    """
    try:
        # Importar el módulo de detección dinámicamente
        try:
            # Intentar importar el módulo directamente
            from ..services.detection_image_youtube_slow import VideoProcessor
            use_module = True
        except ImportError:
            # Si falla, usar la ruta relativa para importar
            spec = importlib.util.spec_from_file_location(
                "detection_image_youtube_slow", 
                "backend/services/detection_image_youtube_slow.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            VideoProcessor = module.VideoProcessor
            use_module = True
        except Exception as e:
            print(f"Error al importar el módulo: {e}")
            use_module = False
        
        if use_module:
            # Función de callback para actualizar el estado del trabajo
            def update_status(status_data):
                if job_id in job_status:
                    job_status[job_id]["frame_count"] = status_data.get("frame_count", 0)
                    job_status[job_id]["progress"] = status_data.get("progress", 0)
                    job_status[job_id]["detections"] = status_data.get("detections", [])
            
            # Crear instancia del procesador y configurar callback
            processor = VideoProcessor("best_v5.pt", url)
            processor.set_status_callback(update_status)
            
            # Procesar el video
            success = processor.process_video()
            
            if success:
                # Obtener métricas finales
                metrics = processor.get_processing_metrics()
                
                # Actualizar el estado del trabajo
                if job_id in job_status:
                    job_status[job_id]["status"] = "completed"
                    job_status[job_id]["detections"] = metrics["detection_results"]
                    job_status[job_id]["total_video_time_segs"] = metrics["video_info"]["total_video_time_segs"]
                    job_status[job_id]["end_time"] = datetime.now().isoformat()
                    
                    # Enviar resultados al backend para persistencia
                    processor.send_results_to_backend()
            else:
                if job_id in job_status:
                    job_status[job_id]["status"] = "error"
                    job_status[job_id]["error"] = "Error al procesar el video"
        else:
            # Fallback: ejecutar como subproceso si no se puede importar el módulo
            result = subprocess.run([
                sys.executable,
                "backend/services/detection_image_youtube_slow.py",
                url
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Procesar la salida del script
                output = result.stdout
                
                # Actualizar el estado del trabajo
                if job_id in job_status:
                    job_status[job_id]["status"] = "completed"
                    job_status[job_id]["output"] = output
                    job_status[job_id]["end_time"] = datetime.now().isoformat()
            else:
                if job_id in job_status:
                    job_status[job_id]["status"] = "error"
                    job_status[job_id]["error"] = result.stderr
    except Exception as e:
        if job_id in job_status:
            job_status[job_id]["status"] = "error"
            job_status[job_id]["error"] = str(e)

@router.post("/predict/url")
def predict_url(data: PredictUrlRequest):
    try:
        id_video = persist_results(
            vtype=data.type,
            name=data.name,
            fps=data.fps_estimated,
            total_secs=data.duration_sec,
            summary=data.detections,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "id_video": id_video,
        "type": data.type,
        "name": data.name,
        "fps_estimated": data.fps_estimated,
        "processed_secs": data.duration_sec,
        "detections": data.detections,
    }