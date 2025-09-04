import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

from config.settings import settings


class ColoredFormatter(logging.Formatter):
    """Formateador con colores para la consola"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class LoggerSetup:
    """Configurador centralizado de logging"""
    
    def __init__(self):
        self.logger = logging.getLogger("brand_detector")
        self.logger.setLevel(getattr(logging, settings.log_level))
        
        # Evitar duplicación de handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        self._setup_console_handler()
        if settings.log_file:
            self._setup_file_handler()
    
    def _setup_console_handler(self):
        """Configura el handler para la consola"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.log_level))
        
        # Usar colores solo en desarrollo
        if settings.environment == "development":
            formatter = ColoredFormatter(settings.log_format)
        else:
            formatter = logging.Formatter(settings.log_format)
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self):
        """Configura el handler para archivos con rotación"""
        # Crear directorio de logs si no existe
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handler con rotación por tamaño
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.log_file,
            maxBytes=settings.log_max_size,
            backupCount=settings.log_backup_count,
            encoding='utf-8'
        )
        
        file_handler.setLevel(getattr(logging, settings.log_level))
        formatter = logging.Formatter(settings.log_format)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Obtiene un logger hijo con el nombre especificado"""
        if name:
            return self.logger.getChild(name)
        return self.logger


# Instancia global del configurador de logging
logger_setup = LoggerSetup()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Función de conveniencia para obtener un logger"""
    return logger_setup.get_logger(name)


# Logger principal de la aplicación
app_logger = get_logger("app")
db_logger = get_logger("database")
api_logger = get_logger("api")
yolo_logger = get_logger("yolo")