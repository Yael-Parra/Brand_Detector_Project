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
