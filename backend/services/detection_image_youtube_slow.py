from ultralytics import YOLO
import cv2
import time
import os
import subprocess
import sys
import traceback
import threading
from pathlib import Path
import yt_dlp
from loguru import logger

from backend.database import db_insertion_data as db


class VideoProcessor:
    def __init__(self, model_path: str = "yolov8n.pt"):
        logger.info("Inicializando VideoProcessor con modelo: {}", model_path)
        self.model = YOLO(model_path)
        self.video_path = None
        self.cap = None
        self.thread = None
        self.paused = False
        self.speed = 1.0
        self.stop_requested = False
        self.progress_callback = None

        self.metrics = {
            "fps": 0,
            "total_frames": 0,
            "duration_secs": 0,
            "detections": {},
        }

    def download_video(self, url: str) -> str:
        """Descarga el video en data/uploads y devuelve la ruta."""
        logger.info("Iniciando descarga de video: {}", url)
        downloads_dir = Path("data/uploads")
        downloads_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "outtmpl": str(downloads_dir / "%(title)s.%(ext)s"),
            "format": "mp4/bestvideo+bestaudio/best",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                logger.success("Descarga completada: {}", filename)
                print(f"[Download] Video descargado en {filename}")
                return filename
        except Exception as e:
            logger.error("Fallo al descargar video: {}", e)
            traceback.print_exc()
            raise

    def start(self, url: str, progress_callback=None):
        logger.info("Iniciando procesamiento del video: {}", url)
        self.progress_callback = progress_callback
        self.video_path = self.download_video(url)

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            logger.error("No se pudo abrir el video: {}", self.video_path)
            raise RuntimeError("No se pudo abrir el video descargado")

        self.metrics["fps"] = self.cap.get(cv2.CAP_PROP_FPS)
        self.metrics["total_frames"] = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.metrics["duration_secs"] = (
            self.metrics["total_frames"] / self.metrics["fps"]
            if self.metrics["fps"] > 0 else 0
        )

        logger.info(
            "Video abierto con FPS={} TotalFrames={} Duración={:.2f}s",
            self.metrics["fps"],
            self.metrics["total_frames"],
            self.metrics["duration_secs"]
        )

        self.thread = threading.Thread(target=self._process_video, daemon=True)
        self.thread.start()

    def _process_video(self):
        conn = None
        id_video = None
        try:
            logger.info("Conectando a la base de datos...")
            conn = db.connect()
            logger.success("Conexión establecida con la base de datos")

            id_video = db.insert_video(
                conn,
                vtype="youtube",
                name=os.path.basename(self.video_path),
                total_secs=self.metrics["duration_secs"],
            )
            logger.info("Video insertado en BD con id_video={}", id_video)

            frame_count = 0
            while self.cap.isOpened() and not self.stop_requested:
                if self.paused:
                    logger.debug("Video en pausa, esperando...")
                    time.sleep(0.1)
                    continue

                ret, frame = self.cap.read()
                if not ret:
                    logger.info("No se pudo leer más frames. Terminando.")
                    break

                frame_count += 1
                logger.debug("Procesando frame {}", frame_count)

                try:
                    results = self.model(frame, verbose=False)
                    boxes = results[0].boxes

                    for box in boxes:
                        cls_id = int(box.cls[0])
                        label = self.model.names[cls_id]
                        self.metrics["detections"].setdefault(label, 0)
                        self.metrics["detections"][label] += 1

                    logger.debug("Frame {} → detecciones acumuladas: {}", frame_count, self.metrics["detections"])
                except Exception as det_err:
                    logger.error("Error procesando frame {}: {}", frame_count, det_err)
                    traceback.print_exc()

                if self.progress_callback:
                    progress = frame_count / self.metrics["total_frames"] * 100
                    self.progress_callback({
                        "frame": frame_count,
                        "progress": progress,
                        "detections": self.metrics["detections"],
                    })
                    logger.debug("Progreso enviado: {:.2f}%", progress)

                if self.speed > 0:
                    time.sleep(max(0.001, 1.0 / self.metrics["fps"] / self.speed))

            logger.info("Procesamiento terminado. Insertando métricas finales en BD...")
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
                logger.success("Métrica insertada en BD: {} = {} detecciones ({:.2f}%)", label, qty, percent)

        except Exception as e:
            logger.error("[VideoProcessor] Error principal: {}", e)
            traceback.print_exc()
        finally:
            if self.cap:
                self.cap.release()
                logger.info("Captura liberada")
            if conn:
                db.disconnect(conn)
                logger.info("Conexión a BD cerrada")
            if self.video_path and os.path.exists(self.video_path):
                os.remove(self.video_path)
                logger.info("Archivo temporal eliminado: {}", self.video_path)

            if self.progress_callback:
                self.progress_callback({"status": "finished", "metrics": self.metrics})
                logger.info("Callback final enviado con métricas")

    # --- controles ---
    def pause(self):
        logger.info("Video pausado")
        self.paused = True

    def resume(self):
        logger.info("Video reanudado")
        self.paused = False

    def set_speed(self, multiplier: float):
        logger.info("Velocidad ajustada a {}x", multiplier)
        self.speed = max(0.1, multiplier)

    def stop(self):
        logger.info("Se solicitó detener el procesamiento")
        self.stop_requested = True
        if self.thread and self.thread.is_alive():
            self.thread.join()
            logger.info("Hilo de procesamiento detenido")


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