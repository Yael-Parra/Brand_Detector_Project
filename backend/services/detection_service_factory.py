from typing import Dict, Any, Optional, Type, Union, List
from enum import Enum

from .base_detection_service import BaseDetectionService
from .image_detection_service import ImageDetectionService
from .video_detection_service import VideoDetectionService
from .youtube_detection_service import YouTubeDetectionService
from .streaming_detection_service import StreamingDetectionService
from backend.core.logging import get_logger
from backend.core.exceptions import DetectionError, ValidationError
from backend.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()

class DetectionServiceType(Enum):
    """Tipos de servicios de detección disponibles"""
    IMAGE = "image"
    VIDEO = "video"
    YOUTUBE = "youtube"
    STREAMING = "streaming"

class DetectionServiceFactory:
    """
    Factory para crear y gestionar servicios de detección.
    Implementa el patrón Singleton para reutilizar instancias.
    """
    
    _instance: Optional['DetectionServiceFactory'] = None
    _services: Dict[str, BaseDetectionService] = {}
    
    def __new__(cls) -> 'DetectionServiceFactory':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._service_classes: Dict[DetectionServiceType, Type[BaseDetectionService]] = {
                DetectionServiceType.IMAGE: ImageDetectionService,
                DetectionServiceType.VIDEO: VideoDetectionService,
                DetectionServiceType.YOUTUBE: YouTubeDetectionService,
                DetectionServiceType.STREAMING: StreamingDetectionService
            }
            self._initialized = True
            logger.info("DetectionServiceFactory inicializado")
    
    def create_service(
        self, 
        service_type: Union[DetectionServiceType, str], 
        model_path: Optional[str] = None,
        reuse_instance: bool = True
    ) -> BaseDetectionService:
        """
        Crea o reutiliza una instancia del servicio de detección especificado.
        
        Args:
            service_type: Tipo de servicio a crear
            model_path: Ruta del modelo YOLO (opcional)
            reuse_instance: Si reutilizar instancia existente (default: True)
            
        Returns:
            Instancia del servicio de detección
            
        Raises:
            ValidationError: Si el tipo de servicio no es válido
            DetectionError: Si hay error creando el servicio
        """
        try:
            # Convertir string a enum si es necesario
            if isinstance(service_type, str):
                try:
                    service_type = DetectionServiceType(service_type.lower())
                except ValueError:
                    raise ValidationError(f"Tipo de servicio inválido: {service_type}")
            
            # Generar clave para el cache
            cache_key = f"{service_type.value}_{model_path or 'default'}"
            
            # Reutilizar instancia si existe y se solicita
            if reuse_instance and cache_key in self._services:
                logger.debug(f"Reutilizando instancia de {service_type.value}")
                return self._services[cache_key]
            
            # Crear nueva instancia
            service_class = self._service_classes.get(service_type)
            if not service_class:
                raise ValidationError(f"Servicio no implementado: {service_type.value}")
            
            logger.info(f"Creando nueva instancia de {service_type.value}")
            service = service_class(model_path=model_path)
            
            # Guardar en cache si se solicita reutilización
            if reuse_instance:
                self._services[cache_key] = service
            
            return service
            
        except Exception as e:
            logger.error(f"Error creando servicio {service_type}: {e}")
            raise DetectionError(f"No se pudo crear el servicio: {str(e)}")
    
    def get_image_service(self, model_path: Optional[str] = None) -> ImageDetectionService:
        """
        Obtiene el servicio de detección de imágenes.
        
        Args:
            model_path: Ruta del modelo (opcional)
            
        Returns:
            Servicio de detección de imágenes
        """
        return self.create_service(DetectionServiceType.IMAGE, model_path)
    
    def get_video_service(self, model_path: Optional[str] = None) -> VideoDetectionService:
        """
        Obtiene el servicio de detección de videos.
        
        Args:
            model_path: Ruta del modelo (opcional)
            
        Returns:
            Servicio de detección de videos
        """
        return self.create_service(DetectionServiceType.VIDEO, model_path)
    
    def get_youtube_service(self, model_path: Optional[str] = None) -> YouTubeDetectionService:
        """
        Obtiene el servicio de detección de YouTube.
        
        Args:
            model_path: Ruta del modelo (opcional)
            
        Returns:
            Servicio de detección de YouTube
        """
        return self.create_service(DetectionServiceType.YOUTUBE, model_path)
    
    def get_streaming_service(self, model_path: Optional[str] = None) -> StreamingDetectionService:
        """
        Obtiene el servicio de detección de streaming.
        
        Args:
            model_path: Ruta del modelo (opcional)
            
        Returns:
            Servicio de detección de streaming
        """
        return self.create_service(DetectionServiceType.STREAMING, model_path)
    
    def get_service_by_input_type(self, input_data: Any, **kwargs) -> BaseDetectionService:
        """
        Obtiene el servicio apropiado basado en el tipo de entrada.
        
        Args:
            input_data: Datos de entrada
            **kwargs: Argumentos adicionales
            
        Returns:
            Servicio apropiado para el tipo de entrada
        """
        from pathlib import Path
        from fastapi import UploadFile
        
        # Determinar tipo de servicio basado en la entrada
        if isinstance(input_data, str):
            # URL de YouTube
            if any(domain in input_data.lower() for domain in ['youtube.com', 'youtu.be']):
                return self.get_youtube_service()
            
            # Archivo local
            elif Path(input_data).exists():
                suffix = Path(input_data).suffix.lower()
                if suffix in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                    return self.get_image_service()
                elif suffix in ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']:
                    return self.get_video_service()
            
            # URL de stream
            elif input_data.startswith(('http://', 'https://')):
                return self.get_streaming_service()
        
        elif isinstance(input_data, UploadFile):
            # Archivo subido
            if input_data.content_type:
                if input_data.content_type.startswith('image/'):
                    return self.get_image_service()
                elif input_data.content_type.startswith('video/'):
                    return self.get_video_service()
        
        elif isinstance(input_data, int):
            # Índice de cámara
            return self.get_streaming_service()
        
        # Por defecto, usar servicio de imagen
        logger.warning(f"No se pudo determinar el tipo de servicio para: {type(input_data)}, usando servicio de imagen")
        return self.get_image_service()
    
    def cleanup_service(self, service_type: Union[DetectionServiceType, str], model_path: Optional[str] = None) -> bool:
        """
        Limpia y elimina un servicio específico del cache.
        
        Args:
            service_type: Tipo de servicio
            model_path: Ruta del modelo
            
        Returns:
            True si se limpió correctamente
        """
        try:
            if isinstance(service_type, str):
                service_type = DetectionServiceType(service_type.lower())
            
            cache_key = f"{service_type.value}_{model_path or 'default'}"
            
            if cache_key in self._services:
                service = self._services[cache_key]
                service.cleanup()
                del self._services[cache_key]
                logger.info(f"Servicio {service_type.value} limpiado")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error limpiando servicio {service_type}: {e}")
            return False
    
    def cleanup_all_services(self) -> None:
        """
        Limpia todos los servicios en cache.
        """
        logger.info("Limpiando todos los servicios...")
        
        for cache_key, service in list(self._services.items()):
            try:
                service.cleanup()
                del self._services[cache_key]
            except Exception as e:
                logger.error(f"Error limpiando servicio {cache_key}: {e}")
        
        self._services.clear()
        logger.info("Todos los servicios han sido limpiados")
    
    def get_available_services(self) -> List[str]:
        """
        Obtiene la lista de servicios disponibles.
        
        Returns:
            Lista de nombres de servicios disponibles
        """
        return [service_type.value for service_type in DetectionServiceType]
    
    def get_active_services(self) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene información de los servicios activos.
        
        Returns:
            Información de servicios activos
        """
        active_services = {}
        
        for cache_key, service in self._services.items():
            try:
                model_info = service.get_model_info()
                active_services[cache_key] = {
                    "service_type": type(service).__name__,
                    "model_info": model_info,
                    "is_initialized": model_info.get("status") == "initialized"
                }
            except Exception as e:
                active_services[cache_key] = {
                    "service_type": type(service).__name__,
                    "error": str(e)
                }
        
        return active_services
    
    def health_check(self) -> Dict[str, Any]:
        """
        Realiza un chequeo de salud de todos los servicios.
        
        Returns:
            Estado de salud de los servicios
        """
        health_status = {
            "factory_status": "healthy",
            "total_services": len(self._services),
            "services": {}
        }
        
        for cache_key, service in self._services.items():
            try:
                model_info = service.get_model_info()
                health_status["services"][cache_key] = {
                    "status": "healthy" if model_info.get("status") == "initialized" else "unhealthy",
                    "model_path": model_info.get("model_path"),
                    "classes_count": len(model_info.get("classes", []))
                }
            except Exception as e:
                health_status["services"][cache_key] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return health_status

# Instancia global del factory
detection_factory = DetectionServiceFactory()

# Funciones de conveniencia
def get_detection_service(
    service_type: Union[DetectionServiceType, str], 
    model_path: Optional[str] = None
) -> BaseDetectionService:
    """
    Función de conveniencia para obtener un servicio de detección.
    
    Args:
        service_type: Tipo de servicio
        model_path: Ruta del modelo (opcional)
        
    Returns:
        Servicio de detección
    """
    return detection_factory.create_service(service_type, model_path)

def get_service_for_input(input_data: Any, **kwargs) -> BaseDetectionService:
    """
    Función de conveniencia para obtener el servicio apropiado para una entrada.
    
    Args:
        input_data: Datos de entrada
        **kwargs: Argumentos adicionales
        
    Returns:
        Servicio apropiado
    """
    return detection_factory.get_service_by_input_type(input_data, **kwargs)

def cleanup_all_detection_services() -> None:
    """
    Función de conveniencia para limpiar todos los servicios.
    """
    detection_factory.cleanup_all_services()