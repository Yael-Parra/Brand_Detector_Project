import React, { useState } from 'react';
import { useApp } from '../contexts/AppContext';

const AdvancedSettings = ({ isVisible = false, onToggle }) => {
  const { state, actions } = useApp();
  const [settings, setSettings] = useState({
    confidence: 0.5,
    maxDetections: 10,
    enableTracking: true,
    outputFormat: 'json'
  });

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const resetToDefaults = () => {
    setSettings({
      confidence: 0.5,
      maxDetections: 10,
      enableTracking: true,
      outputFormat: 'json'
    });
  };

  if (!isVisible) {
    return (
      <button 
        onClick={onToggle}
        style={{
          background: 'none',
          border: '1px solid #6c757d',
          color: '#6c757d',
          padding: '0.5rem 1rem',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.9rem',
          marginTop: '1rem'
        }}
      >
        ⚙️ Configuración Avanzada
      </button>
    );
  }

  return (
    <div style={{
      border: '1px solid #dee2e6',
      borderRadius: '8px',
      padding: '1.5rem',
      marginTop: '1rem',
      backgroundColor: '#f8f9fa'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1rem'
      }}>
        <h3 style={{ margin: 0, color: '#495057' }}>⚙️ Configuración Avanzada</h3>
        <button 
          onClick={onToggle}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '1.2rem',
            cursor: 'pointer',
            color: '#6c757d'
          }}
        >
          ✕
        </button>
      </div>

      <div style={{ display: 'grid', gap: '1rem' }}>
        {/* Confianza mínima */}
        <div>
          <label style={{ 
            display: 'block', 
            marginBottom: '0.5rem', 
            fontWeight: '500',
            color: '#495057'
          }}>
            Confianza mínima: {(settings.confidence * 100).toFixed(0)}%
          </label>
          <input
            type="range"
            min="0.1"
            max="1"
            step="0.1"
            value={settings.confidence}
            onChange={(e) => handleSettingChange('confidence', parseFloat(e.target.value))}
            style={{
              width: '100%',
              height: '6px',
              borderRadius: '3px',
              background: '#ddd',
              outline: 'none'
            }}
          />
          <small style={{ color: '#6c757d' }}>
            Ajusta qué tan seguro debe estar el modelo para detectar un logo
          </small>
        </div>

        {/* Máximo de detecciones */}
        <div>
          <label style={{ 
            display: 'block', 
            marginBottom: '0.5rem', 
            fontWeight: '500',
            color: '#495057'
          }}>
            Máximo de detecciones: {settings.maxDetections}
          </label>
          <input
            type="range"
            min="1"
            max="50"
            step="1"
            value={settings.maxDetections}
            onChange={(e) => handleSettingChange('maxDetections', parseInt(e.target.value))}
            style={{
              width: '100%',
              height: '6px',
              borderRadius: '3px',
              background: '#ddd',
              outline: 'none'
            }}
          />
          <small style={{ color: '#6c757d' }}>
            Número máximo de logos a detectar por frame
          </small>
        </div>

        {/* Seguimiento habilitado */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            id="enableTracking"
            checked={settings.enableTracking}
            onChange={(e) => handleSettingChange('enableTracking', e.target.checked)}
            style={{ transform: 'scale(1.2)' }}
          />
          <label htmlFor="enableTracking" style={{ 
            fontWeight: '500',
            color: '#495057',
            cursor: 'pointer'
          }}>
            Habilitar seguimiento de objetos
          </label>
        </div>
        <small style={{ color: '#6c757d', marginTop: '-0.5rem' }}>
          Mejora la detección en videos al seguir objetos entre frames
        </small>

        {/* Formato de salida */}
        <div>
          <label style={{ 
            display: 'block', 
            marginBottom: '0.5rem', 
            fontWeight: '500',
            color: '#495057'
          }}>
            Formato de salida
          </label>
          <select
            value={settings.outputFormat}
            onChange={(e) => handleSettingChange('outputFormat', e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              backgroundColor: 'white'
            }}
          >
            <option value="json">JSON detallado</option>
            <option value="simple">JSON simplificado</option>
            <option value="csv">CSV</option>
          </select>
          <small style={{ color: '#6c757d' }}>
            Formato en el que se exportarán los resultados
          </small>
        </div>

        {/* Botones de acción */}
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          marginTop: '1rem',
          paddingTop: '1rem',
          borderTop: '1px solid #dee2e6'
        }}>
          <button
            onClick={resetToDefaults}
            style={{
              flex: 1,
              padding: '0.5rem',
              border: '1px solid #6c757d',
              backgroundColor: 'white',
              color: '#6c757d',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Restablecer
          </button>
          <button
            onClick={() => {
              // Aquí podrías guardar la configuración en el contexto
              console.log('Configuración guardada:', settings);
              onToggle();
            }}
            style={{
              flex: 2,
              padding: '0.5rem',
              border: 'none',
              backgroundColor: '#007bff',
              color: 'white',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Aplicar Configuración
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdvancedSettings;