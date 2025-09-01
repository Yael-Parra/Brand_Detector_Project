from fastapi import APIRouter, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
import tempfile
import cv2
import os
import time
import json
from datetime import datetime
from typing import Dict
#from ..services.yolo_service import get_model
from ultralytics import YOLO
import threading


router = APIRouter()

# Diccionario para almacenar el estado de los trabajos de video
video_job_status: Dict[str, Dict] = {}

# Mutex para proteger el acceso al diccionario
video_job_status_lock = threading.Lock()

# Cargar el estado de los trabajos desde el archivo al iniciar
try:
    if os.path.exists('video_job_status.json'):
        with open('video_job_status.json', 'r') as f:
            loaded_data = json.load(f)
            video_job_status.update(loaded_data)
        print(f"Cargados {len(video_job_status)} trabajos desde archivo: {list(video_job_status.keys())}")
except Exception as e:
    print(f"Error al cargar estado de trabajos desde archivo: {e}")


# =========================================
# Endpoint para procesar videos mp4 subidos
# =========================================

@router.post("/predict/mp4")
async def predict_mp4(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Generar un ID único para este trabajo usando timestamp para compatibilidad con frontend
    job_id = f"video-job-{int(datetime.now().timestamp() * 1000)}"
    
    # Guardar el archivo temporalmente
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
        temp_video.write(await file.read())
        temp_video_path = temp_video.name
    
    # Inicializar el estado del trabajo con el mutex
    with video_job_status_lock:
        video_job_status[job_id] = {
            "status": "processing",
            "file_name": file.filename,
            "start_time": datetime.now().isoformat(),
            "detections": 0,
            "frame_count": 0,
            "progress": 0,
            "total_frames": 0
        }
        # Guardar el estado actual en un archivo para depuración
        try:
            with open('video_job_status.json', 'w') as f:
                json.dump({k: v for k, v in video_job_status.items()}, f, indent=2)
        except Exception as e:
            print(f"Error al guardar estado: {e}")
    
    print(f"Iniciando procesamiento para job_id: {job_id}")
    
    # Ejecutar el procesamiento en segundo plano
    background_tasks.add_task(
        process_video_in_background, temp_video_path, job_id, file.filename
    )
    
    return {"job_id": job_id, "status": "processing"}

# Endpoint para verificar el estado de un trabajo de procesamiento de video
@router.get("/status/{job_id}", response_model=dict)
async def get_job_status(job_id: str):
    """Obtiene el estado actual de un trabajo de procesamiento de video."""
    print(f"Solicitud de estado para job_id: {job_id}")
    with video_job_status_lock:
        # Intentar cargar el estado desde el archivo si no está en memoria
        if job_id not in video_job_status:
            try:
                if os.path.exists('video_job_status.json'):
                    with open('video_job_status.json', 'r') as f:
                        saved_status = json.load(f)
                        # Actualizar el diccionario en memoria con los datos guardados
                        for k, v in saved_status.items():
                            if k not in video_job_status:
                                video_job_status[k] = v
                    print(f"Recargados {len(saved_status)} trabajos desde archivo")
            except Exception as e:
                print(f"Error al cargar estado desde archivo: {e}")
        
        # Verificar nuevamente si el job_id existe después de intentar cargarlo
        if job_id not in video_job_status:
            print(f"Job ID no encontrado: {job_id}")
            print(f"Jobs disponibles: {list(video_job_status.keys())}")
            
            # Intentar buscar el job_id directamente en el archivo como último recurso
            try:
                if os.path.exists('video_job_status.json'):
                    with open('video_job_status.json', 'r') as f:
                        saved_status = json.load(f)
                        if job_id in saved_status:
                            # Encontrado en archivo pero no en memoria
                            video_job_status[job_id] = saved_status[job_id]
                            print(f"Job ID {job_id} recuperado directamente del archivo")
                        else:
                            # Si el job_id comienza con video-job- o youtube-job-, crear un estado temporal
                            if job_id.startswith('video-job-') or job_id.startswith('youtube-job-'):
                                print(f"Creando estado temporal para job_id: {job_id}")
                                # Crear un estado temporal para evitar errores 404
                                video_job_status[job_id] = {
                                    "status": "processing",
                                    "file_name": "unknown_file.mp4",
                                    "start_time": datetime.now().isoformat(),
                                    "detections": 0,
                                    "frame_count": 0,
                                    "progress": 0,
                                    "total_frames": 100  # Valor predeterminado
                                }
                                # Guardar el estado temporal en el archivo
                                try:
                                    with open('video_job_status.json', 'w') as f:
                                        json.dump(video_job_status, f, indent=2)
                                except Exception as e_save:
                                    print(f"Error al guardar estado temporal: {e_save}")
                            else:
                                return JSONResponse(status_code=404, content={"detail": "Job not found in memory or file"})
                else:
                    # Si el archivo no existe pero el job_id parece válido, crear un estado temporal
                    if job_id.startswith('video-job-') or job_id.startswith('youtube-job-'):
                        print(f"Creando estado temporal para job_id: {job_id} (sin archivo)")
                        video_job_status[job_id] = {
                            "status": "processing",
                            "file_name": "unknown_file.mp4",
                            "start_time": datetime.now().isoformat(),
                            "detections": 0,
                            "frame_count": 0,
                            "progress": 0,
                            "total_frames": 100  # Valor predeterminado
                        }
                        # Crear el archivo y guardar el estado
                        try:
                            with open('video_job_status.json', 'w') as f:
                                json.dump(video_job_status, f, indent=2)
                        except Exception as e_save:
                            print(f"Error al crear archivo de estado: {e_save}")
                    else:
                        return JSONResponse(status_code=404, content={"detail": "Job not found and no status file exists"})
            except Exception as e:
                print(f"Error al buscar job_id en archivo: {e}")
                # Último recurso: crear un estado temporal si el job_id parece válido
                if job_id.startswith('video-job-') or job_id.startswith('youtube-job-'):
                    print(f"Creando estado temporal después de error para job_id: {job_id}")
                    video_job_status[job_id] = {
                        "status": "processing",
                        "file_name": "recovery_file.mp4",
                        "start_time": datetime.now().isoformat(),
                        "detections": 0,
                        "frame_count": 0,
                        "progress": 0,
                        "total_frames": 100  # Valor predeterminado
                    }
                else:
                    return JSONResponse(status_code=404, content={"detail": "Error checking job status"})
        
        # Devolver una copia del estado para evitar problemas de concurrencia
        return dict(video_job_status[job_id])

def process_video_in_background(video_path: str, job_id: str, filename: str):
    """Procesa un video en segundo plano y actualiza el estado del trabajo."""
    try:
        start_time = time.time()
        
        # Cargar modelo YOLO
        model = YOLO("best_v5.pt")
        cap = cv2.VideoCapture(video_path)
        
        # Obtener información del video
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        
        # Actualizar el estado con el total de frames
        if job_id in video_job_status:
            video_job_status[job_id]["total_frames"] = total_frames
        
        label_frames = {}
        frame_idx = 0
        total_detections = 0
        
        # Procesar el video frame por frame
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Procesar el frame con YOLO
            results = model(frame)
            frame_detections = 0
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0]) if hasattr(box, 'cls') else None
                    label = model.names.get(cls, str(cls))
                    if label:
                        label_frames[label] = label_frames.get(label, 0) + 1
                        frame_detections += 1
            
            # Actualizar contadores
            frame_idx += 1
            total_detections += frame_detections
            
            # Actualizar el estado del trabajo cada 10 frames
            if frame_idx % 10 == 0:
                progress = (frame_idx / total_frames * 100) if total_frames > 0 else 0
                print(f"Progreso: {progress:.2f}% - Frame: {frame_idx}/{total_frames} - Detecciones: {total_detections}")
                
                # Imprimir las etiquetas detectadas hasta ahora
                print(f"Etiquetas detectadas: {label_frames}")
                
                # Usar el mutex para actualizar el estado
                with video_job_status_lock:
                    if job_id in video_job_status:
                        video_job_status[job_id].update({
                            "frame_count": frame_idx,
                            "progress": progress,
                            "detections": total_detections,
                            "labels": label_frames  # Añadir conteo de etiquetas en tiempo real
                        })
                    else:
                        print(f"ADVERTENCIA: job_id {job_id} no encontrado en video_job_status")
                        # Recrear el estado del trabajo si no existe
                        video_job_status[job_id] = {
                            "status": "processing",
                            "file_name": filename,
                            "start_time": datetime.now().isoformat(),
                            "detections": total_detections,
                            "labels": label_frames,  # Añadir conteo de etiquetas
                            "frame_count": frame_idx,
                            "progress": progress,
                            "total_frames": total_frames
                        }
                    
                    # Guardar el estado actualizado en el archivo
                    try:
                        with open('video_job_status.json', 'w') as f:
                            json.dump({k: v for k, v in video_job_status.items()}, f, indent=2)
                    except Exception as e:
                        print(f"Error al guardar estado: {e}")
        
        # Liberar recursos
        cap.release()
        
        # Calcular tiempo de procesamiento
        end_time = time.time()
        processed_secs = end_time - start_time
        
        # Generar resumen de detecciones
        from ..services.yolo_service import summarize_counts
        detections_summary = summarize_counts(label_frames, frame_idx)
        
        # Actualizar el estado final del trabajo con el mutex
        with video_job_status_lock:
            if job_id in video_job_status:
                video_job_status[job_id].update({
                    "status": "completed",
                    "end_time": datetime.now().isoformat(),
                    "detections": detections_summary,
                    "labels": label_frames,  # Mantener el conteo de etiquetas en el resultado final
                    "fps_estimated": fps,
                    "processed_secs": processed_secs,
                    "progress": 100
                })
                
                # Imprimir resumen final de etiquetas detectadas
                print(f"\nResumen final de detecciones para {job_id}:")
                print(f"Total de frames procesados: {frame_idx}")
                print(f"Total de detecciones: {total_detections}")
                print("Etiquetas detectadas:")
                for label, count in label_frames.items():
                    print(f"  - {label}: {count} veces")
                
                # Guardar el estado final en el archivo
                try:
                    with open('video_job_status.json', 'w') as f:
                        json.dump({k: v for k, v in video_job_status.items()}, f, indent=2)
                except Exception as e:
                    print(f"Error al guardar estado final: {e}")
        
        # Limpiar el archivo temporal
        try:
            os.remove(video_path)
        except Exception as e:
            print(f"Error al eliminar archivo temporal: {e}")
    
    except Exception as e:
        # Actualizar el estado con el error usando el mutex
        with video_job_status_lock:
            if job_id in video_job_status:
                video_job_status[job_id].update({
                    "status": "error",
                    "error": str(e),
                    "end_time": datetime.now().isoformat()
                })
                
                # Guardar el estado de error en el archivo
                try:
                    with open('video_job_status.json', 'w') as f:
                        json.dump({k: v for k, v in video_job_status.items()}, f, indent=2)
                except Exception as e_save:
                    print(f"Error al guardar estado de error: {e_save}")
                    
        print(f"Error al procesar video: {e}")
        
        # Intentar limpiar el archivo temporal en caso de error
        try:
            os.remove(video_path)
        except Exception as e_remove:
            print(f"Error al eliminar archivo temporal: {e_remove}")