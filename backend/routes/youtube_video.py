# =======================================================
# Endpoint para procesar YouTube desde frontend o Swagger
# =======================================================

from fastapi import APIRouter
import subprocess
import sys
from backend.models import YoutubeRequest, PredictUrlRequest
from fastapi import HTTPException
from backend.main import persist_results
from backend.services.detection_image_youtube_slow import VideoProcessor

router = APIRouter()

@router.post("/process/youtube")
def process_youtube(data: YoutubeRequest):
    try:
        processor = VideoProcessor(model_path="best_v5.pt", video_source=data.url)
        processor.process_with_yolo_stream()
        metrics = processor.get_processing_metrics()

        # Guardar en BD reutilizando persist_results
        id_video = persist_results(
            vtype=metrics["video_info"]["type"],
            name=metrics["video_info"]["name"],
            fps=metrics["total_frames_processed"] / metrics["video_info"]["total_video_time_segs"] if metrics["video_info"]["total_video_time_segs"] > 0 else 0.0,
            total_secs=metrics["video_info"]["total_video_time_segs"],
            summary=metrics["detection_results"],
        )

        return {"id_video": id_video, **metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



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