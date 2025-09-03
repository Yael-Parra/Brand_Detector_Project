import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.logging import get_logger

logger = get_logger("middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requests HTTP"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generar ID único para el request
        request_id = str(uuid.uuid4())[:8]
        
        # Información del request
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log del request entrante
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "content_type": request.headers.get("content-type"),
                "content_length": request.headers.get("content-length")
            }
        )
        
        # Agregar request_id al estado del request para uso en otros lugares
        request.state.request_id = request_id
        
        try:
            # Procesar el request
            response = await call_next(request)
            
            # Calcular tiempo de procesamiento
            process_time = time.time() - start_time
            
            # Log del response
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2),
                    "response_size": response.headers.get("content-length"),
                    "client_ip": client_ip
                }
            )
            
            # Agregar headers de respuesta útiles
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
            
            return response
            
        except Exception as e:
            # Log de errores
            process_time = time.time() - start_time
            
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "error_type": e.__class__.__name__,
                    "process_time_ms": round(process_time * 1000, 2),
                    "client_ip": client_ip
                }
            )
            
            # Re-lanzar la excepción para que sea manejada por los handlers
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para agregar headers de seguridad"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Headers de seguridad básicos
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Solo en producción, agregar HSTS
        from backend.config.settings import settings
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para limitar el tamaño de requests"""
    
    def __init__(self, app: ASGIApp, max_size: int = None):
        super().__init__(app)
        from backend.config.settings import settings
        self.max_size = max_size or settings.max_file_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Verificar tamaño del contenido
        content_length = request.headers.get("content-length")
        
        if content_length:
            content_length = int(content_length)
            if content_length > self.max_size:
                logger.warning(
                    f"Request size limit exceeded",
                    extra={
                        "content_length": content_length,
                        "max_size": self.max_size,
                        "path": request.url.path,
                        "client_ip": request.client.host if request.client else "unknown"
                    }
                )
                
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Request size {content_length} exceeds maximum allowed size {self.max_size}"
                )
        
        return await call_next(request)