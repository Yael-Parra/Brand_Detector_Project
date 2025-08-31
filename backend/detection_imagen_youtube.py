from ultralytics import YOLO
import cv2
import imutils
# Cargamos el modelo YOLO
# model = YOLO("yolo11n.pt")
# model = YOLO("best.pt")
model = YOLO("../runs/detect/train5/weights/best.pt")

# Especificar la URL del video
# source = "https://www.youtube.com/watch?v=SWo_7mELz-o&t"
source = "https://www.youtube.com/watch?v=PUFVBp8TT1w"

# Realizamos la inferencia de YOLO ... aki se tiene que añadir las configuraciones
results = model(source, stream=True)


for result in results:
    annotated_frame = result.plot()
    annotated_frame = imutils.resize(annotated_frame, width=640)
    # Display the annotated frame
    cv2.imshow("YOLO Inference", annotated_frame)
    # El ciclo se rompe al presionar "Esc"
    if cv2.waitKey(1) & 0xFF == 27:
        break
cv2.destroyAllWindows()
