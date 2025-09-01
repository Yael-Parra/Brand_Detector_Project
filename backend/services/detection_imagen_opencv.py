import cv2
from ultralytics import YOLO
import base64

def predict_image(image_path: str):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")
    model = YOLO("best.pt")
    results = model(image)
    detections = []
    for result in results:
        names = [result.names[int(label)] for label in result.boxes.cls]
        xyxys = result.boxes.xyxy
        for i, xyxy in enumerate(xyxys):
            x1, y1 = int(xyxy[0]), int(xyxy[1])
            x2, y2 = int(xyxy[2]), int(xyxy[3])
            detections.append({
                "bbox_xyxy": [x1, y1, x2, y2],
                "label": names[i],
            })
        # Anotar imagen
        annotated = result.plot()
        ok, buf = cv2.imencode(".jpg", annotated)
        img_b64 = base64.b64encode(buf).decode("ascii") if ok else None
        break
    return {"detections": detections}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python detection_imagen_opencv.py <ruta_imagen>")
    else:
        result = predict_image(sys.argv[1])
        print(result)