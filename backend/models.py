
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class ImageUploadResponse(BaseModel):
    detections: list
    annotated_jpg_base64: Optional[str] = None

class YoutubeRequest(BaseModel):
    url: str

class PredictUrlRequest(BaseModel):
    type: str = Field(..., description="url o mp4")
    name: str = Field(..., description="URL o nombre de archivo")
    duration_sec: int = Field(..., ge=0)
    fps_estimated: float = Field(..., ge=0)
    detections: Dict[str, Any]