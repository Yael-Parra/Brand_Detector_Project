# =======================================================
# Endpoint para procesar YouTube desde frontend o Swagger
# =======================================================

from fastapi import Body, APIRouter
import subprocess
import sys
from ..models import YoutubeRequest

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
            "backend/services/detection_image_youtube_slow.py",
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