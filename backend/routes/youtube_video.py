# =======================================================
# Endpoint para procesar YouTube desde frontend o Swagger
# =======================================================

from fastapi import APIRouter
import subprocess
import sys
from models import YoutubeRequest, PredictUrlRequest
from fastapi import HTTPException
from main import persist_results


router = APIRouter()

@router.post("/process/youtube")
def process_youtube(data: YoutubeRequest):
    """
    Procesa un video de YouTube usando el script detection_image_youtube_slow.py y retorna las métricas.
    """
    # Llama al script como subproceso, pasando la URL como argumento
    try:
        result = subprocess.run([
            sys.executable,
            "services/detection_image_youtube_slow.py",
            data.url
        ], capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            # Busca la sección de métricas en la salida
            output = result.stdout
            # Opcional: puedes parsear la salida para devolver solo las métricas
            return {"output": output}
        else:
            return {"error": result.stderr, "output": result.stdout}
    except Exception as e:
        return {"error": str(e)}  

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