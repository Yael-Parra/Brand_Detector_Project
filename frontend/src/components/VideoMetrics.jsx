import React, { useState, useEffect } from 'react';
import { useApi } from '../hooks/useApi';

const VideoMetrics = ({ jobId, isVisible = true }) => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const { getJobStatus } = useApi();

  useEffect(() => {
    if (jobId && isVisible) {
      fetchMetrics();
    }
  }, [jobId, isVisible]);

  const fetchMetrics = async () => {
    setLoading(true);
    try {
      const { data } = await getJobStatus(jobId);
      if (data) {
        setMetrics(data);
      }
    } catch (error) {
      console.error('Error fetching metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  const formatPercentage = (value) => {
    return `${(value || 0).toFixed(1)}%`;
  };

  const calculateLabelDuration = (labelInfo, totalFrames, fps) => {
    if (!labelInfo || !fps) return 0;
    const framesDetected = labelInfo.qty_frames_detected || labelInfo.frames || 0;
    return framesDetected / fps;
  };

  const calculateTotalVideoTime = (totalFrames, fps) => {
    if (!totalFrames || !fps) return 0;
    return totalFrames / fps;
  };

  if (!isVisible || !metrics) {
    return null;
  }

  const {
    total_frames = 0,
    fps_estimated = 0,
    processed_secs = 0,
    detections = {},
    labels = {},
    frame_count = 0,
    progress = 0,
    status = 'unknown'
  } = metrics;

  const totalVideoTime = calculateTotalVideoTime(total_frames, fps_estimated);
  const processingSpeed = total_frames > 0 ? (total_frames / processed_secs).toFixed(1) : 0;
  const totalDetections = Object.values(labels).reduce((sum, count) => sum + count, 0);

  return (
    <div style={{
      backgroundColor: 'var(--card-bg)',
      border: '1px solid var(--border-color)',
      borderRadius: '12px',
      padding: '1.5rem',
      marginTop: '1rem',
      color: 'var(--white)'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        marginBottom: '1rem',
        gap: '0.5rem'
      }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem' }}>📊 Métricas del Video</h3>
        {loading && (
          <div style={{
            width: '16px',
            height: '16px',
            border: '2px solid var(--gray-600)',
            borderTop: '2px solid var(--primary-color)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }} />
        )}
        <button
          onClick={fetchMetrics}
          style={{
            marginLeft: 'auto',
            padding: '0.25rem 0.5rem',
            fontSize: '0.8rem',
            backgroundColor: 'var(--primary-color)',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          🔄 Actualizar
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem'
      }}>
        {/* Métricas Generales */}
        <div style={{
          backgroundColor: 'var(--gray-800)',
          padding: '1rem',
          borderRadius: '8px'
        }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--primary-color)' }}>⏱️ Tiempo</h4>
          <div style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
            <div><strong>Duración total:</strong> {formatTime(totalVideoTime)}</div>
            <div><strong>Tiempo procesamiento:</strong> {formatTime(processed_secs)}</div>
            <div><strong>Progreso:</strong> {formatPercentage(progress)}</div>
            <div><strong>Estado:</strong> <span style={{
              color: status === 'completed' ? '#4ade80' : 
                     status === 'processing' ? '#fbbf24' : 
                     status === 'error' ? '#f87171' : '#9ca3af'
            }}>{status}</span></div>
          </div>
        </div>

        {/* Métricas de Frames */}
        <div style={{
          backgroundColor: 'var(--gray-800)',
          padding: '1rem',
          borderRadius: '8px'
        }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--primary-color)' }}>🎬 Frames</h4>
          <div style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
            <div><strong>Total frames:</strong> {total_frames.toLocaleString()}</div>
            <div><strong>Frames procesados:</strong> {frame_count.toLocaleString()}</div>
            <div><strong>FPS original:</strong> {fps_estimated.toFixed(1)}</div>
            <div><strong>Velocidad proc.:</strong> {processingSpeed} fps</div>
          </div>
        </div>

        {/* Métricas de Detecciones */}
        <div style={{
          backgroundColor: 'var(--gray-800)',
          padding: '1rem',
          borderRadius: '8px'
        }}>
          <h4 style={{ margin: '0 0 0.5rem 0', color: 'var(--primary-color)' }}>🎯 Detecciones</h4>
          <div style={{ fontSize: '0.9rem', lineHeight: '1.4' }}>
            <div><strong>Total detecciones:</strong> {totalDetections.toLocaleString()}</div>
            <div><strong>Etiquetas únicas:</strong> {Object.keys(labels).length}</div>
            <div><strong>Densidad:</strong> {total_frames > 0 ? (totalDetections / total_frames * 100).toFixed(1) : 0}%</div>
          </div>
        </div>
      </div>

      {/* Detalles por Etiqueta */}
      {Object.keys(labels).length > 0 && (
        <div style={{ marginTop: '1rem' }}>
          <h4 style={{ margin: '0 0 0.75rem 0', color: 'var(--primary-color)' }}>🏷️ Detalles por Etiqueta</h4>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '0.75rem'
          }}>
            {Object.entries(labels).map(([label, count]) => {
              const labelDetections = detections[label] || {};
              const framesDetected = labelDetections.qty_frames_detected || count;
              const percentage = labelDetections.frames_appearance_in_percentage || 
                               (total_frames > 0 ? (framesDetected / total_frames * 100) : 0);
              const duration = calculateLabelDuration(labelDetections, total_frames, fps_estimated);
              
              return (
                <div key={label} style={{
                  backgroundColor: 'var(--gray-700)',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  border: '1px solid var(--gray-600)'
                }}>
                  <div style={{
                    fontWeight: 'bold',
                    marginBottom: '0.5rem',
                    color: 'var(--white)',
                    fontSize: '0.95rem'
                  }}>
                    {label}
                  </div>
                  <div style={{ fontSize: '0.85rem', lineHeight: '1.3', color: 'var(--gray-300)' }}>
                    <div><strong>Apariciones:</strong> {count.toLocaleString()}</div>
                    <div><strong>Frames detectados:</strong> {framesDetected.toLocaleString()}</div>
                    <div><strong>Tiempo visible:</strong> {formatTime(duration)}</div>
                    <div><strong>% del video:</strong> {formatPercentage(percentage)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default VideoMetrics;