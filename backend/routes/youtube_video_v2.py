# =======================================================
# Endpoint mejorado para procesar YouTube directamente
# =======================================================

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from ..models import YoutubeRequest, PredictUrlRequest
from ..services.detection_image_youtube_slow import VideoProcessor
import os
import traceback
from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

# Simulación de base de datos en memoria para almacenar resultados
_video_results = {}

@router.post("/predict/url", response_model=dict)
async def persist_results(data: PredictUrlRequest):
    """
    Persiste los resultados del procesamiento de un video de YouTube.
    Esta función es llamada por VideoProcessor.send_results_to_backend().
    """
    try:
        # Generar un ID único para este resultado
        result_id = f"video_{len(_video_results) + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Almacenar los resultados en memoria
        _video_results[result_id] = {
            "id": result_id,
            "type": data.type,
            "name": data.name,
            "duration_sec": data.duration_sec,
            "fps_estimated": data.fps_estimated,
            "detections": data.detections,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"✓ Resultados persistidos con ID: {result_id}")
        
        return {
            "status": "success",
            "message": "Resultados guardados correctamente",
            "id": result_id
        }
    except Exception as e:
        print(f"✗ Error al persistir resultados: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al persistir resultados: {str(e)}")

@router.get("/results/{result_id}", response_model=dict)
async def get_result(result_id: str):
    """
    Obtiene los resultados de un procesamiento específico por su ID.
    """
    if result_id not in _video_results:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    
    return _video_results[result_id]

@router.get("/results", response_model=list)
async def list_results():
    """
    Lista todos los resultados de procesamiento almacenados.
    """
    return list(_video_results.values())

@router.get("/stats", response_model=dict)
async def get_stats():
    """
    Obtiene estadísticas generales de todos los videos procesados.
    """
    if not _video_results:
        return {
            "total_videos": 0,
            "total_duration": 0,
            "labels": {}
        }
    
    total_videos = len(_video_results)
    total_duration = sum(result["duration_sec"] for result in _video_results.values())
    
    # Agregar todas las etiquetas detectadas
    all_labels = {}
    for result in _video_results.values():
        for label, data in result["detections"].items():
            if label not in all_labels:
                all_labels[label] = {
                    "total_detections": 0,
                    "videos_with_label": 0
                }
            
            all_labels[label]["total_detections"] += data["qty_frames_detected"]
            all_labels[label]["videos_with_label"] += 1
    
    return {
        "total_videos": total_videos,
        "total_duration": total_duration,
        "labels": all_labels
    }

class YoutubeResponseV2(BaseModel):
    status: str
    message: str
    video_info: Optional[Dict[str, Any]] = None
    detections: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@router.post("/process/youtube_v2", response_model=YoutubeResponseV2)
async def process_youtube_v2(data: YoutubeRequest, background_tasks: BackgroundTasks):
    """
    Procesa un video de YouTube directamente usando VideoProcessor y retorna las métricas.
    Esta versión mejorada no usa subprocess y maneja mejor los errores.
    """
    try:
        # Validar la URL
        if not data.url or not data.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="URL inválida. Debe comenzar con http:// o https://")
            
        # Inicializar el procesador de video con el modelo YOLO
        model_path = os.path.join(os.getcwd(), "best.pt")
        processor = VideoProcessor(model_path, data.url)
        
        # Procesar el video en segundo plano
        def process_in_background():
            try:
                success = processor.process_video()
                if success:
                    metrics = processor.get_processing_metrics()
                    # Enviar resultados al backend para persistencia
                    processor.send_results_to_backend()
            except Exception as e:
                print(f"Error en procesamiento en segundo plano: {str(e)}")
                traceback.print_exc()
        
        # Iniciar procesamiento en segundo plano
        background_tasks.add_task(process_in_background)
        
        # Devolver respuesta inmediata
        return YoutubeResponseV2(
            status="processing",
            message="El video se está procesando en segundo plano. Los resultados se guardarán automáticamente."
        )
        
    except Exception as e:
        traceback.print_exc()
        return YoutubeResponseV2(
            status="error",
            message="Error al procesar el video",
            error=str(e)
        )

@router.post("/process/youtube_v2/sync", response_model=YoutubeResponseV2)
def process_youtube_v2_sync(data: YoutubeRequest):
    """
    Versión síncrona que procesa el video y espera los resultados.
    Útil para pruebas o videos cortos.
    """
    try:
        # Validar la URL
        if not data.url or not data.url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="URL inválida. Debe comenzar con http:// o https://")
            
        # Inicializar el procesador de video con el modelo YOLO
        model_path = os.path.join(os.getcwd(), "best.pt")
        processor = VideoProcessor(model_path, data.url)
        
        # Procesar el video y esperar resultados
        success = processor.process_video()
        
        if success:
            # Obtener métricas y enviar resultados al backend
            metrics = processor.get_processing_metrics()
            processor.send_results_to_backend()
            
            # Devolver resultados completos
            return YoutubeResponseV2(
                status="success",
                message="Video procesado correctamente",
                video_info=metrics["video_info"],
                detections=metrics["detection_results"]
            )
        else:
            return YoutubeResponseV2(
                status="error",
                message="No se pudo procesar el video correctamente"
            )
            
    except Exception as e:
        traceback.print_exc()
        return YoutubeResponseV2(
            status="error",
            message="Error al procesar el video",
            error=str(e)
        )