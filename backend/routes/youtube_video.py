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
from datetime import datetime
from typing import Dict, Optional
from ..models import YoutubeRequest, PredictUrlRequest
from fastapi import HTTPException
from main import persist_results


router = APIRouter()

# Diccionario para almacenar el estado de los trabajos
job_status: Dict[str, Dict] = {}

@router.post("/process/youtube")
def process_youtube(data: YoutubeRequest, background_tasks: BackgroundTasks):
    """
    Procesa un video de YouTube usando el script detection_image_youtube_slow.py y retorna las métricas.
    Ahora ejecuta el procesamiento en segundo plano y devuelve un ID de trabajo.
    """
    # Generar un ID único para este trabajo usando timestamp para compatibilidad con frontend
    job_id = f"youtube-job-{int(datetime.now().timestamp() * 1000)}"
    
    # Inicializar el estado del trabajo
    job_status[job_id] = {
        "status": "processing",
        "url": data.url,
        "start_time": datetime.now().isoformat(),
        "detections": [],
        "total_video_time_segs": 0
    }
    
    # Ejecutar el script de procesamiento en segundo plano
    background_tasks.add_task(
        run_detection_script, data.url, job_id
    )
    
    return {"job_id": job_id, "status": "processing"}

@router.get("/status/{job_id}")
def get_job_status(job_id: str):
    """
    Obtiene el estado actual de un trabajo de procesamiento.
    """
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status[job_id]

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

@router.post("/process/youtube")
def process_youtube(data: YoutubeRequest):
    """
    Procesa un video de YouTube y retorna las métricas.
    """
    import json # Importa la librería json
    try:
        # Llama al script como subproceso
        result = subprocess.run([
            sys.executable,
            "services/detection_image_youtube_slow.py", # La ruta que ya corregiste
            data.url
        ], capture_output=True, text=True, timeout=600)
        
        # Si el subproceso falla, devuelve el error
        if result.returncode != 0:
            return {"error": result.stderr}

        # Parsea la salida del subproceso como JSON
        # El script ahora devuelve un JSON en lugar de texto plano
        response_data = json.loads(result.stdout)
        
        # Si el script reporta un fallo, lo manejas
        if not response_data.get("success", False):
            raise HTTPException(status_code=500, detail="El procesamiento del video falló.")
        
        return response_data

    except json.JSONDecodeError:
        # Si la salida del script no es un JSON válido, algo falló
        raise HTTPException(status_code=500, detail="Error al procesar la respuesta del script.")
    except Exception as e:
        # Otros errores de ejecución
        raise HTTPException(status_code=500, detail=str(e))