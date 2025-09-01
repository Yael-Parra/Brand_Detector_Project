import os
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database.db_io import connect, disconnect, insert_video, insert_detection

from pydantic import BaseModel

# =============================
# Constantes y utilidades
# =============================
load_dotenv()

app = FastAPI(title="Brand Logo Detector API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# =============================
# Persistencia
# =============================
def persist_results(*, vtype: str, name: str, fps: float, total_secs: float, summary: dict):
    """
    Guarda el video y sus detecciones (si las hay) en la base de datos.
    Si no hay detecciones, inserta un placeholder.
    """
    conn = connect()
    try:
        id_video = insert_video(conn, vtype=vtype, name=name, total_secs=total_secs)
        inserted = 0
        if summary:
            for label, info in summary.items():
                insert_detection(
                    conn,
                    id_video=id_video,
                    label_name=label,
                    qty_frames_detected=int(info.get("frames", 0)),
                    fps=fps,
                    percent=float(info.get("percentage", 0.0)),
                )
                inserted += 1
        else:
            insert_detection(
                conn,
                id_video=id_video,
                label_name="(ninguno)",
                qty_frames_detected=0,
                fps=fps,
                percent=0.0,
            )
            inserted = 1
        if hasattr(conn, "commit"):
            conn.commit()
        print(f"[persist] OK video={id_video} type={vtype} name={name} total_secs={total_secs:.3f} fps={fps:.2f} rows={inserted}")
        return id_video
    except Exception as e:
        try:
            if hasattr(conn, "rollback"):
                conn.rollback()
        except Exception:
            pass
        print(f"[persist] ERROR: {e}")
        raise
    finally:
        disconnect(conn)

# =============================
# Modelos
# =============================

@app.get("/")
def health():
    return {"status": "ok"}

# =============================
# Gestión de sesiones y endpoints de streaming
# =============================

# @app.post("/predict/session/start")
# def start_session(name: Optional[str] = None):
#     """Inicia una nueva sesión de streaming/captura."""
#     sid = str(uuid.uuid4())
#     with _sessions_lock:
#         _sessions[sid] = {
#             "name": name or "webcam",
#             "start_time": _now(),
#             "last_time": None,
#             "total_frames": 0,
#             "label_times": {},   # {label: segundos}
#             "label_frames": {},  # {label: frames}
#         }
#     return {"session_id": sid}

# @app.post("/predict/frame")
# async def predict_frame(
#     file: UploadFile = File(...),
#     session_id: Optional[str] = Query(None)
# ):
#     """Recibe un frame, lo procesa y lo asocia a la sesión si corresponde."""
#     content = await file.read()
#     nparr = np.frombuffer(content, np.uint8)
#     frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#     if frame is None:
#         return JSONResponse(status_code=400, content={"error": "Imagen inválida"})
#     results = model.predict(source=frame, verbose=False)
#     r0 = results[0]
#     boxes = r0.boxes
#     detections = []
#     if boxes is not None and len(boxes) > 0:
#         names = getattr(model, "names", None) or getattr(r0, "names", {})
#         for i in range(len(boxes)):
#             xyxy = r0.boxes.xyxy[i].tolist()
#             cls_id = int(getattr(r0.boxes.cls[i], "item", lambda: r0.boxes.cls[i])())
#             conf = float(r0.boxes.conf[i])
#             label = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
#             detections.append({"bbox_xyxy": xyxy, "label": label, "confidence": conf})
#     annotated = r0.plot()
#     ok, buf = cv2.imencode(".jpg", annotated)
#     img_b64 = base64.b64encode(buf).decode("ascii") if ok else ""
#     # Acumular en sesión
#     if session_id:
#         with _sessions_lock:
#             sess = _sessions.get(session_id)
#             if sess:
#                 now = _now()
#                 if sess["last_time"] is None:
#                     sess["last_time"] = now
#                 else:
#                     elapsed = now - sess["last_time"]
#                     sess["last_time"] = now
#                     for lbl in {d["label"] for d in detections}:
#                         sess["label_times"][lbl] = sess["label_times"].get(lbl, 0.0) + elapsed
#                         sess["label_frames"][lbl] = sess["label_frames"].get(lbl, 0) + 1
#                 sess["total_frames"] += 1
#     return {"detections": detections, "annotated_jpg_base64": img_b64}

# @app.post("/predict/session/finish")
# def finish_session(
#     session_id_q: Optional[str] = Query(None),
#     payload: Optional[SessionIdReq] = Body(None),
# ):
#     """Finaliza la sesión y guarda los resultados en la base de datos."""
#     session_id = session_id_q or (payload.session_id if payload else None)
#     if not session_id:
#         raise HTTPException(
#             status_code=422,
#             detail="Falta session_id (pásalo como query ?session_id=... o como JSON {'session_id': '...'})"
#         )
#     with _sessions_lock:
#         sess = _sessions.get(session_id)
#         if not sess:
#             raise HTTPException(404, "Sesión no encontrada")
#         total_secs = max(0.0, _now() - sess["start_time"])
#         total_frames = sess["total_frames"]
#         fps = (total_frames / total_secs) if total_secs > 0 else 0.0
#         summary_map: Dict[str, Dict[str, Any]] = {}
#         for label, t in sess["label_times"].items():
#             frames = sess["label_frames"].get(label, 0)
#             pct = (t / total_secs * 100.0) if total_secs > 0 else 0.0
#             summary_map[label] = {
#                 "seconds": round(t, 3),
#                 "frames": frames,
#                 "percentage": round(pct, 2),
#             }
#         name = sess["name"]
#         try:
#             id_video = persist_results(
#                 vtype="streaming",
#                 name=name,
#                 fps=fps,
#                 total_secs=total_secs,
#                 summary=summary_map,
#             )
#         except Exception as e:
#             print(f"[persist] Error guardando en BD: {e}")
#             raise HTTPException(status_code=500, detail=f"Error guardando en BD: {e}")
#         del _sessions[session_id]
#     detections_list = [
#         {"label": lbl, **vals} for lbl, vals in summary_map.items()
#     ]
#     return {
#         "id_video": id_video,
#         "type": "streaming",
#         "name": name,
#         "fps_estimated": fps,
#         "processed_secs": total_secs,
#         "detections": detections_list,
#     }



from .routes.youtube_video import router as youtube_router
from .routes.upload_image import router as upload_image_router
from .routes.upload_videos import router as upload_videos_router

app.include_router(youtube_router)
app.include_router(upload_image_router)
app.include_router(upload_videos_router)