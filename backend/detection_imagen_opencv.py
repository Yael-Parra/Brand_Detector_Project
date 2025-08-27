from ultralytics import YOLO
import cv2
# Cargamos la imagen de entrada
image = cv2.imread("data/perrito.bmp")
# Cargamos el modelo YOLO
model = YOLO("yolo11n.pt")

# Realizamos la inferencia sobre la imagen
results = model(image)
for result in results:
    print(result)
    # Extraemos los nombres de las clases detectadas
    names = [result.names[int(label)] for label in result.boxes.cls]
    print(names)
    # Extraemos las coordenadas de las cajas delimitadoras
    xyxys = result.boxes.xyxy
    for i, xyxy in enumerate(xyxys):
        x1, y1 = int(xyxy[0]), int(xyxy[1])
        x2, y2 = int(xyxy[2]), int(xyxy[3])
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 255), 2)
        cv2.putText(image, names[i], (x1, y1 -5), 1, 1.1, (0, 255, 255), 2)
    cv2.imshow("Image", image)
    cv2.waitKey(0) #se visualiza hasta q se toca cualquier tecla
cv2.destroyAllWindows()