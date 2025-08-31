from ultralytics import YOLO
import cv2
# Manejo seguro de importación de módulos
try:
    import imutils
except ImportError:
    print("Instalando imutils...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imutils==0.5.4"])
    import imutils

try:
    from loguru import logger
except ImportError:
    print("Instalando loguru...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "loguru==0.7.3"])
    from loguru import logger

# Manejo seguro de pytubefix (usado por ultralytics para YouTube)
try:
    import pytubefix
except ImportError:
    print("Instalando pytubefix...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytubefix>=6.5.2"])
    import pytubefix

import time
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import requests

class VideoProcessor:
    def send_results_to_backend(self, api_url: str = "http://localhost:8000/predict/url"):
        metrics = self.get_processing_metrics()
        video_info = metrics["video_info"]
        detections = metrics["detection_results"]

        data = {
            "type": video_info["type"],
            "name": video_info["name"],
            "duration_sec": int(video_info["total_video_time_segs"]) or 0,
            "fps_estimated": (
                metrics["total_frames_processed"] / video_info["total_video_time_segs"]
                if video_info["total_video_time_segs"] > 0 else 0.0
            ),
            "detections": detections,
        }

        resp = requests.post(api_url, json=data, timeout=30)
        print("\n[BACKEND]", resp.status_code, resp.text)

    def __init__(self, model_path, video_source):
        self.model = YOLO(model_path)
        self.source = video_source
        self.speed_multiplier = 0.5  # Velocidad lenta por defecto
        self.paused = False
        self.current_frame = 0
        self.downloaded_path = None
        self.frame_count = 0
        self.frame_skip_counter = 0
        
        # Variables para métricas (solo cálculo, no guardado)
        self.start_time = None
        self.detection_data = {}
        self.total_frames_processed = 0
        self.video_duration = 0
        self.processing_metrics = {}
    
    def get_processing_metrics(self):
        """Obtener todas las métricas calculadas para la base de datos"""
        return {
            'video_info': {
                'type': 'url' if self.source.startswith('http') else 'mp4',
                'name': os.path.basename(self.source) if not self.source.startswith('http') else self.source,
                'total_video_time_segs': self.video_duration,
                'date_registered': datetime.now().isoformat()
            },
            'detection_results': self.calculate_metrics(),
            'total_frames_processed': self.total_frames_processed
        }
    
    def update_detection_stats(self, results):
        """Actualizar estadísticas de detección (solo cálculo)"""
        if hasattr(results, 'boxes') and results.boxes is not None:
            for box in results.boxes:
                class_id = int(box.cls[0])
                label_name = self.model.names[class_id]
                
                if label_name not in self.detection_data:
                    self.detection_data[label_name] = {'count': 0}
                
                self.detection_data[label_name]['count'] += 1
    
    def calculate_metrics(self):
        """Calcular métricas finales (solo cálculo, NO guardado)"""
        metrics = {}
        total_time = time.time() - self.start_time if self.start_time else 0
        
        for label_name, data in self.detection_data.items():
            count = data['count']
            fps = count / total_time if total_time > 0 else 0
            percentage = (count / self.total_frames_processed * 100) if self.total_frames_processed > 0 else 0
            
            metrics[label_name] = {
                'qty_frames_detected': count,
                'frame_per_second': fps,
                'frames_appearance_in_percentage': percentage
            }
        
        return metrics
        
    def send_results_to_backend(self):
        """Enviar resultados al backend para persistencia"""
        try:
            metrics = self.get_processing_metrics()
            video_info = metrics['video_info']
            detection_results = metrics['detection_results']
            
            # Preparar datos para la API
            data = {
                "type": video_info['type'],
                "name": video_info['name'],
                "duration_sec": int(video_info['total_video_time_segs']),
                "fps_estimated": float(self.total_frames_processed / video_info['total_video_time_segs']) if video_info['total_video_time_segs'] > 0 else 0,
                "detections": detection_results
            }
            
            # Enviar a la API para persistencia
            try:
                # Intentar primero con la API local
                response = requests.post(
                    "http://localhost:8000/predict/url",
                    json=data
                )
                if response.status_code == 200:
                    print("✓ Resultados enviados correctamente al backend")
                    result_id = response.json().get('id', 'unknown')
                    print(f"  ID de resultado: {result_id}")
                    return True
                else:
                    print(f"✗ Error al enviar resultados: {response.status_code} - {response.text}")
            except requests.exceptions.ConnectionError:
                print("✗ No se pudo conectar con el backend. Asegúrate de que la API esté en ejecución.")
            
            return False
        except Exception as e:
            print(f"✗ Error al enviar resultados: {e}")
            return False
        
    def download_youtube_video(self, url):
        """Descargar video de YouTube usando yt-dlp"""
        logger.info("Intentando descargar video de YouTube...")
        print("Descargando video de YouTube...")
        
        # Crear carpeta temporal si no existe
        temp_dir = Path("temp_videos")
        temp_dir.mkdir(exist_ok=True)
        
        # Nombre de archivo temporal
        output_path = temp_dir / "temp_video.%(ext)s"
        
        try:
            # Comando yt-dlp para descargar
            cmd = [
                "yt-dlp",
                "--format", "best[height<=720]",  # Calidad máxima 720p para evitar problemas
                "--output", str(output_path),
                "--no-playlist",
                url
            ]
            
            logger.info(f"Ejecutando: {' '.join(cmd)}")
            print(f"Ejecutando comando de descarga...")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Buscar el archivo descargado
                for file in temp_dir.glob("temp_video.*"):
                    logger.info(f"Video descargado: {file}")
                    print(f"Video descargado exitosamente: {file}")
                    return str(file)
            else:
                logger.error(f"Error en yt-dlp: {result.stderr}")
                print(f"Error al descargar el video: {result.stderr}")
                return None
                
        except FileNotFoundError:
            logger.error("yt-dlp no está instalado. Intentando instalar automáticamente...")
            print("Error: yt-dlp no está instalado. Intentando instalar automáticamente...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
                print("yt-dlp instalado correctamente. Reintentando descarga...")
                # Reintentar la descarga después de instalar
                return self.download_youtube_video(url)
            except Exception as install_error:
                logger.error(f"Error al instalar yt-dlp: {install_error}")
                print(f"Error al instalar yt-dlp: {install_error}")
                return None
        except Exception as e:
            logger.error(f"Error al descargar: {e}")
            print(f"Error al descargar: {e}")
            return None
    
    def process_with_yolo_stream(self):
        """Procesar video usando el método stream de YOLO (sin GUI para evitar errores de OpenCV)"""
        print("=== PROCESANDO VIDEO ===")
        print(f"Iniciando procesamiento con velocidad: {self.speed_multiplier}x")
        
        # Inicializar métricas
        self.start_time = time.time()
        self.detection_data = {}
        self.total_frames_processed = 0
        fps = 0
        frame_times = []
        
        try:
            # Usar el método stream de YOLO
            results = self.model(self.source, stream=True, verbose=True)
            
            frame_count = 0
            start_time = time.time()
            
            # Mostrar progreso cada 100 frames
            progress_interval = 100
            next_progress_update = progress_interval
            
            for result in results:
                self.current_frame += 1
                
                # Control de velocidad mediante saltos de frames
                if self.speed_multiplier > 1.0:
                    self.frame_skip_counter += 1
                    if self.frame_skip_counter % int(self.speed_multiplier) != 0:
                        continue
                
                # Procesar frame
                frame_count += 1
                self.total_frames_processed += 1
                
                # Actualizar estadísticas de detección
                self.update_detection_stats(result)
                
                # Calcular FPS en tiempo real
                current_time = time.time()
                frame_times.append(current_time)
                
                # Mantener solo los últimos 30 frames para cálculo de FPS
                if len(frame_times) > 30:
                    frame_times.pop(0)
                
                # Calcular FPS basado en los últimos frames
                if len(frame_times) > 1:
                    fps = len(frame_times) / (frame_times[-1] - frame_times[0])
                
                # Mostrar progreso periódicamente
                if frame_count >= next_progress_update:
                    elapsed = time.time() - start_time
                    print(f"Progreso: {frame_count} frames procesados, FPS: {fps:.1f}, Tiempo: {elapsed:.2f}s")
                    
                    # Mostrar detecciones actuales
                    if self.detection_data:
                        print("Detecciones actuales:")
                        for label, data in self.detection_data.items():
                            print(f"  - {label}: {data['count']} frames")
                    
                    next_progress_update += progress_interval
                
                # CONTROL DE VELOCIDAD para velocidades lentas
                if self.speed_multiplier < 1.0:
                    target_delay = (1.0 / (30 * self.speed_multiplier)) - 0.01  # Asumiendo 30 FPS
                    if target_delay > 0:
                        time.sleep(target_delay)
            
            # Al final del procesamiento, calcular métricas finales
            self.video_duration = time.time() - self.start_time
            self.processing_metrics = self.get_processing_metrics()
            
            print("\n=== MÉTRICAS CALCULADAS ===")
            print(f"Duración total: {self.video_duration:.2f} segundos")
            print(f"Frames procesados: {self.total_frames_processed}")
            for label, stats in self.processing_metrics['detection_results'].items():
                print(f"{label}: {stats['qty_frames_detected']} detecciones, {stats['frames_appearance_in_percentage']:.1f}%")
            
            logger.info(f"Video completado. Frames procesados: {frame_count}")
            print(f"Video completado. Frames procesados: {frame_count}")
            return True
            
        except AttributeError as e:
            if "'NoneType' object has no attribute 'isnumeric'" in str(e):
                logger.warning("Error conocido de YOLO con YouTube, intentando descargar video...")
                print("Error conocido de YOLO con YouTube, intentando descargar video...")
                raise Exception("Error de isnumeric - necesita descarga") from e
            else:
                raise
        except Exception as e:
            logger.error(f"Error al procesar el video con stream: {e}")
            print(f"Error al procesar el video con stream: {e}")
            return False
    
    def process_downloaded_video(self):
        """Procesar video descargado (método de respaldo)"""
        logger.info("Intentando descargar el video primero...")
        print("Intentando descargar el video primero...")
        downloaded_path = self.download_youtube_video(self.source)
        
        if downloaded_path:
            self.downloaded_path = downloaded_path
            
            # Procesar el video descargado usando el método stream de YOLO
            try:
                # Guardar el source original y temporalmente usar el descargado
                original_source = self.source
                self.source = downloaded_path
                
                result = self.process_with_yolo_stream()
                
                # Restaurar el source original
                self.source = original_source
                
                # Limpiar archivo temporal
                try:
                    os.remove(downloaded_path)
                    logger.info("Archivo temporal eliminado")
                    print("Archivo temporal eliminado")
                except:
                    pass
                    
                return result
            except Exception as e:
                logger.error(f"Error al procesar video descargado: {e}")
                print(f"Error al procesar video descargado: {e}")
                return False
        else:
            logger.error("No se pudo descargar el video")
            print("Error: No se pudo descargar el video")
            return False
    
    def process_video(self):
        """Método principal que intenta procesar con stream primero"""
        if self.source.startswith(('http', 'www')):
            logger.info("Intentando procesar con YOLO stream...")
            print("Intentando procesar con YOLO stream...")
            
            # Primero intentar con el método stream de YOLO
            try:
                return self.process_with_yolo_stream()
            except Exception as e:
                if "Error de isnumeric - necesita descarga" in str(e):
                    logger.warning("Error específico de YouTube detectado, intentando descargar...")
                    print("Error específico de YouTube detectado, intentando descargar...")
                    return self.process_downloaded_video()
                else:
                    logger.error(f"Falló procesamiento con stream: {e}")
                    print(f"Falló procesamiento con stream: {e}")
                    return self.process_downloaded_video()
        else:
            # Archivo local - usar el método stream
            return self.process_with_yolo_stream()

# Uso
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
        print(f"\n{'='*60}")
        print(f"Procesando video recibido por argumento: {video_url}")
        print(f"{'='*60}")
        processor = VideoProcessor("best.pt", video_url)
        success = processor.process_video()
        if success:
            metrics = processor.get_processing_metrics()
            print("\nDatos listos para guardar en BD:")
            print(f"Tipo: {metrics['video_info']['type']}")
            print(f"Nombre: {metrics['video_info']['name']}")
            print(f"Duración: {metrics['video_info']['total_video_time_segs']} segundos")
            print("Detecciones:", metrics['detection_results'])
            processor.send_results_to_backend()
            logger.success(f"Éxito con {video_url}")
            print(f"✓ Éxito con {video_url}")
        else:
            logger.warning(f"✗ Falló {video_url}")
            print(f"✗ Falló {video_url}")
    else:
        print("Por favor, proporciona una URL de YouTube como argumento al ejecutar el script.")


# Videos probados:
    # processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=oaExWXqwkqg") # 👍 60 segundos
    # processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=FKdlUnVvX7Q") # 20 segundos lo abre y cierra casi inmediatamente y no lo procesa entero
    # processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=siO1ZpNYNN4") # 👍40 segundos
    # processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=75k9zt8iad0") # 31 segundos  error AttributeError: 'NoneType' object has no attribute 'isnumeric'
    # processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=j5b80kjVQcU") # 47 segundos error AttributeError: 'NoneType' object has no attribute 'isnumeric'
    # processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=aPgSFJt2lqE") # 20 segundos lo abre y cierra casi inmediatamente y no lo procesa entero
    # processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=xw6fehnxMjU") # 10 segundos error AttributeError: 'NoneType' object has no attribute 'isnumeric'