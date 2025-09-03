from typing import Dict, List, Any, Optional, Callable, Generator
import cv2
import numpy as np
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass

from .base_detection_service import BaseDetectionService
from backend.core.logging import get_logger
from backend.core.exceptions import DetectionError, ValidationError

logger = get_logger(__name__)

@dataclass
class StreamingMetrics:
    """Métricas para streaming en tiempo real"""
    fps: float = 0.0
    total_frames: int = 0
    processed_frames: int = 0
    dropped_frames: int = 0
    avg_processing_time: float = 0.0
    label_times: Dict[str, float] = None
    label_frames: Dict[str, int] = None
    
    def __post_init__(self):
        if self.label_times is None:
            self.label_times = defaultdict(float)
        if self.label_frames is None:
            self.label_frames = defaultdict(int)

class StreamingDetectionService(BaseDetectionService):
    """
    Servicio especializado para detección en streaming en tiempo real.
    Optimizado para baja latencia y procesamiento continuo.
    """
    
    def __init__(self, model_path: str = None):
        super().__init__(model_path)
        
        # Control de streaming
        self._is_streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._stop_streaming = False
        
        # Fuente de video
        self._cap: Optional[cv2.VideoCapture] = None
        self._source = None
        
        # Métricas y estadísticas
        self.metrics = StreamingMetrics()
        self._processing_times = deque(maxlen=100)  # Últimos 100 tiempos de procesamiento
        
        # Configuración de rendimiento
        self.frame_skip = 1  # Procesar cada N frames
        self.max_fps = 30    # FPS máximo de procesamiento
        self.buffer_size = 5 # Tamaño del buffer de frames
        
        # Callbacks
        self._frame_callback: Optional[Callable] = None
        self._detection_callback: Optional[Callable] = None
        self._stats_callback: Optional[Callable] = None
        
        # Buffer de frames para procesamiento asíncrono
        self._frame_buffer = deque(maxlen=self.buffer_size)
        self._buffer_lock = threading.Lock()
        
        # Seguimiento temporal
        self._start_time = None
        self._last_frame_time = None
        self._current_labels = set()
    
    def start_streaming(self, source: Any, **kwargs) -> Dict[str, Any]:
        """
        Inicia el streaming de detección en tiempo real.
        
        Args:
            source: Fuente del stream (int para cámara, str para archivo/URL)
            **kwargs: Configuración del streaming:
                - frame_skip: int - Procesar cada N frames (default: 1)
                - max_fps: int - FPS máximo de procesamiento (default: 30)
                - confidence_threshold: float - Umbral de confianza (default: 0.5)
                - show_display: bool - Mostrar ventana de visualización (default: False)
                - frame_callback: Callable - Callback para cada frame procesado
                - detection_callback: Callable - Callback para detecciones
                - stats_callback: Callable - Callback para estadísticas
        
        Returns:
            Información del streaming iniciado
        """
        try:
            if self._is_streaming:
                raise DetectionError("Ya hay un streaming activo")
            
            # Configuración
            self.frame_skip = kwargs.get('frame_skip', 1)
            self.max_fps = kwargs.get('max_fps', 30)
            self._frame_callback = kwargs.get('frame_callback')
            self._detection_callback = kwargs.get('detection_callback')
            self._stats_callback = kwargs.get('stats_callback')
            
            # Abrir fuente de video
            self._source = source
            self._cap = cv2.VideoCapture(source)
            
            if not self._cap.isOpened():
                raise ValidationError(f"No se pudo abrir la fuente: {source}")
            
            # Configurar cámara para mejor rendimiento
            if isinstance(source, int):
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self._cap.set(cv2.CAP_PROP_FPS, self.max_fps)
            
            # Obtener información de la fuente
            self.metrics.fps = self._cap.get(cv2.CAP_PROP_FPS)
            width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Inicializar métricas
            self._start_time = time.time()
            self._last_frame_time = self._start_time
            self.metrics = StreamingMetrics(fps=self.metrics.fps)
            
            # Iniciar hilo de streaming
            self._is_streaming = True
            self._stop_streaming = False
            self._stream_thread = threading.Thread(
                target=self._streaming_loop,
                args=(kwargs,),
                daemon=True
            )
            self._stream_thread.start()
            
            logger.info(f"Streaming iniciado: {width}x{height} @ {self.metrics.fps} FPS")
            
            return {
                "status": "streaming_started",
                "source": source,
                "resolution": {"width": width, "height": height},
                "fps": self.metrics.fps,
                "thread_id": self._stream_thread.ident
            }
            
        except Exception as e:
            logger.error(f"Error iniciando streaming: {e}")
            self._cleanup_streaming()
            raise DetectionError(f"No se pudo iniciar streaming: {str(e)}")
    
    def _streaming_loop(self, kwargs: Dict) -> None:
        """
        Bucle principal del streaming.
        
        Args:
            kwargs: Configuración del streaming
        """
        confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        show_display = kwargs.get('show_display', False)
        
        frame_interval = 1.0 / self.max_fps if self.max_fps > 0 else 0
        frame_count = 0
        
        try:
            while self._is_streaming and not self._stop_streaming:
                start_time = time.time()
                
                # Leer frame
                ret, frame = self._cap.read()
                if not ret:
                    logger.warning("No se pudo leer frame, finalizando streaming")
                    break
                
                frame_count += 1
                self.metrics.total_frames = frame_count
                
                # Saltar frames si es necesario
                if frame_count % self.frame_skip != 0:
                    self.metrics.dropped_frames += 1
                    continue
                
                # Procesar frame
                try:
                    detections = self._process_frame(frame, confidence_threshold)
                    self.metrics.processed_frames += 1
                    
                    # Actualizar métricas temporales
                    self._update_temporal_metrics(detections)
                    
                    # Callbacks
                    if self._detection_callback and detections:
                        self._detection_callback(detections)
                    
                    if self._frame_callback:
                        annotated_frame = self._annotate_frame(frame, detections)
                        self._frame_callback(annotated_frame, detections)
                    
                    # Mostrar display si se solicita
                    if show_display:
                        self._show_display(frame, detections)
                    
                except Exception as e:
                    logger.error(f"Error procesando frame {frame_count}: {e}")
                    continue
                
                # Calcular tiempo de procesamiento
                processing_time = time.time() - start_time
                self._processing_times.append(processing_time)
                self.metrics.avg_processing_time = np.mean(self._processing_times)
                
                # Callback de estadísticas (cada 30 frames)
                if self._stats_callback and frame_count % 30 == 0:
                    self._stats_callback(self.get_streaming_stats())
                
                # Control de FPS
                elapsed = time.time() - start_time
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
            
        except Exception as e:
            logger.error(f"Error en bucle de streaming: {e}")
        
        finally:
            self._cleanup_streaming()
            logger.info("Streaming finalizado")
    
    def _process_frame(self, frame: np.ndarray, confidence_threshold: float) -> List[Dict[str, Any]]:
        """
        Procesa un frame individual.
        
        Args:
            frame: Frame a procesar
            confidence_threshold: Umbral de confianza
            
        Returns:
            Lista de detecciones
        """
        # Realizar detección
        results = self.model(frame, verbose=False)
        detections = self._extract_detections(results)
        
        # Filtrar por confianza
        filtered_detections = [
            det for det in detections 
            if det['confidence'] >= confidence_threshold
        ]
        
        return filtered_detections
    
    def _update_temporal_metrics(self, detections: List[Dict]) -> None:
        """
        Actualiza métricas temporales de las detecciones.
        
        Args:
            detections: Lista de detecciones del frame actual
        """
        current_time = time.time()
        elapsed_time = current_time - self._last_frame_time
        self._last_frame_time = current_time
        
        # Obtener etiquetas del frame actual
        current_labels = {det['label'] for det in detections}
        
        # Actualizar tiempo y frames para etiquetas detectadas
        for label in current_labels:
            self.metrics.label_times[label] += elapsed_time
            self.metrics.label_frames[label] += 1
        
        self._current_labels = current_labels
    
    def _show_display(self, frame: np.ndarray, detections: List[Dict]) -> None:
        """
        Muestra el frame con detecciones en una ventana.
        
        Args:
            frame: Frame original
            detections: Lista de detecciones
        """
        # Anotar frame
        annotated_frame = self._annotate_frame(frame, detections)
        
        # Agregar información de estadísticas
        self._add_stats_overlay(annotated_frame)
        
        # Mostrar frame
        cv2.imshow("YOLO Streaming Detection", annotated_frame)
        
        # Salir con ESC
        if cv2.waitKey(1) & 0xFF == 27:
            self.stop_streaming()
    
    def _add_stats_overlay(self, frame: np.ndarray) -> None:
        """
        Agrega overlay de estadísticas al frame.
        
        Args:
            frame: Frame a anotar
        """
        y_pos = 30
        
        # Información general
        fps_text = f"FPS: {self.metrics.fps:.1f} | Processed: {self.metrics.processed_frames}"
        cv2.putText(frame, fps_text, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y_pos += 25
        
        # Tiempo de procesamiento
        proc_time_text = f"Proc Time: {self.metrics.avg_processing_time*1000:.1f}ms"
        cv2.putText(frame, proc_time_text, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        y_pos += 25
        
        # Estadísticas de etiquetas (top 5)
        sorted_labels = sorted(
            self.metrics.label_frames.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:5]
        
        for label, frames in sorted_labels:
            total_time = self.metrics.label_times[label]
            text = f"{label}: {frames} frames ({total_time:.1f}s)"
            cv2.putText(frame, text, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y_pos += 20
    
    def stop_streaming(self) -> bool:
        """
        Detiene el streaming.
        
        Returns:
            True si se detuvo correctamente
        """
        if not self._is_streaming:
            return False
        
        logger.info("Deteniendo streaming...")
        self._stop_streaming = True
        
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=5.0)
        
        self._cleanup_streaming()
        return True
    
    def _cleanup_streaming(self) -> None:
        """
        Limpia recursos del streaming.
        """
        self._is_streaming = False
        
        if self._cap:
            self._cap.release()
            self._cap = None
        
        cv2.destroyAllWindows()
        
        logger.info("Recursos de streaming liberados")
    
    def get_streaming_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas actuales del streaming.
        
        Returns:
            Estadísticas del streaming
        """
        total_time = time.time() - self._start_time if self._start_time else 0
        
        # Calcular porcentajes de aparición
        label_percentages = {}
        if self.metrics.processed_frames > 0:
            for label, frames in self.metrics.label_frames.items():
                percentage = (frames / self.metrics.processed_frames) * 100
                label_percentages[label] = {
                    "frames": frames,
                    "percentage": percentage,
                    "total_time": self.metrics.label_times[label]
                }
        
        return {
            "is_streaming": self._is_streaming,
            "source": self._source,
            "total_time": total_time,
            "fps": self.metrics.fps,
            "frames": {
                "total": self.metrics.total_frames,
                "processed": self.metrics.processed_frames,
                "dropped": self.metrics.dropped_frames
            },
            "performance": {
                "avg_processing_time_ms": self.metrics.avg_processing_time * 1000,
                "processing_fps": 1.0 / self.metrics.avg_processing_time if self.metrics.avg_processing_time > 0 else 0
            },
            "detections": label_percentages,
            "current_labels": list(self._current_labels)
        }
    
    def is_streaming(self) -> bool:
        """
        Verifica si el streaming está activo.
        
        Returns:
            True si está streaming
        """
        return self._is_streaming
    
    def get_frame_generator(self, source: Any, **kwargs) -> Generator[tuple, None, None]:
        """
        Generador de frames con detecciones para uso en APIs.
        
        Args:
            source: Fuente del video
            **kwargs: Configuración del procesamiento
            
        Yields:
            Tupla (frame_anotado, detecciones)
        """
        confidence_threshold = kwargs.get('confidence_threshold', 0.5)
        
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise ValidationError(f"No se pudo abrir la fuente: {source}")
        
        try:
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Saltar frames si es necesario
                if frame_count % self.frame_skip != 0:
                    continue
                
                # Procesar frame
                detections = self._process_frame(frame, confidence_threshold)
                annotated_frame = self._annotate_frame(frame, detections)
                
                yield annotated_frame, detections
                
        finally:
            cap.release()
    
    def process(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        Implementación del método abstracto para compatibilidad.
        Redirige al método start_streaming.
        
        Args:
            input_data: Fuente del stream
            **kwargs: Argumentos de configuración
            
        Returns:
            Resultado del streaming
        """
        return self.start_streaming(input_data, **kwargs)
    
    def cleanup(self) -> None:
        """
        Limpia todos los recursos del servicio.
        """
        self.stop_streaming()
        super().cleanup()