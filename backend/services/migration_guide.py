"""Guía de migración y utilidades para migrar del código legacy a los nuevos servicios.

Este módulo proporciona:
1. Funciones de compatibilidad hacia atrás
2. Mapeo de funciones legacy a nuevos servicios
3. Utilidades de migración
4. Ejemplos de uso
"""

import warnings
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from .detection_service_factory import detection_factory, DetectionServiceType
from backend.core.logging import get_logger

logger = get_logger(__name__)

def _deprecation_warning(old_function: str, new_function: str, version: str = "3.0.0"):
    """Emite una advertencia de deprecación."""
    warnings.warn(
        f"{old_function} está deprecado y será removido en la versión {version}. "
        f"Use {new_function} en su lugar.",
        DeprecationWarning,
        stacklevel=3
    )

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA detection_imagen.py
# ============================================================================

def predict_image_legacy(image_path: str, model_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Función de compatibilidad para detection_imagen.py
    
    Args:
        image_path: Ruta de la imagen
        model_path: Ruta del modelo YOLO
        
    Returns:
        Resultados de detección en formato legacy
    """
    _deprecation_warning(
        "predict_image_legacy",
        "ImageDetectionService.process_image"
    )
    
    service = detection_factory.get_image_service(model_path)
    result = service.process_image(image_path)
    
    # Convertir a formato legacy
    return {
        "detections": result.detections,
        "annotated_image": result.annotated_image_base64,
        "statistics": result.statistics,
        "processing_time": result.processing_time
    }

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA detection_imagen_opencv.py
# ============================================================================

def predict_image_opencv_legacy(
    image_path: str, 
    confidence_threshold: float = 0.5,
    model_path: Optional[str] = None
) -> tuple:
    """
    Función de compatibilidad para detection_imagen_opencv.py
    
    Args:
        image_path: Ruta de la imagen
        confidence_threshold: Umbral de confianza
        model_path: Ruta del modelo
        
    Returns:
        Tupla (detecciones, imagen_anotada_base64)
    """
    _deprecation_warning(
        "predict_image_opencv_legacy",
        "ImageDetectionService.process_image"
    )
    
    service = detection_factory.get_image_service(model_path)
    result = service.process_image(
        image_path, 
        confidence_threshold=confidence_threshold
    )
    
    return result.detections, result.annotated_image_base64

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA detection_imagen_video.py
# ============================================================================

def process_video_legacy(
    video_source: Union[str, int] = 0,
    model_path: Optional[str] = None,
    confidence_threshold: float = 0.5
) -> None:
    """
    Función de compatibilidad para detection_imagen_video.py
    
    Args:
        video_source: Fuente del video (ruta o índice de cámara)
        model_path: Ruta del modelo
        confidence_threshold: Umbral de confianza
    """
    _deprecation_warning(
        "process_video_legacy",
        "VideoDetectionService.process_video o StreamingDetectionService.start_streaming"
    )
    
    if isinstance(video_source, int):
        # Es una cámara, usar streaming service
        service = detection_factory.get_streaming_service(model_path)
        service.start_streaming(
            source=video_source,
            confidence_threshold=confidence_threshold
        )
    else:
        # Es un archivo de video
        service = detection_factory.get_video_service(model_path)
        service.process_video(
            video_source,
            confidence_threshold=confidence_threshold,
            display_video=True
        )

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA detection_imagen_streaming.py
# ============================================================================

def process_streaming_legacy(
    camera_index: int = 0,
    model_path: Optional[str] = None,
    confidence_threshold: float = 0.5
) -> None:
    """
    Función de compatibilidad para detection_imagen_streaming.py
    
    Args:
        camera_index: Índice de la cámara
        model_path: Ruta del modelo
        confidence_threshold: Umbral de confianza
    """
    _deprecation_warning(
        "process_streaming_legacy",
        "StreamingDetectionService.start_streaming"
    )
    
    service = detection_factory.get_streaming_service(model_path)
    service.start_streaming(
        source=camera_index,
        confidence_threshold=confidence_threshold
    )

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA detection_imagen_youtube.py
# ============================================================================

def process_youtube_legacy(
    youtube_url: str,
    model_path: Optional[str] = None,
    confidence_threshold: float = 0.5
) -> None:
    """
    Función de compatibilidad para detection_imagen_youtube.py
    
    Args:
        youtube_url: URL del video de YouTube
        model_path: Ruta del modelo
        confidence_threshold: Umbral de confianza
    """
    _deprecation_warning(
        "process_youtube_legacy",
        "YouTubeDetectionService.process_video"
    )
    
    service = detection_factory.get_youtube_service(model_path)
    service.process_video(
        youtube_url,
        confidence_threshold=confidence_threshold,
        display_video=True
    )

# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA detection_image_youtube_slow.py
# ============================================================================

class VideoProcessorLegacy:
    """
    Clase de compatibilidad para VideoProcessor de detection_image_youtube_slow.py
    """
    
    def __init__(self, model_path: Optional[str] = None):
        _deprecation_warning(
            "VideoProcessorLegacy",
            "YouTubeDetectionService"
        )
        self.service = detection_factory.get_youtube_service(model_path)
        self._current_task_id = None
    
    def start(self, youtube_url: str, **kwargs) -> str:
        """Inicia el procesamiento de un video de YouTube."""
        task_id = self.service.process_video_async(
            youtube_url,
            **kwargs
        )
        self._current_task_id = task_id
        return task_id
    
    def pause(self) -> bool:
        """Pausa el procesamiento actual."""
        if self._current_task_id:
            return self.service.pause_processing(self._current_task_id)
        return False
    
    def resume(self) -> bool:
        """Reanuda el procesamiento pausado."""
        if self._current_task_id:
            return self.service.resume_processing(self._current_task_id)
        return False
    
    def stop(self) -> bool:
        """Detiene el procesamiento actual."""
        if self._current_task_id:
            return self.service.stop_processing(self._current_task_id)
        return False
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado del procesamiento actual."""
        if self._current_task_id:
            return self.service.get_processing_status(self._current_task_id)
        return {"status": "idle"}

# ============================================================================
# UTILIDADES DE MIGRACIÓN
# ============================================================================

def migrate_legacy_code_examples() -> Dict[str, str]:
    """
    Proporciona ejemplos de migración del código legacy.
    
    Returns:
        Diccionario con ejemplos de migración
    """
    return {
        "detection_imagen.py": """
# ANTES (Legacy)
from backend.services.detection_imagen import main
main()

# DESPUÉS (Nuevo)
from backend.services import ImageDetectionService
service = ImageDetectionService()
result = service.process_image("path/to/image.jpg")
print(f"Detecciones: {len(result.detections)}")
        """,
        
        "detection_imagen_opencv.py": """
# ANTES (Legacy)
from backend.services.detection_imagen_opencv import predict_image
detections, annotated = predict_image("image.jpg")

# DESPUÉS (Nuevo)
from backend.services import get_detection_service
service = get_detection_service("image")
result = service.process_image("image.jpg")
detections = result.detections
annotated = result.annotated_image_base64
        """,
        
        "detection_imagen_video.py": """
# ANTES (Legacy)
# Código directo en el archivo

# DESPUÉS (Nuevo)
from backend.services import VideoDetectionService
service = VideoDetectionService()
service.process_video("video.mp4", display_video=True)
        """,
        
        "detection_imagen_streaming.py": """
# ANTES (Legacy)
# Código directo en el archivo

# DESPUÉS (Nuevo)
from backend.services import StreamingDetectionService
service = StreamingDetectionService()
service.start_streaming(source=0)  # Cámara 0
        """,
        
        "detection_imagen_youtube.py": """
# ANTES (Legacy)
# Código directo en el archivo

# DESPUÉS (Nuevo)
from backend.services import YouTubeDetectionService
service = YouTubeDetectionService()
service.process_video("https://youtube.com/watch?v=...", display_video=True)
        """,
        
        "detection_image_youtube_slow.py": """
# ANTES (Legacy)
from backend.services.detection_image_youtube_slow import VideoProcessor
processor = VideoProcessor()
task_id = processor.start("youtube_url")

# DESPUÉS (Nuevo)
from backend.services import YouTubeDetectionService
service = YouTubeDetectionService()
task_id = service.process_video_async("youtube_url")
        """,
        
        "Factory Pattern": """
# NUEVO: Uso del Factory Pattern
from backend.services import detection_factory, get_service_for_input

# Automático basado en entrada
service = get_service_for_input("image.jpg")  # ImageDetectionService
service = get_service_for_input("video.mp4")  # VideoDetectionService
service = get_service_for_input("https://youtube.com/...")  # YouTubeDetectionService
service = get_service_for_input(0)  # StreamingDetectionService (cámara)

# Manual
image_service = detection_factory.get_image_service()
video_service = detection_factory.get_video_service()
youtube_service = detection_factory.get_youtube_service()
streaming_service = detection_factory.get_streaming_service()
        """
    }

def check_legacy_imports() -> List[str]:
    """
    Verifica si hay imports legacy en el código.
    
    Returns:
        Lista de archivos con imports legacy
    """
    legacy_patterns = [
        "from backend.services.detection_imagen import",
        "from backend.services.detection_imagen_opencv import",
        "from backend.services.detection_imagen_video import",
        "from backend.services.detection_imagen_streaming import",
        "from backend.services.detection_imagen_youtube import",
        "from backend.services.detection_image_youtube_slow import"
    ]
    
    # Esta función podría implementarse para escanear archivos
    # Por ahora, solo retorna una lista vacía
    logger.info("Función check_legacy_imports no implementada completamente")
    return []

def get_migration_recommendations() -> Dict[str, Any]:
    """
    Proporciona recomendaciones para la migración.
    
    Returns:
        Recomendaciones de migración
    """
    return {
        "immediate_actions": [
            "Actualizar imports para usar los nuevos servicios",
            "Reemplazar llamadas directas con el factory pattern",
            "Actualizar manejo de errores para usar las nuevas excepciones",
            "Migrar configuraciones hardcodeadas a settings"
        ],
        "benefits": [
            "Mejor separación de responsabilidades",
            "Código más testeable y mantenible",
            "Manejo de errores más robusto",
            "Logging centralizado y consistente",
            "Reutilización de instancias de modelo",
            "API más consistente entre servicios"
        ],
        "breaking_changes": [
            "Cambio en la estructura de retorno de funciones",
            "Nuevos parámetros requeridos en algunos métodos",
            "Diferentes nombres de métodos",
            "Manejo de excepciones actualizado"
        ],
        "compatibility": [
            "Funciones legacy disponibles con advertencias de deprecación",
            "Migración gradual posible",
            "Documentación de migración incluida"
        ]
    }

if __name__ == "__main__":
    # Mostrar ejemplos de migración
    examples = migrate_legacy_code_examples()
    recommendations = get_migration_recommendations()
    
    print("=" * 80)
    print("GUÍA DE MIGRACIÓN - SERVICIOS DE DETECCIÓN")
    print("=" * 80)
    
    print("\n📋 RECOMENDACIONES:")
    for category, items in recommendations.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for item in items:
            print(f"  • {item}")
    
    print("\n📝 EJEMPLOS DE MIGRACIÓN:")
    for file_name, example in examples.items():
        print(f"\n{'-' * 40}")
        print(f"📁 {file_name}")
        print(f"{'-' * 40}")
        print(example)