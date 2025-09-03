from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from ultralytics import YOLO
import cv2
import numpy as np
from pathlib import Path
from backend.config.settings import get_settings
from backend.core.logging import get_logger
from backend.core.exceptions import DetectionError, ModelLoadError

settings = get_settings()
logger = get_logger(__name__)

class BaseDetectionService(ABC):
    """
    Clase base abstracta para todos los servicios de detección.
    Proporciona funcionalidad común y define la interfaz para servicios específicos.
    """
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or settings.model_path or "best_v5.pt"
        self._model = None
        self._is_initialized = False
        
    @property
    def model(self) -> YOLO:
        """Lazy loading del modelo YOLO"""
        if self._model is None:
            self._load_model()
        return self._model
    
    def _load_model(self) -> None:
        """Carga el modelo YOLO"""
        try:
            logger.info(f"Cargando modelo YOLO desde: {self.model_path}")
            self._model = YOLO(self.model_path)
            self._is_initialized = True
            logger.info("Modelo YOLO cargado exitosamente")
        except Exception as e:
            logger.error(f"Error al cargar modelo YOLO: {e}")
            raise ModelLoadError(f"No se pudo cargar el modelo: {e}")
    
    def _extract_detections(self, results) -> List[Dict[str, Any]]:
        """
        Extrae las detecciones de los resultados de YOLO en un formato estándar.
        
        Args:
            results: Resultados de la inferencia de YOLO
            
        Returns:
            Lista de detecciones con formato estándar
        """
        detections = []
        
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes
                for i in range(len(boxes)):
                    # Coordenadas de la caja
                    xyxy = boxes.xyxy[i].cpu().numpy()
                    x1, y1, x2, y2 = map(int, xyxy)
                    
                    # Confianza
                    confidence = float(boxes.conf[i].cpu().numpy())
                    
                    # Clase
                    cls_id = int(boxes.cls[i].cpu().numpy())
                    label = self.model.names[cls_id]
                    
                    detection = {
                        "bbox_xyxy": [x1, y1, x2, y2],
                        "bbox_xywh": [x1, y1, x2-x1, y2-y1],
                        "confidence": confidence,
                        "class_id": cls_id,
                        "label": label
                    }
                    detections.append(detection)
        
        return detections
    
    def _annotate_frame(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """
        Anota un frame con las detecciones.
        
        Args:
            frame: Frame a anotar
            detections: Lista de detecciones
            
        Returns:
            Frame anotado
        """
        annotated_frame = frame.copy()
        
        for detection in detections:
            x1, y1, x2, y2 = detection["bbox_xyxy"]
            label = detection["label"]
            confidence = detection["confidence"]
            
            # Dibujar rectángulo
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Dibujar etiqueta
            label_text = f"{label}: {confidence:.2f}"
            label_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(annotated_frame, label_text, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return annotated_frame
    
    def _validate_input(self, input_data: Any) -> bool:
        """
        Valida los datos de entrada.
        
        Args:
            input_data: Datos a validar
            
        Returns:
            True si los datos son válidos
        """
        return input_data is not None
    
    @abstractmethod
    def process(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        Método abstracto para procesar datos de entrada.
        
        Args:
            input_data: Datos a procesar
            **kwargs: Argumentos adicionales
            
        Returns:
            Resultados del procesamiento
        """
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Obtiene información del modelo cargado.
        
        Returns:
            Información del modelo
        """
        if not self._is_initialized:
            return {"status": "not_initialized", "model_path": self.model_path}
        
        return {
            "status": "initialized",
            "model_path": self.model_path,
            "model_type": type(self.model).__name__,
            "classes": list(self.model.names.values()) if hasattr(self.model, 'names') else []
        }
    
    def cleanup(self) -> None:
        """
        Limpia recursos utilizados por el servicio.
        """
        if self._model is not None:
            del self._model
            self._model = None
        self._is_initialized = False
        logger.info("Recursos del servicio de detección liberados")