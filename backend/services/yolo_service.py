from typing import Dict, Set

def summarize_counts(label_frames: Dict[str,int], total_frames: int, frames_with_label: Dict[str, Set[int]] = None, fps: float = None) -> Dict[str, Dict]:
    """
    Calcula % de aparición por etiqueta y porcentaje de tiempo visible.
    
    Args:
        label_frames: Diccionario con conteo de frames por etiqueta
        total_frames: Total de frames procesados
        frames_with_label: Diccionario con sets de frames donde aparece cada etiqueta
        fps: Frames por segundo del video
    """
    out = {}
    for label, frames in label_frames.items():
        pct = (frames / total_frames * 100.0) if total_frames > 0 else 0.0
        
        # Calcular porcentaje de tiempo visible
        percentage_of_video_time = 0.0
        if frames_with_label and label in frames_with_label and fps and fps > 0:
            unique_frames = len(frames_with_label[label])
            total_video_duration = total_frames / fps
            time_visible = unique_frames / fps
            percentage_of_video_time = (time_visible / total_video_duration * 100.0) if total_video_duration > 0 else 0.0
        
        out[label] = {
            "frames": frames,
            "percentage": pct,
            "percentage_of_video_time": percentage_of_video_time
        }
    return out
