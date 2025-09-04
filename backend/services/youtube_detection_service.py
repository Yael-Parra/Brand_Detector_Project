from typing import Dict, List, Any, Optional, Callable
import cv2
import os
import time
import threading
from pathlib import Path
import yt_dlp
from urllib.parse import urlparse, parse_qs

from .video_detection_service import VideoDetectionService, VideoMetrics, ProcessingStatus
from core.logging import get_logger
from core.exceptions import DetectionError, ValidationError
from database import db_insertion_data as db

logger = get_logger(__name__)

class YouTubeDetectionService(VideoDetectionService):
    """
    Servicio especializado para detección en videos de YouTube.
    Extiende VideoDetectionService con capacidades de descarga de YouTube.
    """
    
    def __init__(self, model_path: str = None):
        super().__init__(model_path)
        self.download_dir = Path("data/uploads/youtube")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuración de yt-dlp
        self.ydl_opts = {
            "outtmpl": str(self.download_dir / "%(title)s.%(ext)s"),
            "format": "mp4/bestvideo+bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "extractaudio": False,
            "audioformat": "mp3",
            "embed_subs": False,
            "writesubtitles": False,
        }
        
        # Información del video de YouTube
        self.youtube_info: Optional[Dict] = None
        self.downloaded_file: Optional[str] = None
        
        # Callback para actualizaciones de estado
        self.status_callback: Optional[Callable] = None
    
    def set_status_callback(self, callback: Callable) -> None:
        """Establece el callback para actualizaciones de estado."""
        self.status_callback = callback
        self._progress_callback = callback
    
    def process_youtube_url(self, youtube_url: str, **kwargs) -> Dict[str, Any]:
        """
        Procesa un video de YouTube desde su URL con métricas avanzadas.
        
        Args:
            youtube_url: URL del video de YouTube
            **kwargs: Argumentos adicionales:
                - async_processing: bool - Procesamiento asíncrono (default: True)
                - quality: str - Calidad del video ('best', 'worst', '720p', etc.)
                - keep_file: bool - Mantener archivo descargado (default: False)
                - frame_skip: int - Saltar frames para acelerar (default: 1)
                - confidence_threshold: float - Umbral de confianza (default: 0.5)
                - save_to_db: bool - Guardar en base de datos (default: True)
                - calculate_metrics: bool - Calcular métricas avanzadas (default: True)
        
        Returns:
            Diccionario con resultados del procesamiento y métricas avanzadas
        """
        start_time = time.time()
        
        try:
            # Validar URL
            if not self._is_valid_youtube_url(youtube_url):
                raise ValidationError("URL de YouTube inválida")
            
            # Configuración
            async_processing = kwargs.get('async_processing', True)
            quality = kwargs.get('quality', 'best')
            keep_file = kwargs.get('keep_file', False)
            calculate_metrics = kwargs.get('calculate_metrics', True)
            
            # Actualizar configuración de calidad
            self._update_quality_settings(quality)
            
            # Obtener información del video antes de descargar
            logger.info(f"Obteniendo información del video: {youtube_url}")
            video_info = self.get_video_info(youtube_url)
            
            # Descargar video
            download_start = time.time()
            logger.info(f"Iniciando descarga de YouTube: {youtube_url}")
            video_path = self._download_youtube_video(youtube_url)
            download_time = time.time() - download_start
            logger.info(f"Descarga completada en {download_time:.2f}s: {video_path}")
            
            # Procesar como video normal con métricas
            detection_start = time.time()
            kwargs['save_to_db'] = kwargs.get('save_to_db', True)
            kwargs['calculate_metrics'] = calculate_metrics
            
            # Configurar callbacks para el procesamiento del video
            if self.status_callback:
                def progress_callback(progress_data):
                    # Actualizar progreso con información específica de YouTube
                    updated_data = {
                        **progress_data,
                        'youtube_info': video_info,
                        'source_url': youtube_url,
                        'video_title': video_info.get('title', 'Unknown')
                    }
                    self.status_callback(updated_data)
                
                def completion_callback(completion_data):
                    # Actualizar estado final con información específica de YouTube
                    final_data = {
                        **completion_data,
                        'youtube_info': video_info,
                        'source_url': youtube_url,
                        'video_title': video_info.get('title', 'Unknown')
                    }
                    self.status_callback(final_data)
                
                kwargs['progress_callback'] = progress_callback
                kwargs['completion_callback'] = completion_callback
            
            logger.info(f"Iniciando procesamiento del video descargado: {video_path}")
            logger.info(f"Configuración de procesamiento: async={async_processing}, callbacks configurados={self.status_callback is not None}")
            result = self.process(video_path, **kwargs)
            detection_time = time.time() - detection_start
            logger.info(f"Procesamiento completado en {detection_time:.2f}s")
            
            total_time = time.time() - start_time
            
            # Calcular métricas específicas de YouTube
            youtube_metrics = {
                "download_time": download_time,
                "detection_time": detection_time,
                "total_time": total_time,
                "download_efficiency": video_info.get("duration", 0) / download_time if download_time > 0 else 0,
                "processing_efficiency": result.get("video_info", {}).get("total_frames", 0) / detection_time if detection_time > 0 else 0
            }
            
            # Combinar métricas existentes con métricas de YouTube
            if "metrics" in result and calculate_metrics:
                result["metrics"]["processing_times"].update({
                    "download_time": download_time,
                    "detection_time": detection_time,
                    "total_time": total_time
                })
                result["metrics"]["youtube_specific"] = youtube_metrics
            
            # Agregar información específica de YouTube
            result.update({
                "youtube_info": self.youtube_info or video_info,
                "source_url": youtube_url,
                "downloaded_file": video_path,
                "file_kept": keep_file,
                "download_time": download_time,
                "video_title": video_info.get("title", "Unknown"),
                "video_duration": video_info.get("duration", 0)
            })
            
            # Actualizar callback con información completa
            if self.status_callback:
                self.status_callback({
                    "status": "completed",
                    "youtube_info": result["youtube_info"],
                    "metrics": result.get("metrics", {}),
                    "processing_time": total_time
                })
            
            # Limpiar archivo si no se debe mantener
            if not keep_file and not async_processing:
                self._cleanup_downloaded_file()
            
            logger.info(f"Procesamiento de YouTube completado en {total_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error procesando YouTube URL: {e}")
            # Limpiar en caso de error
            self._cleanup_downloaded_file()
            
            # Notificar error via callback
            if self.status_callback:
                self.status_callback({
                    "status": "error",
                    "error": str(e),
                    "processing_time": time.time() - start_time
                })
            
            raise DetectionError(f"Error procesando video de YouTube: {str(e)}")
    
    def _is_valid_youtube_url(self, url: str) -> bool:
        """
        Valida si la URL es de YouTube.
        
        Args:
            url: URL a validar
            
        Returns:
            True si es una URL válida de YouTube
        """
        try:
            parsed = urlparse(url)
            
            # Dominios válidos de YouTube
            valid_domains = [
                'youtube.com', 'www.youtube.com', 
                'youtu.be', 'www.youtu.be',
                'm.youtube.com'
            ]
            
            if parsed.netloc.lower() not in valid_domains:
                return False
            
            # Verificar que tenga un ID de video
            if 'youtu.be' in parsed.netloc:
                return len(parsed.path) > 1
            else:
                query_params = parse_qs(parsed.query)
                return 'v' in query_params and len(query_params['v'][0]) > 0
            
        except Exception:
            return False
    
    def _update_quality_settings(self, quality: str) -> None:
        """
        Actualiza la configuración de calidad para yt-dlp.
        
        Args:
            quality: Calidad deseada
        """
        quality_formats = {
            'best': 'mp4/bestvideo+bestaudio/best',
            'worst': 'worst',
            '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
            '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
            '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
            '360p': 'bestvideo[height<=360]+bestaudio/best[height<=360]'
        }
        
        self.ydl_opts['format'] = quality_formats.get(quality, quality_formats['best'])
        logger.info(f"Calidad configurada: {quality}")
    
    def _download_youtube_video(self, url: str) -> str:
        """
        Descarga un video de YouTube.
        
        Args:
            url: URL del video
            
        Returns:
            Ruta del archivo descargado
        """
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                # Extraer información del video
                logger.info("Extrayendo información del video...")
                info = ydl.extract_info(url, download=False)
                
                # Guardar información del video
                self.youtube_info = {
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 0),
                    "uploader": info.get('uploader', 'Unknown'),
                    "view_count": info.get('view_count', 0),
                    "upload_date": info.get('upload_date', 'Unknown'),
                    "description": info.get('description', '')[:500],  # Limitar descripción
                    "thumbnail": info.get('thumbnail', ''),
                    "video_id": info.get('id', ''),
                    "webpage_url": info.get('webpage_url', url)
                }
                
                logger.info(f"Video encontrado: {self.youtube_info['title']} ({self.youtube_info['duration']}s)")
                
                # Descargar video
                logger.info("Descargando video...")
                ydl.download([url])
                
                # Obtener ruta del archivo descargado
                filename = ydl.prepare_filename(info)
                
                # Verificar que el archivo existe
                if not os.path.exists(filename):
                    # Buscar archivos con nombre similar (yt-dlp puede cambiar la extensión)
                    base_name = os.path.splitext(filename)[0]
                    for ext in ['.mp4', '.webm', '.mkv', '.avi']:
                        potential_file = base_name + ext
                        if os.path.exists(potential_file):
                            filename = potential_file
                            break
                    else:
                        raise FileNotFoundError(f"Archivo descargado no encontrado: {filename}")
                
                self.downloaded_file = filename
                logger.info(f"Video descargado exitosamente: {filename}")
                return filename
                
        except Exception as e:
            logger.error(f"Error descargando video de YouTube: {e}")
            raise DetectionError(f"No se pudo descargar el video: {str(e)}")
    
    def _cleanup_downloaded_file(self) -> None:
        """
        Elimina el archivo descargado de YouTube.
        """
        if self.downloaded_file and os.path.exists(self.downloaded_file):
            try:
                os.remove(self.downloaded_file)
                logger.info(f"Archivo de YouTube eliminado: {self.downloaded_file}")
                self.downloaded_file = None
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo de YouTube: {e}")
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Obtiene información de un video de YouTube sin descargarlo.
        
        Args:
            url: URL del video
            
        Returns:
            Información del video
        """
        try:
            if not self._is_valid_youtube_url(url):
                raise ValidationError("URL de YouTube inválida")
            
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 0),
                    "duration_string": info.get('duration_string', '0:00'),
                    "uploader": info.get('uploader', 'Unknown'),
                    "view_count": info.get('view_count', 0),
                    "upload_date": info.get('upload_date', 'Unknown'),
                    "description": info.get('description', '')[:200],
                    "thumbnail": info.get('thumbnail', ''),
                    "video_id": info.get('id', ''),
                    "webpage_url": info.get('webpage_url', url),
                    "formats_available": len(info.get('formats', [])),
                    "is_live": info.get('is_live', False)
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo información del video: {e}")
            raise DetectionError(f"No se pudo obtener información del video: {str(e)}")
    
    def process_playlist(self, playlist_url: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Procesa una playlist completa de YouTube.
        
        Args:
            playlist_url: URL de la playlist
            **kwargs: Argumentos de procesamiento
                - max_videos: int - Máximo número de videos a procesar
                - skip_errors: bool - Continuar si hay errores (default: True)
        
        Returns:
            Lista de resultados de procesamiento
        """
        try:
            max_videos = kwargs.get('max_videos', 10)
            skip_errors = kwargs.get('skip_errors', True)
            
            # Extraer URLs de la playlist
            with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                if 'entries' not in playlist_info:
                    raise ValidationError("No se pudo extraer la playlist")
                
                video_urls = []
                for entry in playlist_info['entries'][:max_videos]:
                    if entry and 'url' in entry:
                        video_urls.append(entry['url'])
            
            logger.info(f"Procesando playlist con {len(video_urls)} videos")
            
            # Procesar cada video
            results = []
            for i, video_url in enumerate(video_urls):
                try:
                    logger.info(f"Procesando video {i+1}/{len(video_urls)}: {video_url}")
                    result = self.process_youtube_url(video_url, **kwargs)
                    result['playlist_position'] = i + 1
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Error procesando video {i+1}: {e}")
                    if skip_errors:
                        results.append({
                            'playlist_position': i + 1,
                            'url': video_url,
                            'status': 'error',
                            'error': str(e)
                        })
                    else:
                        raise
            
            return results
            
        except Exception as e:
            logger.error(f"Error procesando playlist: {e}")
            raise DetectionError(f"Error procesando playlist: {str(e)}")
    
    def cleanup(self) -> None:
        """
        Limpia todos los recursos del servicio.
        """
        self._cleanup_downloaded_file()
        super().cleanup()
    
    def get_download_formats(self, url: str) -> List[Dict[str, Any]]:
        """
        Obtiene los formatos disponibles para descarga.
        
        Args:
            url: URL del video
            
        Returns:
            Lista de formatos disponibles
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                
                formats = []
                for fmt in info.get('formats', []):
                    if fmt.get('vcodec') != 'none':  # Solo formatos con video
                        formats.append({
                            'format_id': fmt.get('format_id', ''),
                            'ext': fmt.get('ext', ''),
                            'resolution': fmt.get('resolution', 'unknown'),
                            'fps': fmt.get('fps', 0),
                            'filesize': fmt.get('filesize', 0),
                            'quality': fmt.get('quality', 0)
                        })
                
                return sorted(formats, key=lambda x: x['quality'], reverse=True)
                
        except Exception as e:
            logger.error(f"Error obteniendo formatos: {e}")
            return []