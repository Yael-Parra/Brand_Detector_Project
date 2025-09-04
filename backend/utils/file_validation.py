import os
from pathlib import Path
from typing import List, Optional

from fastapi import UploadFile

from config.settings import settings
from core.logging import get_logger
from core.exceptions import FileProcessingError, ValidationError

logger = get_logger("file_validation")


class FileValidator:
    """Validador de archivos con configuración centralizada"""
    
    def __init__(self):
        self.max_file_size = settings.max_file_size
        self.allowed_image_extensions = settings.allowed_image_extensions
        self.allowed_video_extensions = settings.allowed_video_extensions
        self.upload_dir = Path(settings.upload_dir)
    
    def validate_file_size(self, file: UploadFile) -> None:
        """Valida el tamaño del archivo"""
        if hasattr(file, 'size') and file.size:
            if file.size > self.max_file_size:
                logger.warning(
                    f"File size exceeds limit",
                    extra={
                        "filename": file.filename,
                        "file_size": file.size,
                        "max_size": self.max_file_size
                    }
                )
                raise ValidationError(
                    f"File size {file.size} bytes exceeds maximum allowed size {self.max_file_size} bytes",
                    field="file_size",
                    details={"file_size": file.size, "max_size": self.max_file_size}
                )
    
    def validate_file_extension(self, filename: str, file_type: str = "auto") -> str:
        """Valida la extensión del archivo y determina el tipo"""
        if not filename:
            raise ValidationError("Filename is required", field="filename")
        
        file_ext = Path(filename).suffix.lower()
        
        if not file_ext:
            raise ValidationError(
                "File must have an extension",
                field="filename",
                details={"filename": filename}
            )
        
        # Determinar tipo de archivo
        if file_type == "auto":
            if file_ext in self.allowed_image_extensions:
                detected_type = "image"
            elif file_ext in self.allowed_video_extensions:
                detected_type = "video"
            else:
                logger.warning(
                    f"Unsupported file extension",
                    extra={
                        "filename": filename,
                        "extension": file_ext,
                        "allowed_image_extensions": self.allowed_image_extensions,
                        "allowed_video_extensions": self.allowed_video_extensions
                    }
                )
                raise ValidationError(
                    f"Unsupported file extension '{file_ext}'. Allowed extensions: {self.allowed_image_extensions + self.allowed_video_extensions}",
                    field="filename",
                    details={
                        "extension": file_ext,
                        "allowed_extensions": self.allowed_image_extensions + self.allowed_video_extensions
                    }
                )
        else:
            # Validar tipo específico
            if file_type == "image" and file_ext not in self.allowed_image_extensions:
                raise ValidationError(
                    f"Invalid image extension '{file_ext}'. Allowed: {self.allowed_image_extensions}",
                    field="filename",
                    details={"extension": file_ext, "allowed_extensions": self.allowed_image_extensions}
                )
            elif file_type == "video" and file_ext not in self.allowed_video_extensions:
                raise ValidationError(
                    f"Invalid video extension '{file_ext}'. Allowed: {self.allowed_video_extensions}",
                    field="filename",
                    details={"extension": file_ext, "allowed_extensions": self.allowed_video_extensions}
                )
            detected_type = file_type
        
        logger.debug(
            f"File extension validated",
            extra={
                "filename": filename,
                "extension": file_ext,
                "detected_type": detected_type
            }
        )
        
        return detected_type
    
    def validate_filename(self, filename: str) -> str:
        """Valida y sanitiza el nombre del archivo"""
        if not filename:
            raise ValidationError("Filename is required", field="filename")
        
        # Caracteres no permitidos en nombres de archivo
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        
        for char in invalid_chars:
            if char in filename:
                raise ValidationError(
                    f"Filename contains invalid character: '{char}'",
                    field="filename",
                    details={"invalid_character": char, "filename": filename}
                )
        
        # Longitud máxima del nombre de archivo
        if len(filename) > 255:
            raise ValidationError(
                "Filename is too long (maximum 255 characters)",
                field="filename",
                details={"filename_length": len(filename), "max_length": 255}
            )
        
        return filename
    
    def generate_safe_filename(self, original_filename: str, prefix: Optional[str] = None) -> str:
        """Genera un nombre de archivo seguro y único"""
        import uuid
        import time
        
        # Validar nombre original
        self.validate_filename(original_filename)
        
        # Obtener extensión
        file_path = Path(original_filename)
        extension = file_path.suffix.lower()
        base_name = file_path.stem
        
        # Sanitizar nombre base
        safe_base_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).strip()
        
        # Generar nombre único
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        
        if prefix:
            safe_filename = f"{prefix}_{timestamp}_{unique_id}_{safe_base_name}{extension}"
        else:
            safe_filename = f"{timestamp}_{unique_id}_{safe_base_name}{extension}"
        
        logger.debug(
            f"Generated safe filename",
            extra={
                "original_filename": original_filename,
                "safe_filename": safe_filename,
                "prefix": prefix
            }
        )
        
        return safe_filename
    
    def ensure_upload_directory(self) -> Path:
        """Asegura que el directorio de uploads existe"""
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Upload directory ensured: {self.upload_dir.absolute()}")
            return self.upload_dir
        except Exception as e:
            logger.error(
                f"Failed to create upload directory",
                extra={
                    "upload_dir": str(self.upload_dir),
                    "error": str(e)
                }
            )
            raise FileProcessingError(
                f"Failed to create upload directory: {self.upload_dir}",
                file_path=str(self.upload_dir),
                details={"error": str(e)}
            )
    
    def validate_upload_file(self, file: UploadFile, file_type: str = "auto") -> dict:
        """Validación completa de archivo subido"""
        logger.info(
            f"Starting file validation",
            extra={
                "filename": file.filename,
                "content_type": file.content_type,
                "file_type": file_type
            }
        )
        
        # Validaciones
        self.validate_file_size(file)
        detected_type = self.validate_file_extension(file.filename, file_type)
        safe_filename = self.generate_safe_filename(file.filename, detected_type)
        upload_dir = self.ensure_upload_directory()
        
        result = {
            "original_filename": file.filename,
            "safe_filename": safe_filename,
            "file_type": detected_type,
            "file_path": upload_dir / safe_filename,
            "content_type": file.content_type,
            "file_size": getattr(file, 'size', None)
        }
        
        logger.info(
            f"File validation completed successfully",
            extra=result
        )
        
        return result


# Instancia global del validador
file_validator = FileValidator()


# Funciones de conveniencia
def validate_image_file(file: UploadFile) -> dict:
    """Valida un archivo de imagen"""
    return file_validator.validate_upload_file(file, "image")


def validate_video_file(file: UploadFile) -> dict:
    """Valida un archivo de video"""
    return file_validator.validate_upload_file(file, "video")


def validate_file(file: UploadFile) -> dict:
    """Valida un archivo (auto-detecta el tipo)"""
    return file_validator.validate_upload_file(file, "auto")