from typing import Dict, List, Any, Union
import cv2
import numpy as np
import base64
from pathlib import Path
from fastapi import UploadFile

from .base_detection_service import BaseDetectionService
from core.logging import get_logger
from core.exceptions import DetectionError, ValidationError
from utils.file_validation import validate_image_file

logger = get_logger(__name__)

class ImageDetectionService(BaseDetectionService):
    """
    Servicio especializado para detección en imágenes estáticas.
    """
    
    def __init__(self, model_path: str = None):
        super().__init__(model_path)
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    
    def process(self, input_data: Union[str, np.ndarray, UploadFile], **kwargs) -> Dict[str, Any]:
        """
        Procesa una imagen para detectar objetos.
        
        Args:
            input_data: Puede ser:
                - str: Ruta a la imagen
                - np.ndarray: Imagen como array de numpy
                - UploadFile: Archivo subido via FastAPI
            **kwargs: Argumentos adicionales:
                - return_annotated: bool - Si retornar imagen anotada (default: True)
                - confidence_threshold: float - Umbral de confianza (default: 0.5)
                - return_base64: bool - Si retornar imagen en base64 (default: True)
        
        Returns:
            Diccionario con resultados de detección
        """
        try:
            # Configuración
            return_annotated = kwargs.get('return_annotated', True)
            confidence_threshold = kwargs.get('confidence_threshold', 0.5)
            return_base64 = kwargs.get('return_base64', True)
            
            # Cargar imagen
            image = self._load_image(input_data)
            
            # Validar imagen
            if not self._validate_image(image):
                raise ValidationError("Imagen inválida o corrupta")
            
            # Realizar detección
            logger.info("Iniciando detección en imagen")
            results = self.model(image, verbose=False)
            
            # Extraer detecciones
            detections = self._extract_detections(results)
            
            # Filtrar por confianza
            filtered_detections = [
                det for det in detections 
                if det['confidence'] >= confidence_threshold
            ]
            
            # Preparar respuesta
            response = {
                "detections": filtered_detections,
                "total_detections": len(filtered_detections),
                "image_info": {
                    "width": image.shape[1],
                    "height": image.shape[0],
                    "channels": image.shape[2] if len(image.shape) > 2 else 1
                },
                "processing_info": {
                    "model_path": self.model_path,
                    "confidence_threshold": confidence_threshold
                }
            }
            
            # Agregar imagen anotada si se solicita
            if return_annotated and filtered_detections:
                annotated_image = self._annotate_frame(image, filtered_detections)
                
                if return_base64:
                    # Convertir a base64
                    _, buffer = cv2.imencode('.jpg', annotated_image)
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    response["annotated_image_base64"] = img_base64
                else:
                    response["annotated_image"] = annotated_image
            
            # Estadísticas de detección
            response["detection_stats"] = self._calculate_detection_stats(filtered_detections)
            
            logger.info(f"Detección completada: {len(filtered_detections)} objetos encontrados")
            return response
            
        except Exception as e:
            logger.error(f"Error en detección de imagen: {e}")
            raise DetectionError(f"Error procesando imagen: {str(e)}")
    
    def _load_image(self, input_data: Union[str, np.ndarray, UploadFile]) -> np.ndarray:
        """
        Carga una imagen desde diferentes fuentes.
        
        Args:
            input_data: Fuente de la imagen
            
        Returns:
            Imagen como array de numpy
        """
        if isinstance(input_data, str):
            # Cargar desde archivo
            if not Path(input_data).exists():
                raise ValidationError(f"Archivo no encontrado: {input_data}")
            
            image = cv2.imread(input_data)
            if image is None:
                raise ValidationError(f"No se pudo cargar la imagen: {input_data}")
            return image
            
        elif isinstance(input_data, np.ndarray):
            # Ya es un array de numpy
            return input_data
            
        elif isinstance(input_data, UploadFile):
            # Validar archivo subido
            validation_result = validate_image_file(input_data)
            if not validation_result["valid"]:
                raise ValidationError(f"Archivo inválido: {validation_result['error']}")
            
            # Leer contenido del archivo
            contents = input_data.file.read()
            input_data.file.seek(0)  # Reset file pointer
            
            # Convertir a array numpy
            nparr = np.frombuffer(contents, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValidationError("No se pudo decodificar la imagen")
            return image
        
        else:
            raise ValidationError(f"Tipo de entrada no soportado: {type(input_data)}")
    
    def _validate_image(self, image: np.ndarray) -> bool:
        """
        Valida que la imagen sea correcta.
        
        Args:
            image: Imagen a validar
            
        Returns:
            True si la imagen es válida
        """
        if image is None:
            return False
        
        if len(image.shape) < 2:
            return False
        
        if image.shape[0] == 0 or image.shape[1] == 0:
            return False
        
        return True
    
    def _calculate_detection_stats(self, detections: List[Dict]) -> Dict[str, Any]:
        """
        Calcula estadísticas de las detecciones.
        
        Args:
            detections: Lista de detecciones
            
        Returns:
            Estadísticas calculadas
        """
        if not detections:
            return {"labels_count": {}, "confidence_stats": {}}
        
        # Contar por etiquetas
        labels_count = {}
        confidences = []
        
        for detection in detections:
            label = detection["label"]
            confidence = detection["confidence"]
            
            labels_count[label] = labels_count.get(label, 0) + 1
            confidences.append(confidence)
        
        # Estadísticas de confianza
        confidence_stats = {
            "mean": np.mean(confidences),
            "min": np.min(confidences),
            "max": np.max(confidences),
            "std": np.std(confidences)
        }
        
        return {
            "labels_count": labels_count,
            "confidence_stats": confidence_stats
        }
    
    def process_batch(self, image_paths: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Procesa múltiples imágenes en lote.
        
        Args:
            image_paths: Lista de rutas de imágenes
            **kwargs: Argumentos para el procesamiento
            
        Returns:
            Lista de resultados de detección
        """
        results = []
        
        for i, image_path in enumerate(image_paths):
            try:
                logger.info(f"Procesando imagen {i+1}/{len(image_paths)}: {image_path}")
                result = self.process(image_path, **kwargs)
                result["image_path"] = image_path
                results.append(result)
            except Exception as e:
                logger.error(f"Error procesando {image_path}: {e}")
                results.append({
                    "image_path": image_path,
                    "error": str(e),
                    "detections": [],
                    "total_detections": 0
                })
        
        return results
    
    def get_supported_formats(self) -> List[str]:
        """
        Obtiene los formatos de imagen soportados.
        
        Returns:
            Lista de extensiones soportadas
        """
        return self.supported_formats.copy()