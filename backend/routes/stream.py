# ==================================================
# Endpoint para procesar live videos desde la webcam
# ==================================================

import cv2
import base64
import json
import numpy as np
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from ultralytics import YOLO

from core.logging import get_logger
from services.detection_service_factory import DetectionServiceFactory
from services.streaming_detection_service import StreamingDetectionService

logger = get_logger(__name__)
router = APIRouter()

# Instancia global del modelo YOLO para streaming
try:
    model = YOLO("best_v5.pt")
    logger.info("YOLO model loaded successfully for webcam streaming")
except Exception as e:
    logger.error(f"Failed to load YOLO model: {e}")
    model = None

# Cámara global para streaming MJPEG
camera = None

def get_camera():
    """Obtiene la instancia de la cámara"""
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            raise HTTPException(status_code=500, detail="No se pudo acceder a la cámara")
    return camera

def generate_frames():
    """Genera frames para streaming MJPEG"""
    try:
        cap = get_camera()
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            if model is not None:
                # Procesar frame con YOLO
                results = model(frame)
                annotated_frame = results[0].plot()
            else:
                annotated_frame = frame
            
            # Codificar en JPG
            _, buffer = cv2.imencode(".jpg", annotated_frame)
            frame_bytes = buffer.tobytes()
            
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
    except Exception as e:
        logger.error(f"Error in frame generation: {e}")
        yield b"--frame\r\n\r\n"

def decode_image(image_base64: str) -> np.ndarray:
    """Decodifica imagen base64 a numpy array"""
    try:
        img_bytes = base64.b64decode(image_base64)
        img_array = np.frombuffer(img_bytes, np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        logger.error(f"Error decoding image: {e}")
        return None

def encode_image(img: np.ndarray) -> str:
    """Codifica numpy array a base64"""
    try:
        _, buffer = cv2.imencode('.jpg', img)
        return base64.b64encode(buffer).decode("utf-8")
    except Exception as e:
        logger.error(f"Error encoding image: {e}")
        return ""

@router.get("/webcam/stream")
async def webcam_stream():
    """Endpoint para streaming MJPEG de la webcam con detección YOLO"""
    try:
        return StreamingResponse(
            generate_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame"
        )
    except Exception as e:
        logger.error(f"Error starting webcam stream: {e}")
        raise HTTPException(status_code=500, detail=f"Error al iniciar streaming: {str(e)}")

@router.websocket("/webcam/ws")
async def webcam_websocket(websocket: WebSocket):
    """WebSocket endpoint para procesamiento de frames en tiempo real"""
    await websocket.accept()
    logger.info("WebSocket connection established for webcam")
    
    try:
        while True:
            # Recibir frame del cliente
            data = await websocket.receive_text()
            
            # Decodificar frame
            frame = decode_image(data)
            if frame is None:
                await websocket.send_text(json.dumps({"error": "Invalid frame data"}))
                continue
            
            if model is not None:
                # Procesar con YOLO
                results = model(frame)
                annotated_frame = results[0].plot()
                
                # Extraer detecciones
                detections = []
                for r in results:
                    boxes = r.boxes
                    if boxes is not None:
                        for box in boxes:
                            detection = {
                                "class": r.names[int(box.cls)],
                                "confidence": float(box.conf),
                                "bbox": box.xyxy[0].tolist()
                            }
                            detections.append(detection)
                
                # Enviar frame procesado y detecciones
                response = {
                    "frame": encode_image(annotated_frame),
                    "detections": detections,
                    "timestamp": cv2.getTickCount() / cv2.getTickFrequency()
                }
            else:
                # Sin modelo, solo devolver frame original
                response = {
                    "frame": encode_image(frame),
                    "detections": [],
                    "error": "YOLO model not available"
                }
            
            await websocket.send_text(json.dumps(response))
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for webcam")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except:
            pass

@router.get("/webcam/status")
async def webcam_status():
    """Obtiene el estado de la cámara"""
    try:
        cap = cv2.VideoCapture(0)
        is_available = cap.isOpened()
        cap.release()
        
        return {
            "camera_available": is_available,
            "model_loaded": model is not None,
            "status": "ready" if is_available and model is not None else "not_ready"
        }
    except Exception as e:
        logger.error(f"Error checking webcam status: {e}")
        return {
            "camera_available": False,
            "model_loaded": model is not None,
            "status": "error",
            "error": str(e)
        }

@router.post("/webcam/release")
async def release_camera():
    """Libera la cámara"""
    global camera
    try:
        if camera is not None:
            camera.release()
            camera = None
        return {"message": "Camera released successfully"}
    except Exception as e:
        logger.error(f"Error releasing camera: {e}")
        raise HTTPException(status_code=500, detail=f"Error al liberar cámara: {str(e)}")