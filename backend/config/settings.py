import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configuración centralizada de la aplicación"""
    
    # Configuración de la aplicación
    app_name: str = "YOLO Brand Detector"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Configuración del servidor
    host: str = "localhost"
    port: int = 8000
    reload: bool = True
    
    # Configuración de CORS
    cors_origins: list = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_methods: list = ["GET", "POST", "PUT", "DELETE"]
    cors_headers: list = ["*"]
    
    # Configuración de base de datos
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "brand_detector"
    db_user: str = "postgres"
    db_password: str = "password"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    
    # Configuración de YOLO
    yolo_model_path: str = "best_v5.pt"
    yolo_confidence_threshold: float = 0.5
    yolo_iou_threshold: float = 0.45
    
    # Configuración de archivos
    upload_dir: str = "backend/data/uploads"
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    allowed_image_extensions: list = [".jpg", ".jpeg", ".png", ".bmp"]
    allowed_video_extensions: list = [".mp4", ".avi", ".mov", ".mkv"]
    
    # Configuración de logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file: Optional[str] = "logs/app.log"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Configuración de Redis (para caché futuro)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Configuración de seguridad
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        allowed_envs = ['development', 'testing', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of {allowed_envs}')
        return v
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of {allowed_levels}')
        return v.upper()
    
    @property
    def database_url(self) -> str:
        """Construye la URL de conexión a la base de datos"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Construye la URL de conexión a Redis"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "allow"  # Permitir campos adicionales para compatibilidad


@lru_cache()
def get_settings() -> Settings:
    """Obtiene la configuración de la aplicación (singleton)"""
    return Settings()


# Instancia global de configuración
settings = get_settings()