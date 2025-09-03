"""Servicios de detección refactorizados para el Brand Detector Project.

Este módulo contiene todos los servicios de detección organizados de manera modular:
- BaseDetectionService: Clase base abstracta para todos los servicios
- ImageDetectionService: Detección en imágenes estáticas
- VideoDetectionService: Detección en videos locales
- YouTubeDetectionService: Detección en videos de YouTube
- StreamingDetectionService: Detección en tiempo real
- DetectionServiceFactory: Factory para crear y gestionar servicios
"""

from .base_detection_service import BaseDetectionService
from .image_detection_service import ImageDetectionService
from .video_detection_service import (
    VideoDetectionService,
    VideoMetrics,
    ProcessingStatus
)
from .youtube_detection_service import YouTubeDetectionService
from .streaming_detection_service import (
    StreamingDetectionService,
    StreamingMetrics
)
from .detection_service_factory import (
    DetectionServiceFactory,
    DetectionServiceType,
    detection_factory,
    get_detection_service,
    get_service_for_input,
    cleanup_all_detection_services
)

# Servicios legacy (mantener compatibilidad)
from .yolo_service import summarize_counts

__all__ = [
    # Servicios base y principales
    "BaseDetectionService",
    "ImageDetectionService",
    "VideoDetectionService",
    "YouTubeDetectionService",
    "StreamingDetectionService",
    
    # Factory y utilidades
    "DetectionServiceFactory",
    "DetectionServiceType",
    "detection_factory",
    "get_detection_service",
    "get_service_for_input",
    "cleanup_all_detection_services",
    
    # Modelos de datos
    "VideoMetrics",
    "ProcessingStatus",
    "StreamingMetrics",
    
    # Servicios legacy
    "summarize_counts"
]

# Información del módulo
__version__ = "2.0.0"
__author__ = "Brand Detector Team"
__description__ = "Servicios de detección refactorizados y modulares"