from ultralytics import YOLO
import cv2
import time
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import requests
import threading

# Safe imports with auto-installation
try:
    import imutils
except ImportError:
    print("Installing imutils...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imutils"])
    import imutils

try:
    from loguru import logger
except ImportError:
    print("Installing loguru...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "loguru==0.7.3"])
    from loguru import logger

try:
    import pytubefix
except ImportError:
    print("Installing pytubefix...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pytubefix>=6.5.2"])
    import pytubefix

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
        self.model = YOLO("best_v5.pt")
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
        self.total_detections = 0
        self.video_duration = 0
        self.processing_metrics = {}
        
        # Callback para reportar estado
        self.status_callback = None
        
    def set_status_callback(self, callback_fn):
        """Establecer una función de callback para reportar el estado del procesamiento"""
        self.status_callback = callback_fn
    
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
                
        # Actualizar el contador total de detecciones
        self.total_detections = sum(data['count'] for data in self.detection_data.values())
    
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
        
    def download_youtube_video(self, url):
        """Descargar video de YouTube usando yt-dlp con instalación automática"""
        logger.info("Intentando descargar video de YouTube...")
        print("Descargando video de YouTube...")
        
        # Crear carpeta temporal si no existe
        temp_dir = Path("temp_videos")
        temp_dir.mkdir(exist_ok=True)
        
        # Nombre de archivo temporal
        output_path = temp_dir / "temp_video.%(ext)s"
        
        try:
            # Intentar usar yt-dlp como módulo Python primero
            try:
                import yt_dlp
                
                # Opciones para yt-dlp
                ydl_opts = {
                    'format': 'best[height<=720]',  # Calidad máxima 720p
                    'outtmpl': str(output_path),
                    'noplaylist': True,
                    'quiet': False,
                    'no_warnings': False
                }
                
                # Descargar el video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Buscar el archivo descargado
                for file in temp_dir.glob("temp_video.*"):
                    logger.info(f"Video descargado: {file}")
                    print(f"Video descargado exitosamente: {file}")
                    return str(file)
                    
            except ImportError:
                # Si no está instalado como módulo, intentar instalarlo
                print("Instalando yt-dlp...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
                
                # Reintentar después de instalar
                import yt_dlp
                
                # Opciones para yt-dlp
                ydl_opts = {
                    'format': 'best[height<=720]',  # Calidad máxima 720p
                    'outtmpl': str(output_path),
                    'noplaylist': True,
                    'quiet': False,
                    'no_warnings': False
                }
                
                # Descargar el video
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Buscar el archivo descargado
                for file in temp_dir.glob("temp_video.*"):
                    logger.info(f"Video descargado: {file}")
                    print(f"Video descargado exitosamente: {file}")
                    return str(file)
            
            except Exception as e:
                # Si falla el método de módulo, intentar con el comando
                logger.warning(f"Error al usar yt-dlp como módulo: {e}. Intentando como comando...")
                print(f"Error al usar yt-dlp como módulo: {e}. Intentando como comando...")
                
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
                    raise Exception(f"Error en yt-dlp: {result.stderr}")
                
        except FileNotFoundError:
            # Intentar instalar yt-dlp y reintentar
            try:
                logger.info("yt-dlp no está instalado. Instalando automáticamente...")
                print("yt-dlp no está instalado. Instalando automáticamente...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
                
                # Reintentar después de instalar
                return self.download_youtube_video(url)
            except Exception as e:
                logger.error(f"Error al instalar yt-dlp: {e}")
                print(f"Error al instalar yt-dlp: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error al descargar: {e}")
            print(f"Error al descargar: {e}")
            return None
    
    def process_with_yolo_stream(self, video_path=None):
        """Procesar video usando el método stream de YOLO a velocidad normal"""
        print("=== CONTROLES ===")
        print("ESC: Salir")
        print("ESPACIO: Pausar/Reanudar")
        print("==================")
        print("Iniciando procesamiento a velocidad normal")
        
        # Inicializar métricas
        self.start_time = time.time()
        self.detection_data = {}
        self.total_frames_processed = 0
        fps = 0
        frame_times = []
        
        # Variables para sincronización entre hilos
        self.processing_active = True
        self.current_result = None
        self.result_ready = False
        self.paused = False
        
        try:
            # Iniciar el procesamiento en un hilo separado
            processing_thread = threading.Thread(target=self._process_frames_thread)
            processing_thread.daemon = True
            processing_thread.start()
            
            # Abrir el video con OpenCV para reproducción
            source = video_path if video_path is not None else self.source
            
            if source.startswith(('http', 'www')):
                # Para URLs de YouTube, primero intentamos descargar
                downloaded_path = self.download_youtube_video(source)
                if downloaded_path:
                    cap = cv2.VideoCapture(downloaded_path)
                else:
                    print("No se pudo descargar el video. Intentando reproducir directamente.")
                    cap = cv2.VideoCapture(source)
            else:
                cap = cv2.VideoCapture(source)
            
            if not cap.isOpened():
                raise Exception("No se pudo abrir el video")
            
            # Obtener FPS del video original para reproducción a velocidad normal
            original_fps = cap.get(cv2.CAP_PROP_FPS)
            if original_fps <= 0:
                original_fps = 30  # Valor por defecto si no se puede determinar
            
            frame_delay = 1.0 / original_fps
            frame_count = 0
            last_time = time.time()
            
            while cap.isOpened() and self.processing_active:
                if not self.paused:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    frame_count += 1
                    
                    # Calcular FPS en tiempo real
                    current_time = time.time()
                    frame_times.append(current_time)
                    
                    # Mantener solo los últimos 30 frames para cálculo de FPS
                    if len(frame_times) > 30:
                        frame_times.pop(0)
                    
                    # Calcular FPS basado en los últimos frames
                    if len(frame_times) > 1:
                        fps = len(frame_times) / (frame_times[-1] - frame_times[0])
                    
                    # Mostrar el frame original o el procesado si está disponible
                    display_frame = frame.copy()
                    
                    # Si hay un resultado de detección disponible, mostrarlo
                    if self.result_ready and self.current_result is not None:
                        # Usar el frame anotado del procesamiento
                        display_frame = self.current_result.copy()
                        self.result_ready = False
                    
                    # Redimensionar para visualización
                    display_frame = imutils.resize(display_frame, width=640)
                    
                    # Mostrar información en el frame
                    cv2.putText(display_frame, f"Frame: {frame_count}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Paused: {'Yes' if self.paused else 'No'}", (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    cv2.imshow("YOLO Video Processing", display_frame)
                    
                    # Control de velocidad para mantener FPS original
                    elapsed = time.time() - last_time
                    sleep_time = max(0, frame_delay - elapsed)
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    last_time = time.time()
                else:
                    # Si está pausado, mostrar el último frame
                    if 'display_frame' in locals():
                        paused_frame = display_frame.copy()
                        cv2.putText(paused_frame, "PAUSED", (display_frame.shape[1]//2 - 60, display_frame.shape[0]//2), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                        cv2.imshow("YOLO Video Processing", paused_frame)
                    time.sleep(0.1)
                
                # Control de teclas
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # Esc
                    print("Saliendo...")
                    break
                elif key == ord(' '):  # Espacio para pausar/reanudar
                    self.paused = not self.paused
                    print(f"Video {'pausado' if self.paused else 'reanudado'}")
            
            # Esperar a que termine el hilo de procesamiento
            self.processing_active = False
            if processing_thread.is_alive():
                processing_thread.join(timeout=5.0)
            
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
            
        except Exception as e:
            logger.error(f"Error al procesar el video con stream: {e}")
            print(f"Error al procesar el video con stream: {e}")
            return False
        
        finally:
            if 'cap' in locals() and cap is not None:
                cap.release()
            cv2.destroyAllWindows()
            self.processing_active = False
    
    def _process_frames_thread(self):
        """Hilo para procesar frames con YOLO en segundo plano"""
        try:
            # Usar el método stream de YOLO
            results = self.model(self.source, stream=True, verbose=False)
            
            for result in results:
                if not self.processing_active:
                    break
                    
                if not self.paused:
                    self.total_frames_processed += 1
                    
                    # Actualizar estadísticas de detección
                    self.update_detection_stats(result)
                    
                    # Obtener el frame anotado y guardarlo para visualización
                    annotated_frame = result.plot()
                    self.current_result = annotated_frame
                    self.result_ready = True
                    
                    # Actualizar el estado si hay un callback configurado
                    if self.status_callback and self.total_frames_processed % 10 == 0:  # Actualizar más frecuentemente
                        # Obtener el total de frames si es posible
                        try:
                            cap = cv2.VideoCapture(self.source)
                            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                            cap.release()
                            progress = (self.total_frames_processed / total_frames * 100) if total_frames > 0 else 0
                        except:
                            total_frames = 0
                            progress = 0
                            
                        self.status_callback({
                            'frame_count': self.total_frames_processed,
                            'total_frames': total_frames,
                            'progress': progress,
                            'detections': self.total_detections
                        })
                
                # Pequeña pausa para no saturar la CPU
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error en el hilo de procesamiento: {e}")
            print(f"Error en el hilo de procesamiento: {e}")
            self.processing_active = False
            
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
        
        finally:
            cv2.destroyAllWindows()
    
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
                except Exception as e:
                    logger.warning(f"No se pudo eliminar el archivo temporal: {e}")
                    print(f"Advertencia: No se pudo eliminar el archivo temporal: {e}")
                    
                return result
            except Exception as e:
                logger.error(f"Error al procesar video descargado: {e}")
                print(f"Error al procesar video descargado: {e}")
                return False
        else:
            logger.error("No se pudo descargar el video")
            print("Error: No se pudo descargar el video")
            return False
    
    def process_video(self, url=None):
        """Método principal que intenta procesar con stream primero"""
        try:
            # Si se proporciona una URL, usarla; de lo contrario, usar self.source
            source = url if url is not None else self.source
            self.source = source  # Actualizar la fuente para uso en otros métodos
            
            # Para URLs de YouTube, siempre intentamos descargar primero para mejor rendimiento
            if source.startswith(('http', 'www')) and ('youtube.com' in source or 'youtu.be' in source):
                logger.info("URL de YouTube detectada, descargando para mejor rendimiento...")
                print("Procesando video de YouTube...")
                return self.process_downloaded_video()
            
            # Para otras URLs, intentamos primero con stream
            elif source.startswith(('http', 'www')):
                logger.info("Intentando procesar con YOLO stream...")
                print("Intentando procesar URL directamente...")
                try:
                    return self.process_with_yolo_stream()
                except Exception as e:
                    logger.error(f"Falló procesamiento con stream: {e}")
                    print(f"No se pudo procesar la URL directamente. Intentando descargar...")
                    return self.process_downloaded_video()
            
            else:
                # Es un archivo local, procesarlo directamente
                logger.info("Procesando archivo local...")
                print("Procesando archivo local...")
                return self.process_with_yolo_stream()
                
        except Exception as e:
            print(f"Error al procesar el video: {e}")
            logger.error(f"Error al procesar el video: {e}")
            return False

# Uso
if __name__ == "__main__":

    import json  # Importa la librería json
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
        
        processor = VideoProcessor("../best.pt", video_url)
        success = processor.process_video()
        
        # Prepara el objeto de respuesta JSON
        response_data = {
            "success": success,
            "url": video_url,
            "detections": {}
        }
        
        if success:
            metrics = processor.get_processing_metrics()
            # Si hay detecciones, las añade al objeto de respuesta
            if 'detection_results' in metrics and metrics['detection_results']:
                response_data["detections"] = metrics['detection_results']
            
            # También puedes añadir más datos si los necesitas, como la duración
            response_data["duration_sec"] = metrics['video_info']['total_video_time_segs']
            response_data["frames_processed"] = metrics['total_frames_processed']

            logger.success(f"Éxito con {video_url}")
        else:
            logger.warning(f"✗ Falló {video_url}")

        # Imprime el objeto JSON en la salida estándar
        print(json.dumps(response_data))
        
    else:
        print("Por favor, proporciona una URL de YouTube como argumento al ejecutar el script.")

    import sys
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
        print(f"\n{'='*60}")
        print(f"Procesando video recibido por argumento: {video_url}")
        print(f"{'='*60}")
        processor = VideoProcessor("../best.pt", video_url)
        success = processor.process_video()
        if success:
            metrics = processor.get_processing_metrics()
            print("\nDatos listos para guardar en BD:")
            print(f"Tipo: {metrics['video_info']['type']}\n")
            print(f"Nombre: {metrics['video_info']['name']}\n")
            print(f"Duración: {metrics['video_info']['total_video_time_segs']} segundos")
            print("Detecciones:", metrics['detection_results'], "\n")
            processor.send_results_to_backend()
            logger.success(f"Éxito con {video_url}")
            print(f"✓ Éxito con {video_url}\n")
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