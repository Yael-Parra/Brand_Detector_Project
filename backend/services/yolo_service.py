import os
import time
from typing import Dict, Tuple, Iterable, Optional

import cv2
from ultralytics import YOLO

MODEL_PATH = os.getenv("BEST_WEIGHTS") or "best.pt"
if not os.path.exists(MODEL_PATH):
    alt = "best.pt"
    MODEL_PATH = alt if os.path.exists(alt) else "best.pt"

_model: Optional[YOLO] = None

def get_model() -> YOLO:
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model

def _labels_in_result(result, names_map) -> Iterable[str]:
    """
    Devuelve etiquetas (set) detectadas en 1 frame.
    """
    labels = set()
    for b in result.boxes:
        if b.cls is not None and len(b.cls) > 0:
            labels.add(names_map[int(b.cls[0])])
    return labels

def summarize_counts(label_frames: Dict[str,int], total_frames: int) -> Dict[str, Dict]:
    """
    Calcula % de aparición por etiqueta.
    """
    out = {}
    for label, frames in label_frames.items():
        pct = (frames / total_frames * 100.0) if total_frames > 0 else 0.0
        out[label] = {"frames": frames, "percentage": pct}
    return out

# ------ Análisis de MP4 local ------
def analyze_mp4(path: str) -> Tuple[float, float, Dict[str, Dict]]:
    """
    Devuelve: (fps, total_secs, resumen_por_etiqueta)
    """
    model = get_model()
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir el video")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    total_secs = (total_frames / fps) if fps > 0 else 0.0

    label_frames: Dict[str, int] = {}
    names_map = model.names

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1

        results = model(frame)
        detected = _labels_in_result(results[0], names_map)

        for lab in detected:
            label_frames[lab] = label_frames.get(lab, 0) + 1

    cap.release()
    summary = summarize_counts(label_frames, total_frames=max(total_frames, frame_idx))
    return fps, total_secs, summary

def analyze_stream_url(source: str, duration_sec: int = 15) -> Tuple[float, float, Dict[str, Dict]]:
    """
    Procesa frames durante 'duration_sec' segs desde una URL y calcula métricas.
    fps se estima por frames/tiempo (no siempre disponible).
    """
    model = get_model()
    start = time.time()
    label_frames: Dict[str, int] = {}
    total_frames = 0
    names_map = model.names

    # stream=True produce generador de resultados
    results_iter = model(source, stream=True)
    for result in results_iter:
        now = time.time()
        if now - start > duration_sec:
            break

        total_frames += 1
        detected = _labels_in_result(result, names_map)
        for lab in detected:
            label_frames[lab] = label_frames.get(lab, 0) + 1

    elapsed = max(time.time() - start, 1e-6)
    fps_est = total_frames / elapsed
    summary = summarize_counts(label_frames, total_frames)
    return fps_est, elapsed, summary

def analyze_webcam(camera_index: int = 0, duration_sec: int = 10) -> Tuple[float, float, Dict[str, Dict]]:
    model = get_model()
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la cámara {camera_index}")

    start = time.time()
    label_frames: Dict[str, int] = {}
    total_frames = 0
    names_map = model.names

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        total_frames += 1
        results = model(frame)
        detected = _labels_in_result(results[0], names_map)
        for lab in detected:
            label_frames[lab] = label_frames.get(lab, 0) + 1

        if (time.time() - start) > duration_sec:
            break

    elapsed = max(time.time() - start, 1e-6)
    fps_est = total_frames / elapsed
    cap.release()
    summary = summarize_counts(label_frames, total_frames)
    return fps_est, elapsed, summary
