from typing import Dict

def summarize_counts(label_frames: Dict[str,int], total_frames: int) -> Dict[str, Dict]:
    """
    Calcula % de aparición por etiqueta.
    """
    out = {}
    for label, frames in label_frames.items():
        pct = (frames / total_frames * 100.0) if total_frames > 0 else 0.0
        out[label] = {"frames": frames, "percentage": pct}
    return out
