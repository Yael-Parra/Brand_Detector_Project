import { useEffect, useRef } from 'react';
import { useApp } from '../contexts/AppContext';
import { useNotification } from '../contexts/NotificationContext';
import { useApi } from './useApi';

export const useJobPolling = () => {
  const { state, actions } = useApp();
  const { actions: notificationActions } = useNotification();
  const { getJobStatus } = useApi();
  const intervalRef = useRef(null);
  const timeoutRef = useRef(null);

  const startPolling = (jobId, interval = 2000, maxDuration = 300000) => { // 5 minutos máximo
    if (!jobId) return;

    actions.setJobId(jobId);
    actions.setJobStatus('processing');
    
    // Limpiar intervalos previos
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Timeout para evitar polling infinito
    timeoutRef.current = setTimeout(() => {
      stopPolling();
      actions.setJobStatus('error');
      actions.setError('Tiempo de espera agotado para el procesamiento');
      notificationActions.showError('El procesamiento está tomando más tiempo del esperado');
    }, maxDuration);

    // Función de polling
    const poll = async () => {
      try {
        const { data, error } = await getJobStatus(jobId);
        
        if (error) {
          stopPolling();
          actions.setJobStatus('error');
          actions.setError(error);
          return;
        }

        if (data) {
          const { status, progress, message } = data;
          
          switch (status) {
            case 'completed':
              stopPolling();
              actions.setJobStatus('completed');
              actions.setResults(data);
              notificationActions.showSuccess('Procesamiento completado exitosamente');
              break;
              
            case 'error':
            case 'failed':
              stopPolling();
              actions.setJobStatus('error');
              actions.setError(message || 'Error en el procesamiento');
              notificationActions.showError(message || 'Error en el procesamiento del video');
              break;
              
            case 'processing':
            case 'in_progress':
              actions.setJobStatus('processing');
              if (progress !== undefined) {
                // Aquí podrías manejar el progreso si el backend lo proporciona
                console.log(`Progreso: ${progress}%`);
              }
              break;
              
            default:
              // Mantener el estado actual para estados desconocidos
              break;
          }
        }
      } catch (error) {
        console.error('Error en polling:', error);
        // No detener el polling por errores de red temporales
      }
    };

    // Ejecutar inmediatamente y luego cada intervalo
    poll();
    intervalRef.current = setInterval(poll, interval);
  };

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  // Limpiar al desmontar el componente
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, []);

  // Reanudar polling si hay un jobId activo al montar
  useEffect(() => {
    if (state.jobId && state.jobStatus === 'processing') {
      startPolling(state.jobId);
    }
  }, []);

  return {
    startPolling,
    stopPolling,
    isPolling: intervalRef.current !== null
  };
};

export default useJobPolling;