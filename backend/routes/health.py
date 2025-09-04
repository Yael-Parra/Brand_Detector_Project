from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import psutil
import os
import time
from datetime import datetime
from typing import Dict, Any
import cv2
from ultralytics import YOLO

router = APIRouter()

# Variables globales para el estado del servicio
service_start_time = time.time()
health_checks_count = 0
last_health_check = None

def check_system_resources() -> Dict[str, Any]:
    """Verifica los recursos del sistema"""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memoria
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # Disco
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_free_gb = disk.free / (1024**3)
        disk_total_gb = disk.total / (1024**3)
        
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "cores": cpu_count,
                "status": "healthy" if cpu_percent < 80 else "warning" if cpu_percent < 95 else "critical"
            },
            "memory": {
                "usage_percent": memory_percent,
                "available_gb": round(memory_available_gb, 2),
                "total_gb": round(memory_total_gb, 2),
                "status": "healthy" if memory_percent < 80 else "warning" if memory_percent < 95 else "critical"
            },
            "disk": {
                "usage_percent": disk_percent,
                "free_gb": round(disk_free_gb, 2),
                "total_gb": round(disk_total_gb, 2),
                "status": "healthy" if disk_percent < 80 else "warning" if disk_percent < 95 else "critical"
            }
        }
    except Exception as e:
        return {
            "error": f"Error checking system resources: {str(e)}",
            "status": "error"
        }

def check_dependencies() -> Dict[str, Any]:
    """Verifica las dependencias críticas del servicio"""
    dependencies = {
        "opencv": {"status": "unknown", "version": None},
        "yolo_model": {"status": "unknown", "model_path": None},
        "ffmpeg": {"status": "unknown", "path": None},
        "temp_directory": {"status": "unknown", "path": None}
    }
    
    # Verificar OpenCV
    try:
        dependencies["opencv"]["version"] = cv2.__version__
        dependencies["opencv"]["status"] = "healthy"
    except Exception as e:
        dependencies["opencv"]["status"] = "error"
        dependencies["opencv"]["error"] = str(e)
    
    # Verificar modelo YOLO
    try:
        model_path = "best_v5.pt"
        if os.path.exists(model_path):
            model = YOLO(model_path)
            dependencies["yolo_model"]["status"] = "healthy"
            dependencies["yolo_model"]["model_path"] = model_path
            dependencies["yolo_model"]["classes"] = len(model.names) if hasattr(model, 'names') else "unknown"
        else:
            dependencies["yolo_model"]["status"] = "error"
            dependencies["yolo_model"]["error"] = "Model file not found"
    except Exception as e:
        dependencies["yolo_model"]["status"] = "error"
        dependencies["yolo_model"]["error"] = str(e)
    
    # Verificar FFmpeg
    try:
        import shutil
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            dependencies["ffmpeg"]["status"] = "healthy"
            dependencies["ffmpeg"]["path"] = ffmpeg_path
        else:
            dependencies["ffmpeg"]["status"] = "warning"
            dependencies["ffmpeg"]["error"] = "FFmpeg not found in PATH"
    except Exception as e:
        dependencies["ffmpeg"]["status"] = "error"
        dependencies["ffmpeg"]["error"] = str(e)
    
    # Verificar directorio temporal
    try:
        from . import upload_videos
        temp_dir = upload_videos.create_temp_directory()
        if os.path.exists(temp_dir) and os.access(temp_dir, os.W_OK):
            dependencies["temp_directory"]["status"] = "healthy"
            dependencies["temp_directory"]["path"] = temp_dir
        else:
            dependencies["temp_directory"]["status"] = "error"
            dependencies["temp_directory"]["error"] = "Temp directory not accessible"
    except Exception as e:
        dependencies["temp_directory"]["status"] = "error"
        dependencies["temp_directory"]["error"] = str(e)
    
    return dependencies

def get_service_stats() -> Dict[str, Any]:
    """Obtiene estadísticas del servicio"""
    try:
        from . import upload_videos
        
        # Estadísticas de trabajos de video
        active_jobs = sum(1 for job in upload_videos.video_job_status.values() 
                         if job.get('status') == 'processing')
        completed_jobs = sum(1 for job in upload_videos.video_job_status.values() 
                           if job.get('status') == 'completed')
        error_jobs = sum(1 for job in upload_videos.video_job_status.values() 
                        if job.get('status') == 'error')
        
        uptime_seconds = time.time() - service_start_time
        uptime_hours = uptime_seconds / 3600
        
        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "uptime_hours": round(uptime_hours, 2),
            "health_checks_count": health_checks_count,
            "last_health_check": last_health_check,
            "video_jobs": {
                "total": len(upload_videos.video_job_status),
                "active": active_jobs,
                "completed": completed_jobs,
                "error": error_jobs
            }
        }
    except Exception as e:
        return {
            "error": f"Error getting service stats: {str(e)}",
            "uptime_seconds": round(time.time() - service_start_time, 2)
        }

@router.get("/health")
async def health_check():
    """Endpoint básico de health check"""
    global health_checks_count, last_health_check
    
    health_checks_count += 1
    last_health_check = datetime.now().isoformat()
    
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": last_health_check,
            "service": "Brand Detector API",
            "version": "1.0.0"
        }
    )

@router.get("/health/detailed")
async def detailed_health_check():
    """Endpoint detallado de health check con métricas del sistema"""
    global health_checks_count, last_health_check
    
    health_checks_count += 1
    last_health_check = datetime.now().isoformat()
    
    try:
        # Verificar recursos del sistema
        system_resources = check_system_resources()
        
        # Verificar dependencias
        dependencies = check_dependencies()
        
        # Obtener estadísticas del servicio
        service_stats = get_service_stats()
        
        # Determinar el estado general
        overall_status = "healthy"
        
        # Verificar si hay problemas críticos
        if any(resource.get("status") == "critical" for resource in system_resources.values() if isinstance(resource, dict)):
            overall_status = "critical"
        elif any(dep.get("status") == "error" for dep in dependencies.values()):
            overall_status = "degraded"
        elif any(resource.get("status") == "warning" for resource in system_resources.values() if isinstance(resource, dict)):
            overall_status = "warning"
        
        return JSONResponse(
            status_code=200 if overall_status in ["healthy", "warning"] else 503,
            content={
                "status": overall_status,
                "timestamp": last_health_check,
                "service": "Brand Detector API",
                "version": "1.0.0",
                "system_resources": system_resources,
                "dependencies": dependencies,
                "service_stats": service_stats
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "service": "Brand Detector API",
                "error": str(e)
            }
        )

@router.get("/health/readiness")
async def readiness_check():
    """Endpoint para verificar si el servicio está listo para recibir tráfico"""
    try:
        # Verificar dependencias críticas
        dependencies = check_dependencies()
        
        # El servicio está listo si YOLO y OpenCV están funcionando
        critical_deps = ["opencv", "yolo_model"]
        ready = all(dependencies[dep]["status"] == "healthy" for dep in critical_deps)
        
        if ready:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ready",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Service is ready to accept requests"
                }
            )
        else:
            failed_deps = [dep for dep in critical_deps if dependencies[dep]["status"] != "healthy"]
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "timestamp": datetime.now().isoformat(),
                    "message": f"Service not ready. Failed dependencies: {failed_deps}",
                    "failed_dependencies": {dep: dependencies[dep] for dep in failed_deps}
                }
            )
    
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )

@router.get("/health/liveness")
async def liveness_check():
    """Endpoint para verificar si el servicio está vivo"""
    try:
        # Verificación básica de que el proceso está funcionando
        current_time = time.time()
        uptime = current_time - service_start_time
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "alive",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": round(uptime, 2),
                "message": "Service is alive and responding"
            }
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
        )