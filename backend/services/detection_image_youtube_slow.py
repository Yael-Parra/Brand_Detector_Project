from ultralytics import YOLO
import cv2
import imutils
import time
import os
import subprocess
import sys
from pathlib import Path
from loguru import logger
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
            logger.error("yt-dlp no está instalado. Instálalo con: pip install yt-dlp")
            print("Error: yt-dlp no está instalado. Instálalo con: pip install yt-dlp")
            return None
        except Exception as e:
            logger.error(f"Error al descargar: {e}")
            print(f"Error al descargar: {e}")
            return None
    
    def process_with_yolo_stream(self):
        """Procesar video usando el método stream de YOLO (como en la versión 1)"""
        print("=== CONTROLES ===")
        print("ESC: Salir")
        print("ESPACIO: Pausar/Reanudar")
        print("1: Velocidad normal (1x)")
        print("2: Velocidad rápida (2x)")
        print("4: Velocidad muy rápida (4x)")
        print("0: Velocidad lenta (0.5x)")
        print("3: Velocidad muy lenta (0.25x)")
        print("5: Velocidad súper lenta (0.1x)")
        print("6: Velocidad ultra lenta (0.05x)")
        print("==================")
        print(f"Iniciando con velocidad: {self.speed_multiplier}x")
        
        # Inicializar métricas
        self.start_time = time.time()
        self.detection_data = {}
        self.total_frames_processed = 0
        last_fps_update = time.time()
        fps = 0
        frame_times = []
        
        try:
            # Usar el método stream de YOLO (como en la versión 1)
            results = self.model(self.source, stream=True, verbose=True)
            
            frame_count = 0
            start_time = time.time()
            
            for result in results:
                self.current_frame += 1
                
                # Control de velocidad mediante saltos de frames
                if self.speed_multiplier > 1.0:
                    self.frame_skip_counter += 1
                    if self.frame_skip_counter % int(self.speed_multiplier) != 0:
                        continue
                
                if not self.paused:
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
                    
                    # Obtener el frame anotado
                    annotated_frame = result.plot()
                    annotated_frame = imutils.resize(annotated_frame, width=640)
                    
                    # Mostrar información en el frame (ACTUALIZADA EN TIEMPO REAL)
                    cv2.putText(annotated_frame, f"Speed: {self.speed_multiplier}x", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(annotated_frame, f"Paused: {'Yes' if self.paused else 'No'}", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(annotated_frame, f"Frame: {frame_count}", (10, 90), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10, 120), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    cv2.imshow("YOLO Video Processing", annotated_frame)
                    
                    # CONTROL DE VELOCIDAD para velocidades lentas
                    if self.speed_multiplier < 1.0:
                        target_delay = (1.0 / (30 * self.speed_multiplier)) - 0.01  # Asumiendo 30 FPS
                        if target_delay > 0:
                            time.sleep(target_delay)
                
                else:
                    # SI ESTÁ PAUSADO: Mostrar el último frame pero con texto actualizado
                    if 'annotated_frame' in locals():
                        # Crear una copia del último frame con el texto de pausa actualizado
                        paused_frame = annotated_frame.copy()
                        cv2.putText(paused_frame, f"Speed: {self.speed_multiplier}x", (10, 30), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(paused_frame, f"Paused: {'Yes' if self.paused else 'No'}", (10, 60), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(paused_frame, f"Frame: {frame_count}", (10, 90), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(paused_frame, f"FPS: {fps:.1f}", (10, 120), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
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
                    # Forzar actualización inmediata del texto de pausa
                    continue
                elif key == ord('1'):  # Velocidad normal
                    self.speed_multiplier = 1.0
                    self.frame_skip_counter = 0
                    print("Velocidad: 1x (Normal)")
                elif key == ord('2'):  # 2x
                    self.speed_multiplier = 2.0
                    self.frame_skip_counter = 0
                    print("Velocidad: 2x (Rápida)")
                elif key == ord('4'):  # 4x
                    self.speed_multiplier = 4.0
                    self.frame_skip_counter = 0
                    print("Velocidad: 4x (Muy rápida)")
                elif key == ord('0'):  # 0.5x (más lento)
                    self.speed_multiplier = 0.5
                    print("Velocidad: 0.5x (Lenta)")
                elif key == ord('3'):
                    self.speed_multiplier = 0.25
                    print("Velocidad: 0.25x (Muy lenta)")
                elif key == ord('5'):
                    self.speed_multiplier = 0.1
                    print("Velocidad: 0.1x (Súper lenta)")
                elif key == ord('6'):
                    self.speed_multiplier = 0.05
                    print("Velocidad: 0.05x (Ultra lenta)")
            
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