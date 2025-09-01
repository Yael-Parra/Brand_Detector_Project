from ultralytics import YOLO
import cv2
import time

# Cargamos el modelo YOLO
model = YOLO("best2.pt")
#model = YOLO("yolo11n.pt")

# Diccionario para almacenar el tiempo de aparición de cada etiqueta
label_times = {}
# Diccionario para almacenar el conteo de frames por etiqueta
label_frames = {}

# Variables para el seguimiento del tiempo
current_labels = set()
last_time = time.time()
start_time = time.time()
total_frames = 0

# Cargamos el video de entrada
cap = cv2.VideoCapture(0)

try:
    while cap.isOpened():
        # Leemos el frame del video
        ret, frame = cap.read()
        if not ret:
            break
            
        # Incrementamos el contador de frames
        total_frames += 1
            
        # Calculamos el tiempo transcurrido desde el último frame
        current_time = time.time()
        elapsed_time = current_time - last_time
        last_time = current_time
        
        # Realizamos la inferencia de YOLO sobre el frame
        results = model(frame)
        
        # Obtenemos las etiquetas detectadas en este frame
        detected_labels = set()
        for r in results[0].boxes:
            if r.cls is not None and len(r.cls) > 0:
                label = model.names[int(r.cls[0])]
                detected_labels.add(label)
                
        # Actualizamos el tiempo y frames para las etiquetas detectadas
        for label in detected_labels:
            if label not in label_times:
                label_times[label] = 0
                label_frames[label] = 0
            label_times[label] += elapsed_time
            label_frames[label] += 1
        
        # Extraemos los resultados para visualización
        annotated_frame = results[0].plot()
        
        # Mostramos el tiempo acumulado para cada etiqueta en el frame
        y_pos = 30
        for label, total_time in label_times.items():
            text = f"{label}: {total_time:.2f}s - {label_frames[label]} frames"
            cv2.putText(annotated_frame, text, (10, y_pos), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_pos += 30
        
        # Visualizamos los resultados
        cv2.imshow("YOLO Inference", annotated_frame)
        
        # El ciclo se rompe al presionar "Esc"
        if cv2.waitKey(1) & 0xFF == 27:
            break
    
    # Calculamos el tiempo total del video
    total_time = time.time() - start_time
            
    # Al finalizar, mostramos el resumen de tiempos
    print("\nResumen de tiempo de aparición de etiquetas:")
    for label, total_label_time in label_times.items():
        frames_count = label_frames[label]
        percentage = (total_label_time / total_time) * 100 if total_time > 0 else 0
        print(f"{label}: {total_label_time:.2f} segundos, {frames_count} frames, {percentage:.2f}% del video")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    cap.release()
    cv2.destroyAllWindows()