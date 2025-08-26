import cv2
import os

# Carpeta de imágenes y etiquetas
IMG_DIR = "training-images/images/train"
LABEL_DIR = "training-images/labels/train"
os.makedirs(LABEL_DIR, exist_ok=True)

# Clase única: Mercedes
CLASS_ID = 0

# Variables globales para el mouse callback
refPt = []
cropping = False

def click_and_crop(event, x, y, flags, param):
    global refPt, cropping, image, clone, label_path

    if event == cv2.EVENT_LBUTTONDOWN:
        refPt = [(x, y)]
        cropping = True

    elif event == cv2.EVENT_LBUTTONUP:
        refPt.append((x, y))
        cropping = False

        cv2.rectangle(image, refPt[0], refPt[1], (0, 255, 0), 2)
        cv2.imshow("image", image)

        # Guardar en formato YOLO
        x_min, y_min = refPt[0]
        x_max, y_max = refPt[1]
        h, w = clone.shape[:2]
        x_center = ((x_min + x_max) / 2) / w
        y_center = ((y_min + y_max) / 2) / h
        bw = (x_max - x_min) / w
        bh = (y_max - y_min) / h

        with open(label_path, "w") as f:
            f.write(f"{CLASS_ID} {x_center} {y_center} {bw} {bh}\n")

# Lista de imágenes
images = [f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg", ".png"))]

for img_name in images:
    img_path = os.path.join(IMG_DIR, img_name)
    label_path = os.path.join(LABEL_DIR, os.path.splitext(img_name)[0] + ".txt")

    image = cv2.imread(img_path)
    clone = image.copy()
    cv2.namedWindow("image")
    cv2.setMouseCallback("image", click_and_crop)

    print(f"Anotando: {img_name}. Dibuja el recuadro con el mouse y presiona 'n' para siguiente imagen.")
    while True:
        cv2.imshow("image", image)
        key = cv2.waitKey(1) & 0xFF

        # 'n' para siguiente imagen
        if key == ord("n"):
            break
        # 'r' para reiniciar la caja actual
        elif key == ord("r"):
            image = clone.copy()

cv2.destroyAllWindows()
print("¡Anotación completada!")
