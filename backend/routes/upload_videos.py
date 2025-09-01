from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import cv2
import tempfile
#from ..services.yolo_service import get_model
from ultralytics import YOLO


router = APIRouter()

# =========================================
# Endpoint para procesar videos mp4 subidos
# =========================================

@router.post("/predict/mp4")
async def predict_mp4(file: UploadFile = File(...)):
	import time
	start_time = time.time()
	# Guardar el archivo temporalmente
	with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
		temp_video.write(await file.read())
		temp_video_path = temp_video.name

	# Cargar modelo YOLO
	model = YOLO("best_v5.pt")
	cap = cv2.VideoCapture(temp_video_path)
	label_frames = {}
	frame_idx = 0
	fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
	names_map = getattr(model, "names", {})
	while cap.isOpened():
		ret, frame = cap.read()
		if not ret:
			break
		results = model(frame)
		for r in results:
			boxes = r.boxes
			for box in boxes:
				cls = int(box.cls[0]) if hasattr(box, 'cls') else None
				label = names_map.get(cls, str(cls))
				if label:
					label_frames[label] = label_frames.get(label, 0) + 1
		frame_idx += 1
	cap.release()
	end_time = time.time()
	processed_secs = end_time - start_time
	from ..services.yolo_service import summarize_counts
	detections_summary = summarize_counts(label_frames, frame_idx)
	response = {
		"type": "mp4",
		"name": file.filename,
		"fps_estimated": fps,
		"processed_secs": processed_secs,
		"detections": detections_summary,
	}
	return JSONResponse(content=response)