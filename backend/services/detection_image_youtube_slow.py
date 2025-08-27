from ultralytics import YOLO
import cv2
import imutils
import time

class VideoProcessor:
    def __init__(self, model_path, video_source):
        self.model = YOLO(model_path)
        self.source = video_source
        self.speed_multiplier = 1.0
        self.paused = False
        self.frame_skip = 0
        self.current_frame = 0
        
    def process_video(self):
        # Usar el método stream de YOLO para mantener los logs
        results = self.model(self.source, stream=True, verbose=True)
        
        frame_count = 0
        start_time = time.time()
        
        for result in results:
            self.current_frame += 1
            
            # Saltar frames según la velocidad
            if self.speed_multiplier > 1.0 and frame_count % int(self.speed_multiplier) != 0:
                continue
                
            if not self.paused:
                frame_count += 1
                
                # Obtener el frame anotado
                annotated_frame = result.plot()
                annotated_frame = imutils.resize(annotated_frame, width=640)
                
                # Mostrar información en el frame
                cv2.putText(annotated_frame, f"Speed: {self.speed_multiplier}x", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"Paused: {'Yes' if self.paused else 'No'}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"Frame: {frame_count}", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow("YOLO Video Processing", annotated_frame)
            
            # Control de teclas
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # Esc
                break
            elif key == ord(' '):  # Espacio para pausar/reanudar
                self.paused = not self.paused
                print(f"Video {'pausado' if self.paused else 'reanudado'}")
            elif key == ord('1'):  # Velocidad normal
                self.speed_multiplier = 1.0
                print("Velocidad: 1x")
            elif key == ord('2'):  # 2x
                self.speed_multiplier = 2.0
                print("Velocidad: 2x")
            elif key == ord('4'):  # 4x
                self.speed_multiplier = 4.0
                print("Velocidad: 4x")
            elif key == ord('0'):  # 0.5x (más lento)
                self.speed_multiplier = 0.5
                print("Velocidad: 0.5x")
                # Para velocidad más lenta, mostramos cada 2 frames
                self.frame_skip = 2
            
            # Si está pausado, mantener un pequeño delay
            if self.paused:
                time.sleep(0.1)
        
        cv2.destroyAllWindows()

# Uso
processor = VideoProcessor("best.pt", "https://www.youtube.com/watch?v=oaExWXqwkqg")
processor.process_video()