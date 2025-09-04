import time
import uuid
from typing import Callable, List
import json

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.middleware.cors import CORSMiddleware

from core.logging import get_logger

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
        from config.settings import settings
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware para limitar el tamaño de requests"""
    
    def __init__(self, app: ASGIApp, max_size: int = None):
        super().__init__(app)
        from config.settings import settings
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


class EnhancedCORSMiddleware(BaseHTTPMiddleware):
    """Middleware mejorado para CORS con logging y validación"""
    
    def __init__(self, app: ASGIApp, allowed_origins: List[str] = None, 
                 allowed_methods: List[str] = None, allowed_headers: List[str] = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["*"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin")
        
        # Log de requests CORS
        if origin:
            logger.debug(
                f"CORS request from origin: {origin}",
                extra={
                    "origin": origin,
                    "method": request.method,
                    "path": request.url.path,
                    "allowed_origins": self.allowed_origins
                }
            )
        
        # Manejar preflight requests
        if request.method == "OPTIONS":
            response = Response()
            
            # Verificar origen
            if "*" in self.allowed_origins or origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin or "*"
                response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
                response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Max-Age"] = "86400"  # 24 horas
            else:
                logger.warning(
                    f"CORS preflight rejected for origin: {origin}",
                    extra={"origin": origin, "allowed_origins": self.allowed_origins}
                )
                response.status_code = 403
            
            return response
        
        # Procesar request normal
        response = await call_next(request)
        
        # Agregar headers CORS a la respuesta
        if origin and ("*" in self.allowed_origins or origin in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID, X-Process-Time"
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware para manejo centralizado de errores"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        
        except HTTPException as e:
            # HTTPException ya está manejada por FastAPI, pero podemos loggear
            logger.warning(
                f"HTTP Exception: {e.status_code} - {e.detail}",
                extra={
                    "status_code": e.status_code,
                    "detail": e.detail,
                    "path": request.url.path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else "unknown"
                }
            )
            raise
        
        except ValueError as e:
            logger.error(
                f"ValueError: {str(e)}",
                extra={
                    "error_type": "ValueError",
                    "error_message": str(e),
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Bad Request",
                    "message": "Invalid input data",
                    "detail": str(e),
                    "timestamp": time.time()
                }
            )
        
        except FileNotFoundError as e:
            logger.error(
                f"FileNotFoundError: {str(e)}",
                extra={
                    "error_type": "FileNotFoundError",
                    "error_message": str(e),
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Not Found",
                    "message": "Requested resource not found",
                    "detail": str(e),
                    "timestamp": time.time()
                }
            )
        
        except PermissionError as e:
            logger.error(
                f"PermissionError: {str(e)}",
                extra={
                    "error_type": "PermissionError",
                    "error_message": str(e),
                    "path": request.url.path,
                    "method": request.method
                }
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "message": "Insufficient permissions",
                    "detail": str(e),
                    "timestamp": time.time()
                }
            )
        
        except Exception as e:
            # Error genérico no manejado
            request_id = getattr(request.state, 'request_id', 'unknown')
            
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "error_type": e.__class__.__name__,
                    "error_message": str(e),
                    "path": request.url.path,
                    "method": request.method,
                    "request_id": request_id,
                    "client_ip": request.client.host if request.client else "unknown"
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware básico para rate limiting"""
    
    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}  # {ip: [(timestamp, count), ...]}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Limpiar requests antiguos (más de 1 minuto)
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                (timestamp, count) for timestamp, count in self.request_counts[client_ip]
                if current_time - timestamp < 60
            ]
        
        # Contar requests actuales
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        current_requests = sum(count for _, count in self.request_counts[client_ip])
        
        # Verificar límite
        if current_requests >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip}",
                extra={
                    "client_ip": client_ip,
                    "current_requests": current_requests,
                    "limit": self.requests_per_minute,
                    "path": request.url.path
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": f"Rate limit exceeded. Maximum {self.requests_per_minute} requests per minute.",
                    "retry_after": 60,
                    "timestamp": current_time
                },
                headers={"Retry-After": "60"}
            )
        
        # Registrar request
        self.request_counts[client_ip].append((current_time, 1))
        
        response = await call_next(request)
        
        # Agregar headers informativos
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.requests_per_minute - current_requests - 1))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response