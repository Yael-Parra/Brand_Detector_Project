from typing import Dict, List, Any, Union, Callable, Optional
import cv2
import numpy as np
import threading
import time
import os
from pathlib import Path
from fastapi import UploadFile
from dataclasses import dataclass

from .base_detection_service import BaseDetectionService
from backend.core.logging import get_logger
from backend.core.exceptions import DetectionError, ValidationError
from backend.utils.file_validation import validate_video_file
from backend.database import db_insertion_data as db

logger = get_logger(__name__)

@dataclass
class VideoMetrics:
    """Clase para almacenar métricas del video"""
    fps: float = 0.0
    total_frames: int = 0
    duration_secs: float = 0.0
    processed_frames: int = 0
    detections: Dict[str, int] = None
    frames_with_label: Dict[str, set] = None  # Frames donde aparece cada etiqueta
    
    def __post_init__(self):
        if self.detections is None:
            self.detections = {}
        if self.frames_with_label is None:
            self.frames_with_label = {}

@dataclass
class ProcessingStatus:
    """Clase para el estado del procesamiento"""
    is_running: bool = False
    is_paused: bool = False
    progress_percent: float = 0.0
    current_frame: int = 0
    error_message: Optional[str] = None

class VideoDetectionService(BaseDetectionService):
    """
    Servicio especializado para detección en videos.
    Soporta procesamiento en tiempo real, por lotes y con control de flujo.
    """
    
    def __init__(self, model_path: str = None):
        super().__init__(model_path)
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
        
        # Control de procesamiento
        self._processing_thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._pause_requested = False
        
        # Métricas y estado
        self.metrics = VideoMetrics()
        self.status = ProcessingStatus()
        
        # Callbacks
        self._progress_callback: Optional[Callable] = None
        self._completion_callback: Optional[Callable] = None
        
        # Video capture
        self._cap: Optional[cv2.VideoCapture] = None
        self._video_path: Optional[str] = None
    
    def process(self, input_data: Union[str, UploadFile, int], **kwargs) -> Dict[str, Any]:
        """
        Procesa un video para detectar objetos.
        
        Args:
            input_data: Puede ser:
                - str: Ruta al video o URL
                - UploadFile: Archivo de video subido
                - int: Índice de cámara (0 para cámara por defecto)
            **kwargs: Argumentos adicionales:
                - async_processing: bool - Procesamiento asíncrono (default: False)
                - frame_skip: int - Saltar frames para acelerar (default: 1)
                - confidence_threshold: float - Umbral de confianza (default: 0.5)
                - save_to_db: bool - Guardar en base de datos (default: False)
                - progress_callback: Callable - Callback de progreso
                - completion_callback: Callable - Callback de finalización
        
        Returns:
            Diccionario con resultados del procesamiento
        """
        try:
            # Configuración
            async_processing = kwargs.get('async_processing', False)
            self._progress_callback = kwargs.get('progress_callback')
            self._completion_callback = kwargs.get('completion_callback')
            
            # Preparar video
            self._prepare_video(input_data)
            
            if async_processing:
                return self._start_async_processing(**kwargs)
            else:
                return self._process_video_sync(**kwargs)
                
        except Exception as e:
            logger.error(f"Error en procesamiento de video: {e}")
            raise DetectionError(f"Error procesando video: {str(e)}")
    
    def _prepare_video(self, input_data: Union[str, UploadFile, int]) -> None:
        """
        Prepara el video para procesamiento.
        
        Args:
            input_data: Fuente del video
        """
        if isinstance(input_data, str):
            # Archivo local o URL
            if input_data.startswith(('http://', 'https://')):
                # URL - se maneja directamente por OpenCV
                self._video_path = input_data
            else:
                # Archivo local
                if not Path(input_data).exists():
                    raise ValidationError(f"Archivo no encontrado: {input_data}")
                self._video_path = input_data
                
        elif isinstance(input_data, UploadFile):
            # Archivo subido
            validation_result = validate_video_file(input_data)
            if not validation_result["valid"]:
                raise ValidationError(f"Archivo inválido: {validation_result['error']}")
            
            # Guardar temporalmente
            temp_path = Path("data/uploads") / f"temp_{int(time.time())}_{input_data.filename}"
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(temp_path, "wb") as buffer:
                content = input_data.file.read()
                buffer.write(content)
            
            self._video_path = str(temp_path)
            
        elif isinstance(input_data, int):
            # Cámara
            self._video_path = input_data
        else:
            raise ValidationError(f"Tipo de entrada no soportado: {type(input_data)}")
        
        # Abrir video
        self._cap = cv2.VideoCapture(self._video_path)
        if not self._cap.isOpened():
            raise ValidationError(f"No se pudo abrir el video: {self._video_path}")
        
        # Obtener métricas del video
        self.metrics.fps = self._cap.get(cv2.CAP_PROP_FPS)
        self.metrics.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.metrics.duration_secs = (
            self.metrics.total_frames / self.metrics.fps 
            if self.metrics.fps > 0 else 0
        )
        
        logger.info(f"Video preparado: {self.metrics.total_frames} frames, {self.metrics.fps} FPS")
    
    def _start_async_processing(self, **kwargs) -> Dict[str, Any]:
        """
        Inicia el procesamiento asíncrono del video.
        
        Returns:
            Información del procesamiento iniciado
        """
        if self.status.is_running:
            raise DetectionError("Ya hay un procesamiento en curso")
        
        self._stop_requested = False
        self._pause_requested = False
        self.status.is_running = True
        
        self._processing_thread = threading.Thread(
            target=self._process_video_async,
            args=(kwargs,),
            daemon=True
        )
        self._processing_thread.start()
        
        return {
            "status": "processing_started",
            "video_info": {
                "fps": self.metrics.fps,
                "total_frames": self.metrics.total_frames,
                "duration_secs": self.metrics.duration_secs
            },
            "thread_id": self._processing_thread.ident
        }
    
    def _process_video_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Procesa el video de forma síncrona.
        
        Returns:
            Resultados completos del procesamiento
        """
        frame_skip = kwargs.get('frame_skip', 1)
        confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        save_to_db = kwargs.get('save_to_db', False)
        
        detections_by_frame = []
        frame_count = 0
        
        logger.info("Iniciando procesamiento síncrono de video")
        
        try:
            while self._cap.isOpened():
                ret, frame = self._cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Saltar frames si es necesario
                if frame_count % frame_skip != 0:
                    continue
                
                # Procesar frame
                results = self.model(frame, verbose=False)
                detections = self._extract_detections(results)
                
                # Filtrar por confianza (solo detecciones > 50%)
                filtered_detections = [
                    det for det in detections 
                    if det['confidence'] > 0.5  # Solo detecciones superiores al 50%
                ]
                
                # Actualizar métricas
                frame_labels = set()
                for detection in filtered_detections:
                    label = detection['label']
                    self.metrics.detections[label] = self.metrics.detections.get(label, 0) + 1
                    frame_labels.add(label)
                
                # Registrar frames donde aparece cada etiqueta
                for label in frame_labels:
                    if label not in self.metrics.frames_with_label:
                        self.metrics.frames_with_label[label] = set()
                    self.metrics.frames_with_label[label].add(frame_count)
                
                detections_by_frame.append({
                    "frame_number": frame_count,
                    "detections": filtered_detections
                })
                
                # Callback de progreso
                if self._progress_callback:
                    progress = frame_count / self.metrics.total_frames * 100
                    self._progress_callback({
                        "frame_count": frame_count,
                        "progress": progress,
                        "current_detections": self.metrics.detections.copy()
                    })
            
            # Guardar en BD si se solicita
            if save_to_db:
                self._save_to_database()
            
            # Preparar respuesta
            response = {
                "status": "completed",
                "video_info": {
                    "fps": self.metrics.fps,
                    "total_frames": self.metrics.total_frames,
                    "processed_frames": frame_count,
                    "duration_secs": self.metrics.duration_secs
                },
                "detection_summary": self._calculate_detection_summary(),
                "detections_by_frame": detections_by_frame if len(detections_by_frame) <= 100 else [],
                "processing_info": {
                    "model_path": self.model_path,
                    "confidence_threshold": confidence_threshold,
                    "frame_skip": frame_skip
                }
            }
            
            logger.info(f"Procesamiento completado: {frame_count} frames procesados")
            return response
            
        finally:
            self._cleanup_video()
    
    def _process_video_async(self, kwargs: Dict) -> None:
        """
        Procesa el video de forma asíncrona.
        
        Args:
            kwargs: Argumentos de procesamiento
        """
        try:
            result = self._process_video_sync(**kwargs)
            
            if self._completion_callback:
                self._completion_callback(result)
                
        except Exception as e:
            logger.error(f"Error en procesamiento asíncrono: {e}")
            self.status.error_message = str(e)
            
            if self._completion_callback:
                self._completion_callback({"status": "error", "error": str(e)})
        
        finally:
            self.status.is_running = False
    
    def _calculate_detection_summary(self) -> Dict[str, Any]:
        """
        Calcula resumen de detecciones.
        
        Returns:
            Resumen de detecciones
        """
        total_detections = sum(self.metrics.detections.values())
        
        summary = {
            "total_detections": total_detections,
            "unique_labels": len(self.metrics.detections),
            "detections_by_label": {}
        }
        
        for label, count in self.metrics.detections.items():
            # Calcular porcentaje de frames donde aparece la etiqueta
            frames_with_label = len(self.metrics.frames_with_label.get(label, set()))
            percentage_of_frames = (frames_with_label / self.metrics.processed_frames * 100) if self.metrics.processed_frames > 0 else 0
            
            # Calcular porcentaje de tiempo basado en duración del video
            time_percentage = (frames_with_label / self.metrics.total_frames * 100) if self.metrics.total_frames > 0 else 0
            
            summary["detections_by_label"][label] = {
                "count": count,
                "percentage_of_frames": percentage_of_frames,
                "percentage_of_video_time": round(time_percentage, 2)
            }
        
        return summary
    
    def _save_to_database(self) -> None:
        """
        Guarda los resultados en la base de datos.
        """
        try:
            conn = db.connect()
            
            # Insertar video
            video_name = os.path.basename(self._video_path) if isinstance(self._video_path, str) else "camera_feed"
            id_video = db.insert_video(
                conn,
                vtype="file" if isinstance(self._video_path, str) else "camera",
                name=video_name,
                total_secs=self.metrics.duration_secs
            )
            
            # Insertar detecciones
            for label, count in self.metrics.detections.items():
                percentage = (count / self.metrics.total_frames * 100) if self.metrics.total_frames > 0 else 0
                db.insert_detection(
                    conn,
                    id_video=id_video,
                    label_name=label,
                    qty_frames_detected=count,
                    fps=self.metrics.fps,
                    percent=percentage
                )
            
            logger.info(f"Resultados guardados en BD con video_id={id_video}")
            
        except Exception as e:
            logger.error(f"Error guardando en BD: {e}")
        finally:
            if 'conn' in locals():
                db.disconnect(conn)
    
    def pause(self) -> bool:
        """
        Pausa el procesamiento asíncrono.
        
        Returns:
            True si se pausó correctamente
        """
        if self.status.is_running and not self.status.is_paused:
            self._pause_requested = True
            self.status.is_paused = True
            logger.info("Procesamiento pausado")
            return True
        return False
    
    def resume(self) -> bool:
        """
        Reanuda el procesamiento pausado.
        
        Returns:
            True si se reanudó correctamente
        """
        if self.status.is_running and self.status.is_paused:
            self._pause_requested = False
            self.status.is_paused = False
            logger.info("Procesamiento reanudado")
            return True
        return False
    
    def stop(self) -> bool:
        """
        Detiene el procesamiento asíncrono.
        
        Returns:
            True si se detuvo correctamente
        """
        if self.status.is_running:
            self._stop_requested = True
            
            if self._processing_thread and self._processing_thread.is_alive():
                self._processing_thread.join(timeout=5.0)
            
            self.status.is_running = False
            self.status.is_paused = False
            logger.info("Procesamiento detenido")
            return True
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual del procesamiento.
        
        Returns:
            Estado del procesamiento
        """
        return {
            "is_running": self.status.is_running,
            "is_paused": self.status.is_paused,
            "progress_percent": self.status.progress_percent,
            "current_frame": self.status.current_frame,
            "error_message": self.status.error_message,
            "metrics": {
                "fps": self.metrics.fps,
                "total_frames": self.metrics.total_frames,
                "processed_frames": self.metrics.processed_frames,
                "duration_secs": self.metrics.duration_secs,
                "detections": self.metrics.detections.copy()
            }
        }
    
    def _cleanup_video(self) -> None:
        """
        Limpia recursos del video.
        """
        if self._cap:
            self._cap.release()
            self._cap = None
        
        # Eliminar archivo temporal si existe
        if (self._video_path and 
            isinstance(self._video_path, str) and 
            "temp_" in self._video_path and 
            Path(self._video_path).exists()):
            try:
                os.remove(self._video_path)
                logger.info(f"Archivo temporal eliminado: {self._video_path}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal: {e}")
    
    def cleanup(self) -> None:
        """
        Limpia todos los recursos del servicio.
        """
        self.stop()
        self._cleanup_video()
        super().cleanup()
    
    def get_supported_formats(self) -> List[str]:
        """
        Obtiene los formatos de video soportados.
        
        Returns:
            Lista de extensiones soportadas
        """
        return self.supported_formats.copy()