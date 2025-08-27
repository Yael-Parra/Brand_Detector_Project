from roboflow import Roboflow
rf = Roboflow(api_key="oM4tsslDCyceXPEmfdwj")
project = rf.workspace("test1mrm").project("customlogomercedez-hxxq6")
version = project.version(2)
dataset = version.download("yolov11")

#Cargar el modelo base Yolov11
from ultralytics import YOLO
model = YOLO("yolo11s.pt")

#Entrenamiento del modelo personalizado.
data_path ="/content/customLogoMercedez-2/data.yaml"
results = model.train(data=data_path,epochs=50,imgsz=640)

#Prediciones
# cargamos el modelo ya entrenado
custom_model =YOLO("/content/runs/detect/train/weights/best.pt")

# Realizamos predicciones sobre algunas imagenes
res = custom_model.predict(source="C:/Users/Administrator/Desktop/proyecto_12/Brand_Detector_Project/backend/customLogoMercedez-2/train/images/_m4q9449_webp.rf.fea34810bf11852e430d6c024d29c365.jpg")
# Vizualizacion de los resultados de las detecciones
res[28].show()