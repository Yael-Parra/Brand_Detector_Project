import { useState } from 'react';
import { useNotification } from '../contexts/NotificationContext';

const API_BASE_URL = 'http://localhost:8000';

export const useApi = () => {
  const [loading, setLoading] = useState(false);
  const { actions: notificationActions } = useNotification();

  const makeRequest = async (url, options = {}) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}${url}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers
        },
        ...options
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || `Error ${response.status}`);
      }

      const data = await response.json();
      return { data, error: null };
    } catch (error) {
      console.error('API Error:', error);
      notificationActions.showError(error.message || 'Error en la comunicación con el servidor');
      return { data: null, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  const uploadFile = async (file, type = 'image') => {
    const formData = new FormData();
    formData.append('file', file);

    const endpoint = type === 'video' ? '/predict/mp4' : '/process/image';
    
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || `Error ${response.status}`);
      }

      const data = await response.json();
      notificationActions.showSuccess(`${type === 'video' ? 'Video' : 'Imagen'} procesado exitosamente`);
      return { data, error: null };
    } catch (error) {
      console.error('Upload Error:', error);
      notificationActions.showError(error.message || 'Error al subir el archivo');
      return { data: null, error: error.message };
    } finally {
      setLoading(false);
    }
  };

  const processYouTube = async (url) => {
    return makeRequest('/process/youtube', {
      method: 'POST',
      body: JSON.stringify({ url })
    });
  };

  const getJobStatus = async (jobId) => {
    return makeRequest(`/status/${jobId}`);
  };

  const getProcessedVideo = async (jobId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/video/${jobId}`);
      if (!response.ok) {
        throw new Error(`Error ${response.status}`);
      }
      return { data: response, error: null };
    } catch (error) {
      console.error('Get Processed Video Error:', error);
      notificationActions.showError('Error al obtener el video procesado');
      return { data: null, error: error.message };
    }
  };

  return {
    loading,
    makeRequest,
    uploadFile,
    processYouTube,
    getJobStatus,
    getProcessedVideo
  };
};

export default useApi;