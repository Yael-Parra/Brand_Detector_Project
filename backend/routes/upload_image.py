# =========================================
# Endpoint para procesar imágenes subidas
# =========================================
from fastapi import APIRouter, UploadFile, File, HTTPException
import numpy as np
import cv2
import base64
from fastapi.responses import JSONResponse
#from ..models import ImageUploadResponse
from ..services.yolo_service import get_model

router = APIRouter()

@router.post("/process/image")
async def process_image(file: UploadFile = File(...)):
	"""
	Procesa una imagen subida y retorna si se detectó un logo o no, junto con las detecciones y la imagen anotada (base64).
	"""
	content = await file.read()
	nparr = np.frombuffer(content, np.uint8)
	image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
	if image is None:
		raise HTTPException(status_code=400, detail="Imagen inválida")
	model = get_model()
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
	mensaje = "Logo detectado" if len(detections) > 0 else "Logo no detectado"
	return JSONResponse(content={
		"mensaje": mensaje,
		"detections": detections,
		"annotated_jpg_base64": img_b64
	})
