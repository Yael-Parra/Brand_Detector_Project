# FASE 2: REFACTORING DE SERVICIOS - BRAND DETECTOR PROJECT

## 📋 Resumen de la Implementación

La **Fase 2** se enfoca en la refactorización completa de los servicios de detección, creando una arquitectura modular, escalable y mantenible. Se ha implementado un patrón de diseño robusto que separa responsabilidades y mejora significativamente la calidad del código.

## 🏗️ Arquitectura de Servicios Refactorizada

### Estructura de Archivos Nuevos

```
backend/services/
├── __init__.py                     # Exportaciones y configuración del módulo
├── base_detection_service.py       # Clase base abstracta para todos los servicios
├── image_detection_service.py      # Servicio especializado para imágenes
├── video_detection_service.py      # Servicio para videos locales
├── youtube_detection_service.py    # Servicio especializado para YouTube
├── streaming_detection_service.py  # Servicio para streaming en tiempo real
├── detection_service_factory.py    # Factory pattern para gestión de servicios
└── migration_guide.py              # Guía de migración del código legacy
```

### Archivos Legacy (Mantenidos para Compatibilidad)

```
backend/services/
├── detection_imagen.py             # ⚠️ Legacy - Usar ImageDetectionService
├── detection_imagen_opencv.py      # ⚠️ Legacy - Usar ImageDetectionService
├── detection_imagen_video.py       # ⚠️ Legacy - Usar VideoDetectionService
├── detection_imagen_streaming.py   # ⚠️ Legacy - Usar StreamingDetectionService
├── detection_imagen_youtube.py     # ⚠️ Legacy - Usar YouTubeDetectionService
├── detection_image_youtube_slow.py # ⚠️ Legacy - Usar YouTubeDetectionService
└── yolo_service.py                 # ✅ Mantenido - Funciones de utilidad
```

## 🔧 Componentes Implementados

### 1. BaseDetectionService (Clase Base Abstracta)

**Archivo:** `base_detection_service.py`

**Características:**
- Clase abstracta que define la interfaz común para todos los servicios
- Carga lazy del modelo YOLO para optimizar memoria
- Métodos comunes para validación, anotación y limpieza
- Manejo centralizado de errores y logging
- Extracción y filtrado de detecciones

**Métodos Principales:**
```python
# Métodos abstractos (deben implementarse)
abstract def process(self, input_data, **kwargs) -> Any

# Métodos implementados
def load_model(self, force_reload: bool = False) -> None
def extract_detections(self, results, confidence_threshold: float) -> List[Dict]
def annotate_frame(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray
def validate_input(self, input_data: Any) -> bool
def cleanup(self) -> None
def get_model_info(self) -> Dict[str, Any]
```

### 2. ImageDetectionService (Detección de Imágenes)

**Archivo:** `image_detection_service.py`

**Características:**
- Procesamiento de imágenes estáticas desde múltiples fuentes
- Soporte para archivos locales, arrays NumPy y UploadFile
- Estadísticas detalladas de detección
- Procesamiento por lotes
- Conversión automática a base64 para APIs

**Métodos Principales:**
```python
def process_image(self, image_source, confidence_threshold=0.5, **kwargs) -> DetectionResult
def process_batch(self, image_sources: List, **kwargs) -> List[DetectionResult]
def process_upload_file(self, upload_file: UploadFile, **kwargs) -> DetectionResult
def process_numpy_array(self, image_array: np.ndarray, **kwargs) -> DetectionResult
```

**Modelo de Datos:**
```python
@dataclass
class DetectionResult:
    detections: List[Dict[str, Any]]
    annotated_image_base64: Optional[str]
    statistics: Dict[str, Any]
    processing_time: float
    confidence_threshold: float
    model_info: Dict[str, Any]
```

### 3. VideoDetectionService (Detección en Videos)

**Archivo:** `video_detection_service.py`

**Características:**
- Procesamiento de videos locales y URLs
- Procesamiento síncrono y asíncrono
- Control de reproducción (pausa, reanuda, detiene)
- Métricas detalladas de procesamiento
- Integración con base de datos
- Salto de frames para optimización

**Métodos Principales:**
```python
def process_video(self, video_source, **kwargs) -> VideoMetrics
def process_video_async(self, video_source, **kwargs) -> str
def pause_processing(self, task_id: str) -> bool
def resume_processing(self, task_id: str) -> bool
def stop_processing(self, task_id: str) -> bool
def get_processing_status(self, task_id: str) -> Dict[str, Any]
```

**Modelos de Datos:**
```python
@dataclass
class VideoMetrics:
    total_frames: int
    processed_frames: int
    total_detections: int
    processing_time: float
    fps: float
    detection_summary: Dict[str, int]
    confidence_threshold: float

@dataclass
class ProcessingStatus:
    status: str  # 'running', 'paused', 'completed', 'error'
    progress: float
    current_frame: int
    total_frames: int
    detections_count: int
    error_message: Optional[str]
```

### 4. YouTubeDetectionService (Detección en YouTube)

**Archivo:** `youtube_detection_service.py`

**Características:**
- Hereda de VideoDetectionService
- Descarga automática con yt-dlp
- Procesamiento de playlists completas
- Validación de URLs de YouTube
- Configuración de calidad de video
- Limpieza automática de archivos temporales

**Métodos Principales:**
```python
def process_video(self, youtube_url: str, **kwargs) -> VideoMetrics
def process_playlist(self, playlist_url: str, **kwargs) -> List[VideoMetrics]
def validate_youtube_url(self, url: str) -> bool
def get_video_info(self, url: str) -> Dict[str, Any]
def get_available_formats(self, url: str) -> List[Dict[str, Any]]
```

### 5. StreamingDetectionService (Detección en Tiempo Real)

**Archivo:** `streaming_detection_service.py`

**Características:**
- Streaming en tiempo real desde cámaras o URLs
- Métricas temporales de rendimiento
- Visualización en tiempo real con estadísticas
- Generador de frames para APIs
- Control de streaming (iniciar/detener)

**Métodos Principales:**
```python
def start_streaming(self, source=0, **kwargs) -> None
def stop_streaming(self) -> None
def process_frame(self, frame: np.ndarray, **kwargs) -> Tuple[np.ndarray, List[Dict]]
def get_streaming_stats(self) -> StreamingMetrics
def frame_generator(self, source=0, **kwargs) -> Iterator[bytes]
```

**Modelo de Datos:**
```python
@dataclass
class StreamingMetrics:
    fps: float
    total_frames: int
    total_detections: int
    detection_counts: Dict[str, int]
    average_processing_time: float
    streaming_duration: float
```

### 6. DetectionServiceFactory (Factory Pattern)

**Archivo:** `detection_service_factory.py`

**Características:**
- Patrón Singleton para gestión centralizada
- Creación automática basada en tipo de entrada
- Cache de instancias para reutilización
- Métodos de conveniencia para cada servicio
- Monitoreo de salud de servicios
- Limpieza automática de recursos

**Métodos Principales:**
```python
def create_service(self, service_type, model_path=None, reuse_instance=True) -> BaseDetectionService
def get_service_by_input_type(self, input_data, **kwargs) -> BaseDetectionService
def get_image_service(self, model_path=None) -> ImageDetectionService
def get_video_service(self, model_path=None) -> VideoDetectionService
def get_youtube_service(self, model_path=None) -> YouTubeDetectionService
def get_streaming_service(self, model_path=None) -> StreamingDetectionService
def cleanup_all_services(self) -> None
def health_check(self) -> Dict[str, Any]
```

**Funciones de Conveniencia:**
```python
# Instancia global
detection_factory = DetectionServiceFactory()

# Funciones de conveniencia
def get_detection_service(service_type, model_path=None) -> BaseDetectionService
def get_service_for_input(input_data, **kwargs) -> BaseDetectionService
def cleanup_all_detection_services() -> None
```

## 📚 Guía de Migración

### Funciones de Compatibilidad

Se han implementado funciones de compatibilidad hacia atrás para facilitar la migración:

```python
# Legacy (con advertencia de deprecación)
from backend.services.migration_guide import predict_image_legacy
result = predict_image_legacy("image.jpg")

# Nuevo (recomendado)
from backend.services import ImageDetectionService
service = ImageDetectionService()
result = service.process_image("image.jpg")
```

### Ejemplos de Migración

#### Antes (Legacy)
```python
# detection_imagen_opencv.py
from backend.services.detection_imagen_opencv import predict_image
detections, annotated = predict_image("image.jpg")
```

#### Después (Refactorizado)
```python
# Opción 1: Servicio específico
from backend.services import ImageDetectionService
service = ImageDetectionService()
result = service.process_image("image.jpg")
detections = result.detections
annotated = result.annotated_image_base64

# Opción 2: Factory pattern
from backend.services import get_detection_service
service = get_detection_service("image")
result = service.process_image("image.jpg")

# Opción 3: Automático
from backend.services import get_service_for_input
service = get_service_for_input("image.jpg")  # Detecta automáticamente
result = service.process_image("image.jpg")
```

## 🚀 Ejemplos de Uso

### 1. Detección de Imágenes

```python
from backend.services import ImageDetectionService

# Crear servicio
service = ImageDetectionService(model_path="path/to/model.pt")

# Procesar imagen
result = service.process_image(
    "image.jpg",
    confidence_threshold=0.7,
    save_annotated=True
)

print(f"Detecciones encontradas: {len(result.detections)}")
print(f"Tiempo de procesamiento: {result.processing_time:.2f}s")
print(f"Estadísticas: {result.statistics}")
```

### 2. Detección en Videos

```python
from backend.services import VideoDetectionService

# Crear servicio
service = VideoDetectionService()

# Procesamiento síncrono
metrics = service.process_video(
    "video.mp4",
    confidence_threshold=0.6,
    frame_skip=2,
    save_to_db=True
)

# Procesamiento asíncrono
task_id = service.process_video_async(
    "video.mp4",
    confidence_threshold=0.6
)

# Control de procesamiento
service.pause_processing(task_id)
service.resume_processing(task_id)
status = service.get_processing_status(task_id)
```

### 3. Detección en YouTube

```python
from backend.services import YouTubeDetectionService

# Crear servicio
service = YouTubeDetectionService()

# Procesar video individual
metrics = service.process_video(
    "https://youtube.com/watch?v=example",
    quality="720p",
    confidence_threshold=0.5
)

# Procesar playlist completa
playlist_results = service.process_playlist(
    "https://youtube.com/playlist?list=example",
    max_videos=10
)
```

### 4. Streaming en Tiempo Real

```python
from backend.services import StreamingDetectionService

# Crear servicio
service = StreamingDetectionService()

# Iniciar streaming desde cámara
service.start_streaming(
    source=0,  # Cámara 0
    confidence_threshold=0.6,
    display_stats=True
)

# Para APIs - generador de frames
for frame_bytes in service.frame_generator(source=0):
    # Enviar frame a cliente
    yield frame_bytes
```

### 5. Factory Pattern

```python
from backend.services import detection_factory, get_service_for_input

# Detección automática del tipo de servicio
service = get_service_for_input("image.jpg")        # ImageDetectionService
service = get_service_for_input("video.mp4")        # VideoDetectionService
service = get_service_for_input("https://youtube.com/...")  # YouTubeDetectionService
service = get_service_for_input(0)                  # StreamingDetectionService

# Acceso directo a servicios específicos
image_service = detection_factory.get_image_service()
video_service = detection_factory.get_video_service()
youtube_service = detection_factory.get_youtube_service()
streaming_service = detection_factory.get_streaming_service()

# Monitoreo de salud
health = detection_factory.health_check()
print(f"Servicios activos: {health['total_services']}")
```

## 🔍 Integración con APIs

### Actualización de Endpoints

Los endpoints existentes pueden migrar gradualmente:

```python
# En upload_image.py
from backend.services import get_service_for_input

@router.post("/upload")
async def upload_image(file: UploadFile):
    service = get_service_for_input(file)
    result = await service.process_upload_file(
        file,
        confidence_threshold=0.5
    )
    return {
        "detections": result.detections,
        "statistics": result.statistics,
        "processing_time": result.processing_time
    }
```

## 🧪 Testing

### Estructura de Tests

```python
# tests/test_services.py
import pytest
from backend.services import (
    ImageDetectionService,
    VideoDetectionService,
    detection_factory
)

class TestImageDetectionService:
    def test_process_image(self):
        service = ImageDetectionService()
        result = service.process_image("test_image.jpg")
        assert len(result.detections) >= 0
        assert result.processing_time > 0
    
    def test_batch_processing(self):
        service = ImageDetectionService()
        results = service.process_batch(["img1.jpg", "img2.jpg"])
        assert len(results) == 2

class TestDetectionFactory:
    def test_service_creation(self):
        service = detection_factory.get_image_service()
        assert isinstance(service, ImageDetectionService)
    
    def test_auto_detection(self):
        service = detection_factory.get_service_by_input_type("image.jpg")
        assert isinstance(service, ImageDetectionService)
```

### Comandos de Testing

```bash
# Ejecutar tests específicos de servicios
pytest tests/test_services.py -v

# Test con coverage
pytest tests/test_services.py --cov=backend.services

# Test de integración
pytest tests/test_integration.py -v
```

## 📊 Beneficios de la Refactorización

### 1. **Arquitectura Modular**
- Separación clara de responsabilidades
- Código más mantenible y testeable
- Fácil extensión para nuevos tipos de detección

### 2. **Reutilización de Código**
- Clase base común para todos los servicios
- Factory pattern para gestión centralizada
- Cache de instancias de modelo para optimización

### 3. **Mejor Manejo de Errores**
- Excepciones específicas y descriptivas
- Logging centralizado y consistente
- Validación robusta de entradas

### 4. **Optimización de Rendimiento**
- Carga lazy de modelos YOLO
- Reutilización de instancias
- Procesamiento asíncrono para videos largos

### 5. **API Consistente**
- Interfaz uniforme entre todos los servicios
- Parámetros estandarizados
- Respuestas estructuradas

### 6. **Facilidad de Testing**
- Servicios independientes y testeables
- Mocking simplificado
- Tests unitarios y de integración

### 7. **Compatibilidad hacia Atrás**
- Funciones legacy mantenidas
- Migración gradual posible
- Advertencias de deprecación

## 🔄 Próximos Pasos

### Fase 3: Optimización y Caching
- Implementar cache Redis para resultados
- Optimizar carga de modelos
- Implementar pool de workers

### Fase 4: Monitoreo y Métricas
- Dashboard de monitoreo
- Métricas de rendimiento
- Alertas automáticas

### Fase 5: Escalabilidad
- Procesamiento distribuido
- Load balancing
- Microservicios

## 📝 Notas de Migración

### ⚠️ Cambios Importantes

1. **Estructura de Respuesta**: Los nuevos servicios retornan objetos estructurados en lugar de tuplas
2. **Manejo de Excepciones**: Se usan excepciones específicas del dominio
3. **Configuración**: Los parámetros se pasan como argumentos nombrados
4. **Logging**: Sistema de logging centralizado y estructurado

### ✅ Compatibilidad

- Funciones legacy disponibles con advertencias
- Migración gradual recomendada
- Documentación completa de migración
- Ejemplos de código actualizados

---

**Fecha de Implementación:** Diciembre 2024  
**Versión:** 2.0.0  
**Estado:** ✅ Completado  
**Próxima Fase:** Optimización y Caching