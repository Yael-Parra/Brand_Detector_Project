# Brand Detector API

## Descripción

Esta API permite detectar logos de marcas en videos de YouTube utilizando un modelo YOLO entrenado. La API procesa videos y devuelve estadísticas sobre las marcas detectadas.

## Nuevas características

### Endpoint mejorado para procesar videos de YouTube

Se ha implementado un nuevo endpoint `/process/youtube_v2` que mejora la funcionalidad del endpoint original:

- No utiliza subprocesos, lo que evita problemas con la importación de módulos
- Evita el uso de funciones GUI de OpenCV que causaban errores
- Procesa videos en segundo plano con BackgroundTasks
- Maneja mejor los errores y proporciona respuestas más informativas
- Almacena los resultados en memoria para consulta posterior

## Endpoints disponibles

### Procesar video de YouTube

```
POST /process/youtube_v2
```

**Parámetros:**

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Respuesta:**

```json
{
  "status": "processing",
  "message": "El video se está procesando en segundo plano. Los resultados se guardarán automáticamente."
}
```

### Procesar video de YouTube (síncrono)

```
POST /process/youtube_v2/sync
```

**Parámetros:**

```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Respuesta:**

```json
{
  "status": "success",
  "message": "Video procesado correctamente",
  "video_info": {
    "type": "url",
    "name": "https://www.youtube.com/watch?v=VIDEO_ID",
    "total_video_time_segs": 120.5,
    "date_registered": "2023-07-01T12:34:56.789Z"
  },
  "detections": {
    "marca1": {
      "qty_frames_detected": 150,
      "frame_per_second": 1.25,
      "frames_appearance_in_percentage": 25.0
    },
    "marca2": {
      "qty_frames_detected": 75,
      "frame_per_second": 0.625,
      "frames_appearance_in_percentage": 12.5
    }
  }
}
```

### Obtener resultados de un procesamiento

```
GET /results/{result_id}
```

**Respuesta:**

```json
{
  "id": "video_1_20230701123456",
  "type": "url",
  "name": "https://www.youtube.com/watch?v=VIDEO_ID",
  "duration_sec": 120,
  "fps_estimated": 30.0,
  "detections": {
    "marca1": {
      "qty_frames_detected": 150,
      "frame_per_second": 1.25,
      "frames_appearance_in_percentage": 25.0
    }
  },
  "timestamp": "2023-07-01T12:34:56.789Z"
}
```

### Listar todos los resultados

```
GET /results
```

**Respuesta:**

```json
[
  {
    "id": "video_1_20230701123456",
    "type": "url",
    "name": "https://www.youtube.com/watch?v=VIDEO_ID",
    "duration_sec": 120,
    "fps_estimated": 30.0,
    "detections": { ... },
    "timestamp": "2023-07-01T12:34:56.789Z"
  },
  {
    "id": "video_2_20230701124567",
    "type": "url",
    "name": "https://www.youtube.com/watch?v=ANOTHER_VIDEO_ID",
    "duration_sec": 180,
    "fps_estimated": 25.0,
    "detections": { ... },
    "timestamp": "2023-07-01T12:45:67.890Z"
  }
]
```

### Obtener estadísticas generales

```
GET /stats
```

**Respuesta:**

```json
{
  "total_videos": 2,
  "total_duration": 300,
  "labels": {
    "marca1": {
      "total_detections": 200,
      "videos_with_label": 2
    },
    "marca2": {
      "total_detections": 75,
      "videos_with_label": 1
    }
  }
}
```

## Cómo usar

1. Asegúrate de tener todas las dependencias instaladas:

```bash
pip install -r requirements.txt
```

2. Inicia la API:

```bash
uvicorn backend.main:app --reload
```

3. Accede a la documentación de la API en:

```
http://localhost:8000/docs
```

4. Realiza una solicitud al endpoint `/process/youtube_v2` con la URL del video de YouTube que deseas procesar.

5. Consulta los resultados utilizando los endpoints `/results` o `/stats`.