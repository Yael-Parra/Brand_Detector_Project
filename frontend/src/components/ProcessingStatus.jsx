import React from 'react';
import { useApp } from '../contexts/AppContext';
import LoadingSpinner from './LoadingSpinner';

const ProcessingStatus = () => {
  const { state } = useApp();

  if (state.jobStatus === 'idle' || !state.jobId) {
    return null;
  }

  const getStatusConfig = () => {
    switch (state.jobStatus) {
      case 'processing':
        return {
          color: '#ffc107',
          icon: '⏳',
          message: 'Procesando video...',
          showSpinner: true
        };
      case 'completed':
        return {
          color: '#28a745',
          icon: '✅',
          message: 'Procesamiento completado',
          showSpinner: false
        };
      case 'error':
        return {
          color: '#dc3545',
          icon: '❌',
          message: 'Error en el procesamiento',
          showSpinner: false
        };
      default:
        return {
          color: '#6c757d',
          icon: '❓',
          message: 'Estado desconocido',
          showSpinner: false
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '12px 16px',
      backgroundColor: 'rgba(255, 255, 255, 0.1)',
      borderRadius: '8px',
      border: `2px solid ${config.color}`,
      margin: '16px 0',
      backdropFilter: 'blur(10px)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <span style={{ fontSize: '20px' }}>{config.icon}</span>
        {config.showSpinner && (
          <div style={{ marginRight: '0.5rem' }}>
            <LoadingSpinner 
              size="small" 
              showMessage={false} 
              color={config.color}
            />
          </div>
        )}
      </div>
      
      <div style={{ flex: 1 }}>
        <div style={{
          color: config.color,
          fontWeight: 'bold',
          fontSize: '14px'
        }}>
          {config.message}
        </div>
        
        {state.jobId && (
          <div style={{
            color: 'rgba(255, 255, 255, 0.7)',
            fontSize: '12px',
            marginTop: '4px'
          }}>
            Job ID: {state.jobId}
          </div>
        )}
        
        {state.error && state.jobStatus === 'error' && (
          <div style={{
            color: config.color,
            fontSize: '12px',
            marginTop: '4px',
            opacity: 0.9
          }}>
            {state.error}
          </div>
        )}
      </div>
      
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  );
};

export default ProcessingStatus;