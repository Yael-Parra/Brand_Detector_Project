from loguru import logger
from ultralytics import YOLO
import cv2
import time
import os
from pathlib import Path
import yt_dlp
import threading
import traceback
from backend.database import db_insertion_data as db

logger.add("logs/video_processor.log", rotation="5 MB")

class VideoProcessor:
    def __init__(self, model_path: str = "best_v5.pt"):
        self.model = YOLO(model_path)
        self.video_path = None
        self.cap = None
        self.thread = None
        self.paused = False
        self.stop_requested = False
        self.progress_callback = None

        # métricas
        self.metrics = {
            "fps": 0,
            "total_frames": 0,
            "duration_secs": 0,
            "detections": {},
        }

    def download_video(self, url: str) -> str:
        downloads_dir = Path("data/uploads")
        downloads_dir.mkdir(parents=True, exist_ok=True)
        ydl_opts = {
            "outtmpl": str(downloads_dir / "%(title)s.%(ext)s"),
            "format": "mp4/bestvideo+bestaudio/best",
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        logger.info(f"Video descargado: {filename}")
        return filename

    def set_status_callback(self, callback):
        self.progress_callback = callback

    def start(self, url: str):
        """Inicia procesamiento en hilo separado"""
        logger.info(f"Iniciando procesamiento para: {url}")
        self.video_path = self.download_video(url)
        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            raise RuntimeError("No se pudo abrir el video descargado")

        self.metrics["fps"] = self.cap.get(cv2.CAP_PROP_FPS)
        self.metrics["total_frames"] = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.metrics["duration_secs"] = (
            self.metrics["total_frames"] / self.metrics["fps"]
            if self.metrics["fps"] > 0 else 0
        )

        self.thread = threading.Thread(target=self._process_video, daemon=True)
        self.thread.start()
        logger.info("Hilo de procesamiento iniciado")

    def _process_video(self):
        conn = None
        id_video = None
        try:
            conn = db.connect()
            id_video = db.insert_video(
                conn,
                vtype="url",
                name=os.path.basename(self.video_path),
                total_secs=self.metrics["duration_secs"],
            )

            frame_count = 0
            while self.cap.isOpened() and not self.stop_requested:
                if self.paused:
                    time.sleep(0.1)
                    continue

                ret, frame = self.cap.read()
                if not ret:
                    break

                frame_count += 1
                results = self.model(frame, verbose=False)
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    label = self.model.names[cls_id]
                    self.metrics["detections"].setdefault(label, 0)
                    self.metrics["detections"][label] += 1

                # Callback de progreso
                if self.progress_callback:
                    progress = frame_count / self.metrics["total_frames"] * 100
                    self.progress_callback({
                        "frame_count": frame_count,
                        "progress": progress,
                        "detections": self.metrics["detections"],
                    })

                time.sleep(max(0.001, 1.0 / self.metrics["fps"]))

            # Insertar detecciones finales
            for label, qty in self.metrics["detections"].items():
                percent = qty / self.metrics["total_frames"] * 100 if self.metrics["total_frames"] > 0 else 0
                db.insert_detection(
                    conn,
                    id_video=id_video,
                    label_name=label,
                    qty_frames_detected=qty,
                    fps=self.metrics["fps"],
                    percent=percent,
                )
            logger.info(f"Procesamiento completado para video_id={id_video}")

        except Exception as e:
            logger.error(f"Error en procesamiento: {e}")
            logger.error(traceback.format_exc())
        finally:
            if self.cap:
                self.cap.release()
            if conn:
                db.disconnect(conn)
            if self.video_path and os.path.exists(self.video_path):
                os.remove(self.video_path)
            if self.progress_callback:
                self.progress_callback({"status": "completed", "metrics": self.metrics})

    # Controles
    def pause(self):
        self.paused = True
        logger.info("Procesamiento pausado")

    def resume(self):
        self.paused = False
        logger.info("Procesamiento reanudado")

    def stop(self):
        self.stop_requested = True
        if self.thread and self.thread.is_alive():
            self.thread.join()
        logger.info("Procesamiento detenido")



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