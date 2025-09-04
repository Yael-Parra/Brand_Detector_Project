import { useCallback } from 'react';
import { useNotification } from '../contexts/NotificationContext';

// Configuración de validación
const FILE_VALIDATION_CONFIG = {
  image: {
    maxSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
    allowedExtensions: ['.jpg', '.jpeg', '.png', '.gif', '.webp']
  },
  video: {
    maxSize: 100 * 1024 * 1024, // 100MB
    allowedTypes: ['video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/flv'],
    allowedExtensions: ['.mp4', '.avi', '.mov', '.wmv', '.flv']
  }
};

export const useFileValidation = () => {
  const { actions: notificationActions } = useNotification();

  const validateFile = useCallback((file, type = 'image') => {
    if (!file) {
      notificationActions.showError('No se ha seleccionado ningún archivo');
      return false;
    }

    const config = FILE_VALIDATION_CONFIG[type];
    if (!config) {
      notificationActions.showError('Tipo de archivo no soportado');
      return false;
    }

    // Validar tamaño
    if (file.size > config.maxSize) {
      const maxSizeMB = config.maxSize / (1024 * 1024);
      notificationActions.showError(
        `El archivo es demasiado grande. Tamaño máximo: ${maxSizeMB}MB`
      );
      return false;
    }

    // Validar tipo MIME
    if (!config.allowedTypes.includes(file.type)) {
      notificationActions.showError(
        `Tipo de archivo no válido. Tipos permitidos: ${config.allowedExtensions.join(', ')}`
      );
      return false;
    }

    // Validar extensión
    const fileName = file.name.toLowerCase();
    const hasValidExtension = config.allowedExtensions.some(ext => 
      fileName.endsWith(ext.toLowerCase())
    );

    if (!hasValidExtension) {
      notificationActions.showError(
        `Extensión de archivo no válida. Extensiones permitidas: ${config.allowedExtensions.join(', ')}`
      );
      return false;
    }

    return true;
  }, [notificationActions]);

  const validateYouTubeUrl = useCallback((url) => {
    if (!url || !url.trim()) {
      notificationActions.showError('Por favor, ingresa una URL de YouTube');
      return false;
    }

    // Patrones de URL de YouTube
    const youtubePatterns = [
      /^https?:\/\/(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/,
      /^https?:\/\/(www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/,
      /^https?:\/\/(www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})/
    ];

    const isValidYouTubeUrl = youtubePatterns.some(pattern => pattern.test(url.trim()));

    if (!isValidYouTubeUrl) {
      notificationActions.showError(
        'URL de YouTube no válida. Asegúrate de usar un enlace válido de YouTube.'
      );
      return false;
    }

    return true;
  }, [notificationActions]);

  const getFileInfo = useCallback((file) => {
    if (!file) return null;

    return {
      name: file.name,
      size: file.size,
      sizeFormatted: formatFileSize(file.size),
      type: file.type,
      lastModified: new Date(file.lastModified)
    };
  }, []);

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return {
    validateFile,
    validateYouTubeUrl,
    getFileInfo,
    formatFileSize,
    FILE_VALIDATION_CONFIG
  };
};

export default useFileValidation;