// Exportaciones centralizadas de hooks personalizados
export { useApi } from './useApi';
export { useJobPolling } from './useJobPolling';

// Hook combinado que incluye tanto API como polling
import { useApi } from './useApi';
import { useJobPolling } from './useJobPolling';
import { useApp } from '../contexts/AppContext';
import { useNotification } from '../contexts/NotificationContext';

export const useProcessing = () => {
  const { state, actions } = useApp();
  const { actions: notificationActions } = useNotification();
  const api = useApi();
  const polling = useJobPolling();

  const processFile = async (file, type = 'image') => {
    actions.setLoading(true);
    actions.setError(null);

    try {
      const { data, error } = await api.uploadFile(file, type);
      
      if (error) {
        actions.setError(error);
        return { success: false, error };
      }

      // Configurar resultados
      const results = {
        detections: data.detections || [],
        ...(type === 'image' ? {
          image_url: URL.createObjectURL(file),
          annotated_jpg_base64: data.annotated_jpg_base64,
          original_jpg_base64: data.original_jpg_base64
        } : {
          video_file: file.name,
          video_url: URL.createObjectURL(file)
        })
      };

      actions.setResults(results);

      // Iniciar polling si hay job_id
      if (data.job_id) {
        polling.startPolling(data.job_id);
      }

      return { success: true, data };
    } catch (error) {
      actions.setError(error.message);
      return { success: false, error: error.message };
    } finally {
      actions.setLoading(false);
    }
  };

  const processYouTube = async (url) => {
    actions.setLoading(true);
    actions.setError(null);

    try {
      const { data, error } = await api.processYouTube(url);
      
      if (error) {
        actions.setError(error);
        return { success: false, error };
      }

      // Configurar resultados
      const results = {
        video_url: url,
        detections: data.detections || [],
        total_video_time_segs: data.total_video_time_segs || 0
      };

      actions.setResults(results);

      // Iniciar polling si hay job_id
      if (data.job_id) {
        polling.startPolling(data.job_id);
      }

      return { success: true, data };
    } catch (error) {
      actions.setError(error.message);
      return { success: false, error: error.message };
    } finally {
      actions.setLoading(false);
    }
  };

  const resetProcessing = () => {
    polling.stopPolling();
    actions.resetState();
  };

  return {
    // Estado
    ...state,
    isLoading: state.loading || api.loading,
    isPolling: polling.isPolling,
    
    // Acciones
    processFile,
    processYouTube,
    resetProcessing,
    
    // API y polling individuales
    api,
    polling
  };
};

export default {
  useApi,
  useJobPolling,
  useProcessing
};