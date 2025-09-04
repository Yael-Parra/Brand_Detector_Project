from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import traceback

from core.logging import get_logger

logger = get_logger("exceptions")


class BaseCustomException(Exception):
    """Excepción base personalizada"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(BaseCustomException):
    """Error de validación de datos"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.field = field
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class DatabaseError(BaseCustomException):
    """Error de base de datos"""
    
    def __init__(self, message: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class FileProcessingError(BaseCustomException):
    """Error en el procesamiento de archivos"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.file_path = file_path
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class YOLOModelError(BaseCustomException):
    """Error del modelo YOLO"""
    
    def __init__(self, message: str, model_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.model_path = model_path
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class DetectionError(BaseCustomException):
    """Error en el procesamiento de detección"""
    
    def __init__(self, message: str, detection_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.detection_type = detection_type
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ModelLoadError(BaseCustomException):
    """Error al cargar el modelo"""
    
    def __init__(self, message: str, model_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.model_path = model_path
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class AuthenticationError(BaseCustomException):
    """Error de autenticación"""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class AuthorizationError(BaseCustomException):
    """Error de autorización"""
    
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ResourceNotFoundError(BaseCustomException):
    """Error cuando un recurso no se encuentra"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_id: Optional[str] = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ExternalServiceError(BaseCustomException):
    """Error de servicios externos (YouTube, APIs, etc.)"""
    
    def __init__(self, message: str, service_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.service_name = service_name
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )


class RateLimitError(BaseCustomException):
    """Error de límite de velocidad"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after}
        )


async def custom_exception_handler(request: Request, exc: BaseCustomException) -> JSONResponse:
    """Handler global para excepciones personalizadas"""
    
    logger.error(
        f"Custom exception occurred: {exc.__class__.__name__}",
        extra={
            "message": exc.message,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "type": exc.__class__.__name__,
            "details": exc.details,
            "timestamp": None  # Se puede agregar timestamp aquí
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler para excepciones HTTP de FastAPI"""
    
    logger.warning(
        f"HTTP exception: {exc.status_code}",
        extra={
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "type": "HTTPException",
            "details": {},
            "timestamp": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler para excepciones generales no capturadas"""
    
    error_id = id(exc)  # ID único para el error
    
    logger.error(
        f"Unhandled exception occurred: {exc.__class__.__name__}",
        extra={
            "error_id": error_id,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else None
        }
    )
    
    # En producción, no exponer detalles internos
    from config.settings import settings
    
    if settings.environment == "production":
        message = "An internal server error occurred"
        details = {"error_id": error_id}
    else:
        message = str(exc)
        details = {
            "error_id": error_id,
            "traceback": traceback.format_exc().split('\n')
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": message,
            "type": exc.__class__.__name__,
            "details": details,
            "timestamp": None
        }
    )


def setup_exception_handlers(app):
    """Configura todos los handlers de excepciones en la aplicación FastAPI"""
    
    # Handlers para excepciones personalizadas
    app.add_exception_handler(BaseCustomException, custom_exception_handler)
    app.add_exception_handler(ValidationError, custom_exception_handler)
    app.add_exception_handler(DatabaseError, custom_exception_handler)
    app.add_exception_handler(FileProcessingError, custom_exception_handler)
    app.add_exception_handler(YOLOModelError, custom_exception_handler)
    app.add_exception_handler(DetectionError, custom_exception_handler)
    app.add_exception_handler(ModelLoadError, custom_exception_handler)
    app.add_exception_handler(AuthenticationError, custom_exception_handler)
    app.add_exception_handler(AuthorizationError, custom_exception_handler)
    app.add_exception_handler(ResourceNotFoundError, custom_exception_handler)
    app.add_exception_handler(ExternalServiceError, custom_exception_handler)
    app.add_exception_handler(RateLimitError, custom_exception_handler)
    
    # Handler para excepciones HTTP de FastAPI
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Handler general para excepciones no capturadas
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers configured successfully")