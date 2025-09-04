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

# Función para crear directorios temporales en el backend
def create_temp_directory():
    """Crea un directorio temporal dentro del backend si no existe"""
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_videos")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir

@router.post("/predict/mp4")
async def predict_mp4(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    # Generar un ID único para este trabajo usando timestamp para compatibilidad con frontend
    job_id = f"video-job-{int(datetime.now().timestamp() * 1000)}"
    
    # Crear directorio temporal en el backend
    temp_dir = create_temp_directory()
    
    # Guardar el archivo en el directorio temporal del backend
    filename = f"{job_id}.mp4"
    temp_video_path = os.path.join(temp_dir, filename)
    
    # Escribir el contenido del archivo
    with open(temp_video_path, "wb") as temp_video:
        temp_video.write(await file.read())
    
    # Inicializar el estado del trabajo con el mutex
    with video_job_status_lock:
        video_job_status[job_id] = {
            "status": "processing",
            "file_name": file.filename,
            "start_time": datetime.now().isoformat(),
            "detections": 0,
            "frame_count": 0,
            "progress": 0,
            "total_frames": 0,
            "video_path": temp_video_path  # Guardar la ruta del video para acceso posterior
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

# Endpoint para obtener la URL del video durante el procesamiento
@router.get("/video/{job_id}")
async def get_video_url(job_id: str, force_original: bool = False, force_processed: bool = False):
    """Obtiene la URL del video para reproducción durante el procesamiento.
    
    Args:
        job_id: ID del trabajo de procesamiento
        force_original: Si es True, fuerza el uso del video original
        force_processed: Si es True, fuerza el uso del video procesado (tiene prioridad sobre force_original)
    """
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    import os
    import time
    from datetime import datetime
    
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] SOLICITUD DE VIDEO para job_id: {job_id}")
    print(f"Parámetros: force_original={force_original}, force_processed={force_processed}")
    
    # Información de diagnóstico para ambos videos
    original_info = {
        "exists": False,
        "size": 0,
        "path": "",
        "last_modified": ""
    }
    
    processed_info = {
        "exists": False,
        "size": 0,
        "path": "",
        "last_modified": ""
    }
    
    with video_job_status_lock:
        if job_id not in video_job_status:
            # Intentar cargar desde el archivo
            try:
                if os.path.exists('video_job_status.json'):
                    with open('video_job_status.json', 'r') as f:
                        saved_status = json.load(f)
                        if job_id in saved_status:
                            video_job_status[job_id] = saved_status[job_id]
                            print(f"Estado cargado desde archivo para job_id: {job_id}")
            except Exception as e:
                print(f"Error al cargar estado desde archivo: {e}")
        
        if job_id in video_job_status:
            # Obtener rutas de videos
            original_path = video_job_status[job_id].get('video_path', '')
            processed_path = video_job_status[job_id].get('processed_video_path', '')
            
            # Verificar video original
            if original_path and os.path.exists(original_path):
                original_info["exists"] = True
                original_info["size"] = os.path.getsize(original_path)
                original_info["path"] = original_path
                original_info["last_modified"] = datetime.fromtimestamp(os.path.getmtime(original_path)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Verificar video procesado
            if processed_path and os.path.exists(processed_path):
                processed_info["exists"] = True
                processed_info["size"] = os.path.getsize(processed_path)
                processed_info["path"] = processed_path
                processed_info["last_modified"] = datetime.fromtimestamp(os.path.getmtime(processed_path)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Mostrar información de diagnóstico
            print(f"Estado actual del trabajo {job_id}:")
            print(f"  - Status: {video_job_status[job_id].get('status', 'desconocido')}")
            print(f"  - Video original: {original_path} (existe: {original_info['exists']}, tamaño: {original_info['size']} bytes)")
            print(f"  - Video procesado: {processed_path} (existe: {processed_info['exists']}, tamaño: {processed_info['size']} bytes)")
            
            # Determinar qué video usar según los parámetros y disponibilidad
            video_path = None
            video_type = "ninguno"
            
            # Prioridad 1: Video procesado forzado
            if force_processed and processed_info["exists"] and processed_info["size"] > 0:
                video_path = processed_path
                video_type = "procesado (forzado)"
            
            # Prioridad 2: Video original forzado
            elif force_original and original_info["exists"] and original_info["size"] > 0:
                video_path = original_path
                video_type = "original (forzado)"
            
            # Prioridad 3: Video procesado si existe y tiene tamaño
            elif not force_original and processed_info["exists"] and processed_info["size"] > 0:
                video_path = processed_path
                video_type = "procesado"
                print(f"Video procesado verificado con tamaño: {processed_info['size']} bytes")
            
            # Prioridad 4: Video original como fallback
            elif original_info["exists"] and original_info["size"] > 0:
                video_path = original_path
                video_type = "original (fallback)"
            
            # Verificar que el archivo existe
            if video_path and os.path.exists(video_path):
                # Crear una URL temporal para el video
                # Asegurarse de que la URL use el nombre de archivo correcto
                video_url = f"/temp_videos/{os.path.basename(video_path)}"
                print(f"URL de video generada: {video_url} para archivo: {video_path}")
                print(f"Tipo de video seleccionado: {video_type}")
                
                # Verificar que el archivo existe y tiene contenido
                file_size = os.path.getsize(video_path)
                print(f"Tamaño del archivo de video: {file_size} bytes")
                
                # Si el archivo está vacío, intentar regenerar la URL
                if file_size == 0:
                    print(f"ADVERTENCIA: El archivo de video tiene tamaño cero: {video_path}")
                    # Intentar usar el video original si el procesado está vacío
                    if video_path == processed_path and original_info["exists"] and original_info["size"] > 0:
                        video_path = original_path
                        video_url = f"/temp_videos/{os.path.basename(video_path)}"
                        video_type = "original (fallback por tamaño cero)"
                        print(f"Usando video original como fallback: {video_path}")
                        print(f"URL de video regenerada: {video_url}")
                        print(f"Tipo de video actualizado: {video_type}")
                
                # Montar el directorio temporal como un directorio estático si no está montado
                # Importar app de manera que funcione tanto en modo módulo como en modo script
                try:
                    # Intento de importación relativa
                    from ..main import app
                except ImportError:
                    # Fallback para cuando se ejecuta como script
                    import sys
                    import importlib.util
                    # Importación absoluta usando la ruta del archivo
                    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                    from main import app
                
                # Usar el directorio temporal del backend
                temp_dir = create_temp_directory()
                
                # Verificar si ya está montado
                mounted = False
                for route in app.routes:
                    if hasattr(route, "path") and route.path == "/temp_videos":
                        mounted = True
                        break
                
                if not mounted:
                    app.mount("/temp_videos", StaticFiles(directory=temp_dir), name="temp_videos")
                
                # Devolver la URL del video con información de diagnóstico
                return {
                    "video_url": video_url,
                    "video_info": {
                        "path": video_path,
                        "size": os.path.getsize(video_path),
                        "type": video_type,
                        "is_processed": "processed_video_path" in video_job_status[job_id] and video_path == video_job_status[job_id]["processed_video_path"],
                        "is_original": "video_path" in video_job_status[job_id] and video_path == video_job_status[job_id]["video_path"],
                        "job_status": video_job_status[job_id].get("status", "desconocido"),
                        "last_modified": datetime.fromtimestamp(os.path.getmtime(video_path)).strftime('%Y-%m-%d %H:%M:%S'),
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
                    },
                    "original_video": original_info,
                    "processed_video": processed_info
                }
            else:
                return JSONResponse(status_code=404, content={"detail": "Video file not found"})
        else:
            return JSONResponse(status_code=404, content={"detail": "Video path not found for job"})

# Endpoint para verificar el estado de un trabajo de procesamiento de video
@router.get("/status/{job_id}", response_model=dict)
async def get_job_status(job_id: str, include_video_info: bool = False):
    """Obtiene el estado actual de un trabajo de procesamiento de video.
    
    Args:
        job_id: ID del trabajo de procesamiento
        include_video_info: Si es True, incluye información detallada sobre los archivos de video
    """
    import time
    
    print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] SOLICITUD DE ESTADO para job_id: {job_id}")
    print(f"Parámetros: include_video_info={include_video_info}")
    
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
        
        # Preparar la respuesta con la lista de detecciones si existe
        status_data = dict(video_job_status[job_id])
        
        # Si hay una lista de detecciones, asegurarse de que se incluya en la respuesta
        if "detections_list" in status_data:
            # Mantener el campo detections_list pero también asignar a detections para compatibilidad
            if isinstance(status_data["detections"], int):
                status_data["detections"] = status_data["detections_list"]
        
        # Añadir información detallada sobre los archivos de video si se solicita
        if include_video_info:
            video_info = {}
            
            # Verificar el video original
            if "video_path" in status_data:
                original_path = status_data["video_path"]
                video_info["original"] = {
                    "path": original_path,
                    "exists": os.path.exists(original_path),
                    "size": os.path.getsize(original_path) if os.path.exists(original_path) else 0,
                    "last_modified": time.ctime(os.path.getmtime(original_path)) if os.path.exists(original_path) else "N/A"
                }
            
            # Verificar el video procesado
            if "processed_video_path" in status_data:
                processed_path = status_data["processed_video_path"]
                video_info["processed"] = {
                    "path": processed_path,
                    "exists": os.path.exists(processed_path),
                    "size": os.path.getsize(processed_path) if os.path.exists(processed_path) else 0,
                    "last_modified": time.ctime(os.path.getmtime(processed_path)) if os.path.exists(processed_path) else "N/A"
                }
            
            status_data["video_files_info"] = video_info
        
        return status_data

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
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Crear un archivo de video para guardar el resultado procesado en el directorio temporal del backend
        temp_dir = create_temp_directory()
        processed_video_filename = f"processed_{os.path.basename(video_path)}"
        processed_video_path = os.path.join(temp_dir, processed_video_filename)
        print(f"Guardando video procesado en: {processed_video_path}")
        
        # Asegurarse de que el codec sea compatible con el sistema
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Alternativas: 'avc1', 'H264', 'XVID'
        out = cv2.VideoWriter(processed_video_path, fourcc, fps, (width, height))
        
        # Verificar que el VideoWriter se haya inicializado correctamente
        if not out.isOpened():
            print(f"ERROR: No se pudo crear el VideoWriter para {processed_video_path}")
            # Intentar con un codec alternativo
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            processed_video_path = processed_video_path.replace('.mp4', '.avi')
            print(f"Intentando con codec XVID y ruta: {processed_video_path}")
            out = cv2.VideoWriter(processed_video_path, fourcc, fps, (width, height))
            
            # Actualizar la ruta del video procesado en el estado
            with video_job_status_lock:
                if job_id in video_job_status:
                    video_job_status[job_id]["processed_video_path"] = processed_video_path
                    # Guardar el estado actualizado
                    try:
                        with open('video_job_status.json', 'w') as f:
                            json.dump({k: v for k, v in video_job_status.items()}, f, indent=2)
                    except Exception as e:
                        print(f"Error al guardar estado actualizado: {e}")
        
        # Actualizar el estado con el total de frames y la ruta del video procesado
        if job_id in video_job_status:
            video_job_status[job_id]["total_frames"] = total_frames
            video_job_status[job_id]["processed_video_path"] = processed_video_path
        
        label_frames = {}
        frames_with_label = {}  # Seguimiento de frames donde aparece cada etiqueta
        label_first_appearance = {}  # Primer frame donde aparece cada etiqueta
        label_last_appearance = {}   # Último frame donde aparece cada etiqueta
        label_total_duration = {}    # Tiempo total de aparición por etiqueta
        frame_detection_density = []  # Densidad de detecciones por frame
        processing_times = []        # Tiempos de procesamiento por frame
        frame_idx = 0
        total_detections = 0
        
        # Procesar el video frame por frame
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_start_time = time.time()
            
            # Procesar el frame con YOLO
            results = model(frame)
            frame_detections = 0
            frame_labels = set()  # Etiquetas únicas en este frame
            
            # Dibujar las detecciones en el frame (solo confianza > 50%)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    cls = int(box.cls[0]) if hasattr(box, 'cls') else None
                    # Usar el nombre real de la etiqueta del modelo en lugar de "logo-brand"
                    label = model.names.get(cls, str(cls))
                    confidence = float(box.conf[0]) if hasattr(box, 'conf') else 0.0
                    
                    # Solo procesar detecciones con confianza superior al 50%
                    if label and confidence > 0.5:
                        # Guardar la etiqueta con su nombre real
                        label_frames[label] = label_frames.get(label, 0) + 1
                        
                        # Agregar el frame actual al conjunto de frames de esta etiqueta
                        if label not in frames_with_label:
                            frames_with_label[label] = set()
                        frames_with_label[label].add(frame_idx)
                        
                        # Registrar primera y última aparición
                        if label not in label_first_appearance:
                            label_first_appearance[label] = frame_idx
                        label_last_appearance[label] = frame_idx
                        
                        # Agregar etiqueta al conjunto de este frame
                        frame_labels.add(label)
                        
                        frame_detections += 1
                        
                        # Guardar la detección con timestamp para mostrarla en la interfaz
                        timestamp = frame_idx / fps if fps > 0 else 0
                        if "detections_list" not in video_job_status[job_id]:
                            video_job_status[job_id]["detections_list"] = []
                            
                        video_job_status[job_id]["detections_list"].append({
                            "timestamp": round(timestamp, 2),
                            "label": label,
                            "score": confidence,
                            "frame": frame_idx
                        })
                        
                        # Dibujar el bounding box y la etiqueta en el frame
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(frame, f"{label} {confidence:.2f}", (x1, y1 - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Escribir el frame procesado en el video de salida
            out.write(frame)
            
            # Calcular tiempo de procesamiento del frame
            frame_end_time = time.time()
            frame_processing_time = frame_end_time - frame_start_time
            processing_times.append(frame_processing_time)
            
            # Calcular densidad de detecciones del frame
            frame_density = frame_detections / max(len(frame_labels), 1) if frame_labels else 0
            frame_detection_density.append(frame_density)
            
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
        out.release()
        
        # Verificar que el video procesado se haya guardado correctamente
        if os.path.exists(processed_video_path):
            file_size = os.path.getsize(processed_video_path)
            print(f"Video procesado guardado correctamente en {processed_video_path} con tamaño {file_size} bytes")
            
            # Convertir el video a un formato compatible con navegadores web usando FFmpeg
            if file_size > 0:
                try:
                    # Crear un nombre para el video web-compatible
                    web_video_path = processed_video_path.replace('.mp4', '_web.mp4')
                    web_video_path = web_video_path.replace('.avi', '_web.mp4')
                    
                    # Verificar si FFmpeg está instalado
                    import subprocess
                    import shutil
                    import platform
                    
                    # Buscar FFmpeg en ubicaciones comunes según el sistema operativo
                    ffmpeg_path = shutil.which('ffmpeg')
                    
                    if ffmpeg_path is None:
                        if platform.system() == 'Windows':
                            # Ubicaciones comunes en Windows
                            common_locations = [
                                'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
                                'C:\\ffmpeg\\bin\\ffmpeg.exe',
                                os.path.join(os.environ.get('USERPROFILE', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'ffmpeg', 'bin', 'ffmpeg.exe'),
                                os.path.join(os.environ.get('APPDATA', ''), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                                # Buscar en el directorio actual y subdirectorios
                                os.path.join(os.getcwd(), 'ffmpeg.exe'),
                                os.path.join(os.getcwd(), 'bin', 'ffmpeg.exe'),
                                os.path.join(os.getcwd(), 'ffmpeg', 'bin', 'ffmpeg.exe'),
                                # Buscar en el directorio del proyecto
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ffmpeg.exe'),
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bin', 'ffmpeg.exe'),
                                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ffmpeg', 'bin', 'ffmpeg.exe')
                            ]
                        elif platform.system() == 'Linux':
                            # Ubicaciones comunes en Linux
                            common_locations = [
                                '/usr/bin/ffmpeg',
                                '/usr/local/bin/ffmpeg',
                                '/opt/ffmpeg/bin/ffmpeg',
                                os.path.join(os.path.expanduser('~'), 'bin', 'ffmpeg')
                            ]
                        elif platform.system() == 'Darwin':  # macOS
                            # Ubicaciones comunes en macOS
                            common_locations = [
                                '/usr/local/bin/ffmpeg',
                                '/opt/homebrew/bin/ffmpeg',
                                '/opt/local/bin/ffmpeg',
                                os.path.join(os.path.expanduser('~'), 'bin', 'ffmpeg')
                            ]
                        else:
                            common_locations = []
                        
                        for location in common_locations:
                            if os.path.exists(location):
                                ffmpeg_path = location
                                print(f"FFmpeg encontrado en: {ffmpeg_path}")
                                break
                    
                    if ffmpeg_path is None:
                        print("FFmpeg no encontrado en ninguna ubicación común. Buscando en PATH...")
                        # Intentar buscar en todas las carpetas del PATH
                        path_dirs = os.environ.get('PATH', '').split(os.pathsep)
                        for path_dir in path_dirs:
                            possible_path = os.path.join(path_dir, 'ffmpeg.exe' if platform.system() == 'Windows' else 'ffmpeg')
                            if os.path.isfile(possible_path):
                                ffmpeg_path = possible_path
                                print(f"FFmpeg encontrado en PATH: {ffmpeg_path}")
                                break
                    
                    if ffmpeg_path is None:
                        print("ADVERTENCIA: FFmpeg no encontrado. La conversión de video puede fallar.")
                        print("PATH actual:", os.environ.get('PATH', ''))
                    else:
                        print(f"Usando FFmpeg desde: {ffmpeg_path}")
                    
                    ffmpeg_available = ffmpeg_path is not None
                    
                    if not ffmpeg_available:
                        print("FFmpeg no está instalado o no está en el PATH. Intentando usar OpenCV para la conversión...")
                        try:
                            # Alternativa usando OpenCV para recodificar el video
                            cap = cv2.VideoCapture(processed_video_path)
                            fps = cap.get(cv2.CAP_PROP_FPS)
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            
                            # Intentar con diferentes codecs compatibles con navegadores
                            codecs_to_try = ['avc1', 'H264', 'X264', 'DIVX', 'XVID', 'mp4v']
                            out = None
                            
                            for codec in codecs_to_try:
                                try:
                                    print(f"Intentando con codec {codec}...")
                                    fourcc = cv2.VideoWriter_fourcc(*codec)
                                    # Asegurarse de que la extensión sea correcta según el codec
                                    if codec in ['XVID', 'DIVX']:
                                        if web_video_path.endswith('.mp4'):
                                            web_video_path = web_video_path.replace('.mp4', '.avi')
                                    else:
                                        if web_video_path.endswith('.avi'):
                                            web_video_path = web_video_path.replace('.avi', '.mp4')
                                            
                                    out = cv2.VideoWriter(web_video_path, fourcc, fps, (width, height))
                                    if out.isOpened():
                                        print(f"Codec {codec} funcionó correctamente")
                                        break
                                    else:
                                        print(f"No se pudo abrir el VideoWriter con codec {codec}")
                                        out.release()  # Liberar recursos antes de intentar otro codec
                                except Exception as e:
                                    print(f"Error con codec {codec}: {str(e)}")
                                    
                            if out is None or not out.isOpened():
                                print("No se pudo encontrar un codec compatible. Usando mp4v como último recurso")
                                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                                web_video_path = web_video_path.replace('.avi', '.mp4')
                                out = cv2.VideoWriter(web_video_path, fourcc, fps, (width, height))
                            
                            # Recodificar frame por frame
                            while cap.isOpened():
                                ret, frame = cap.read()
                                if not ret:
                                    break
                                out.write(frame)
                            
                            cap.release()
                            out.release()
                            print(f"Video recodificado con OpenCV: {web_video_path}")
                        except Exception as cv_error:
                            print(f"Error al recodificar con OpenCV: {str(cv_error)}")
                            # Si falla OpenCV, informamos que se necesita FFmpeg
                            print("Se requiere FFmpeg para la conversión de video. Por favor instálelo con:")
                            print("  - Windows: Descargar de https://ffmpeg.org/download.html")
                            print("  - Linux: sudo apt install ffmpeg")
                            print("  - macOS: brew install ffmpeg")
                    else:
                        # Comando FFmpeg para convertir a H.264 (compatible con navegadores)
                        print(f"Convirtiendo video a formato compatible con navegadores web usando FFmpeg...")
                        ffmpeg_cmd = [
                            ffmpeg_path if ffmpeg_path else 'ffmpeg',  # Usar la ruta completa si se encontró
                            '-i', processed_video_path,  # Archivo de entrada
                            '-c:v', 'libx264',          # Codec de video H.264
                            '-preset', 'veryfast',       # Preset de codificación rápida
                            '-crf', '23',               # Factor de calidad (23 es buen balance)
                            '-y',                        # Sobrescribir si existe
                            web_video_path               # Archivo de salida
                        ]
                        print(f"Ejecutando comando FFmpeg: {' '.join(ffmpeg_cmd)}")
                        # Mostrar información sobre la ruta de FFmpeg
                        print(f"Usando FFmpeg desde: {ffmpeg_path if ffmpeg_path else 'PATH del sistema'}")
                        # Verificar que el archivo de entrada existe
                        if not os.path.exists(processed_video_path):
                            print(f"ERROR: El archivo de entrada no existe: {processed_video_path}")
                        # Verificar que el directorio de salida existe
                        output_dir = os.path.dirname(web_video_path)
                        if not os.path.exists(output_dir):
                            print(f"Creando directorio de salida: {output_dir}")
                            os.makedirs(output_dir, exist_ok=True)
                        print(f"Ejecutando comando FFmpeg: {' '.join(ffmpeg_cmd)}")
                        # Mostrar información sobre la ruta de FFmpeg
                        print(f"Usando FFmpeg desde: {ffmpeg_path if ffmpeg_path else 'PATH del sistema'}")
                        # Verificar que el archivo de entrada existe
                        if not os.path.exists(processed_video_path):
                            print(f"ERROR: El archivo de entrada no existe: {processed_video_path}")
                        # Verificar que el directorio de salida existe
                        output_dir = os.path.dirname(web_video_path)
                        if not os.path.exists(output_dir):
                            print(f"Creando directorio de salida: {output_dir}")
                            os.makedirs(output_dir, exist_ok=True)
                        
                        # Ejecutar FFmpeg con manejo de errores mejorado
                        result = None
                        conversion_success = False
                        conversion_method = None
                        try:
                            print(f"Iniciando conversión con FFmpeg...")
                            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                            
                            # Mostrar salida de FFmpeg para diagnóstico
                            if result.stdout:
                                print(f"Salida de FFmpeg:\n{result.stdout}")
                            if result.stderr:
                                print(f"Mensajes de FFmpeg (stderr):\n{result.stderr}")
                                
                            # Verificar código de salida
                            if result.returncode != 0:
                                print(f"ERROR: FFmpeg falló con código de salida {result.returncode}")
                            else:
                                print(f"FFmpeg completó la conversión exitosamente")
                                if os.path.exists(web_video_path) and os.path.getsize(web_video_path) > 0:
                                    print(f"Archivo convertido creado correctamente: {web_video_path} (Tamaño: {os.path.getsize(web_video_path)} bytes)")
                                    conversion_success = True
                                    conversion_method = "ffmpeg"
                                else:
                                    print(f"ERROR: El archivo convertido no existe o está vacío: {web_video_path}")
                        except Exception as e:
                            print(f"ERROR al ejecutar FFmpeg: {str(e)}")
                            result = None
                    
                    # Verificar si la conversión fue exitosa (para ambos métodos: FFmpeg y OpenCV)
                    if os.path.exists(web_video_path) and os.path.getsize(web_video_path) > 0:
                        print(f"Video convertido exitosamente a formato web: {web_video_path}")
                        print(f"Tamaño del video convertido: {os.path.getsize(web_video_path)} bytes")
                        
                        # Verificar el directorio temporal
                        temp_dir = os.path.dirname(web_video_path)
                        print(f"Verificando directorio temporal: {temp_dir}")
                        if not os.path.exists(temp_dir):
                            print(f"El directorio temporal no existe, creándolo: {temp_dir}")
                            os.makedirs(temp_dir, exist_ok=True)
                        else:
                            print(f"Directorio temporal existe. Contenido:")
                            for file in os.listdir(temp_dir):
                                file_path = os.path.join(temp_dir, file)
                                file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else "<directorio>"
                                print(f"  - {file}: {file_size} bytes")
                        
                        # Actualizar la ruta del video procesado en el estado
                        processed_video_path = web_video_path
                        with video_job_status_lock:
                            if job_id in video_job_status:
                                video_job_status[job_id]["processed_video_path"] = web_video_path
                                # Añadir información sobre el método de conversión usado
                                video_job_status[job_id]["conversion_method"] = "ffmpeg" if ffmpeg_available else "opencv"
                                # Añadir información sobre el codec utilizado
                                video_job_status[job_id]["video_codec"] = "h264" if ffmpeg_available else "variable"
                                # Guardar el estado actualizado
                                try:
                                    with open('video_job_status.json', 'w') as f:
                                        json.dump({k: v for k, v in video_job_status.items()}, f, indent=2)
                                except Exception as e:
                                    print(f"Error al guardar estado después de la conversión: {e}")
                    else:
                        print(f"ERROR: La conversión de video falló. Usando el video original.")
                        if ffmpeg_available and result is not None:
                            if hasattr(result, 'stdout') and result.stdout:
                                print(f"Salida de FFmpeg: {result.stdout}")
                            if hasattr(result, 'stderr') and result.stderr:
                                print(f"Error de FFmpeg: {result.stderr}")
                        
                        # Verificar si el directorio temporal existe
                        if not os.path.exists(temp_dir):
                            print(f"ERROR: El directorio temporal no existe: {temp_dir}")
                            try:
                                os.makedirs(temp_dir, exist_ok=True)
                                print(f"Directorio temporal creado: {temp_dir}")
                            except Exception as e:
                                print(f"ERROR al crear directorio temporal: {str(e)}")
                        
                        # Listar archivos en el directorio temporal para diagnóstico
                        try:
                            print(f"Contenido del directorio temporal {temp_dir}:")
                            for file in os.listdir(temp_dir):
                                file_path = os.path.join(temp_dir, file)
                                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                                print(f"  - {file}: {file_size} bytes")
                        except Exception as e:
                            print(f"ERROR al listar directorio temporal: {str(e)}")
                except Exception as e:
                    print(f"ERROR al convertir video: {str(e)}")
                    print("El video procesado puede no ser compatible con todos los navegadores.")
                    print("Se recomienda instalar FFmpeg para una mejor compatibilidad web.")
            
            if file_size == 0:
                print(f"ADVERTENCIA: El archivo de video procesado tiene tamaño cero: {processed_video_path}")
        else:
            print(f"ERROR: No se encontró el archivo de video procesado: {processed_video_path}")
        
        # Calcular tiempo de procesamiento
        end_time = time.time()
        processed_secs = end_time - start_time
        
        # Calcular métricas avanzadas
        avg_processing_time_per_frame = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing_time_per_frame = max(processing_times) if processing_times else 0
        min_processing_time_per_frame = min(processing_times) if processing_times else 0
        
        avg_detection_density = sum(frame_detection_density) / len(frame_detection_density) if frame_detection_density else 0
        max_detection_density = max(frame_detection_density) if frame_detection_density else 0
        
        # Calcular duración total de aparición por etiqueta
        for label in label_frames.keys():
            if label in label_first_appearance and label in label_last_appearance:
                duration_frames = label_last_appearance[label] - label_first_appearance[label] + 1
                label_total_duration[label] = duration_frames / fps if fps > 0 else 0
        
        # Generar resumen de detecciones
        from ..services.yolo_service import summarize_counts
        detections_summary = summarize_counts(label_frames, frame_idx, frames_with_label, fps)
        
        # Agregar métricas avanzadas al resumen
        for label in detections_summary.keys():
            if label in label_total_duration:
                detections_summary[label]['total_duration_seconds'] = label_total_duration[label]
            if label in label_first_appearance:
                detections_summary[label]['first_appearance_frame'] = label_first_appearance[label]
                detections_summary[label]['first_appearance_time'] = label_first_appearance[label] / fps if fps > 0 else 0
            if label in label_last_appearance:
                detections_summary[label]['last_appearance_frame'] = label_last_appearance[label]
                detections_summary[label]['last_appearance_time'] = label_last_appearance[label] / fps if fps > 0 else 0
        
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
                    "progress": 100,
                    # Métricas avanzadas
                    "advanced_metrics": {
                        "avg_processing_time_per_frame": avg_processing_time_per_frame,
                        "max_processing_time_per_frame": max_processing_time_per_frame,
                        "min_processing_time_per_frame": min_processing_time_per_frame,
                        "avg_detection_density": avg_detection_density,
                        "max_detection_density": max_detection_density,
                        "total_processing_speed_fps": frame_idx / processed_secs if processed_secs > 0 else 0,
                        "detection_efficiency": total_detections / frame_idx if frame_idx > 0 else 0,
                        "video_duration_seconds": frame_idx / fps if fps > 0 else 0,
                        "processing_speed_ratio": (frame_idx / fps) / processed_secs if processed_secs > 0 and fps > 0 else 0
                    },
                    "label_durations": label_total_duration
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

                # Guardar en base de datos
                try:
                    from ..main import persist_results
                    # Adaptar detections_summary para persist_results
                    detections_for_db = {}
                    for label, info in detections_summary.items():
                        detections_for_db[label] = {
                            "frames": info.get("qty_frames_detected", 0),
                            "fps": info.get("frame_per_second", 0.0),
                            "percentage": info.get("frames_appearance_in_percentage", 0.0)
                        }
                    id_video = persist_results(
                        vtype="mp4",
                        name=filename,
                        fps=fps,
                        total_secs=processed_secs,
                        summary=detections_for_db
                    )
                    print(f"[BD] Video guardado en la base de datos con id_video={id_video}")
                except Exception as e:
                    print(f"[BD] Error al guardar en la base de datos: {e}")
        
        # Limpiar los archivos temporales
        try:
            # No eliminamos los archivos inmediatamente para permitir su visualización
            # Se podría implementar un sistema de limpieza periódica para eliminar archivos antiguos
            print(f"Archivos temporales disponibles en: {os.path.dirname(video_path)}")
        except Exception as e:
            print(f"Error al gestionar archivos temporales: {e}")
    
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