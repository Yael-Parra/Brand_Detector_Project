// StreamingCamera.jsx - Componente para detección de logos en tiempo real
// Implementa la lógica del detection_imagen_streaming.py adaptada para React
// Captura frames de la cámara web y los procesa usando el servicio backend

import React, { useState, useRef, useEffect } from 'react'

export default function StreamingCamera({ onResult, isAnalyzing, onAnalyzeToggle }) {
  // ===============================================
  // ESTADOS DEL COMPONENTE
  // ===============================================
  const [isCameraOn, setCameraOn] = useState(false)
  const [error, setError] = useState('')
  const [detectionStats, setDetectionStats] = useState({
    frameCount: 0,
    totalDetections: 0,
    labelStats: {},
    startTime: null
  })
  
  // Referencias para elementos DOM y streams
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const canvasRef = useRef(null)
  const timerRef = useRef(null)
  const lastProcessTime = useRef(Date.now())
  
  // URL del API backend
  const API_BASE = "http://localhost:8000"
  // ===============================================
  // FUNCIÓN: Iniciar cámara web
  // ===============================================
  const startCamera = async () => {
    try {
      setError('')
      
      // Solicitar acceso a la cámara web
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: false 
      })
      
      streamRef.current = stream
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      
      setCameraOn(true)
      
      // Notificar al padre que la cámara está lista
      if (onResult) {
        onResult({
          type: 'camera-ready',
          message: 'Cámara lista para análisis'
        })
      }
      
    } catch (err) {
      console.error('Error accediendo a la cámara:', err)
      setError('No se pudo acceder a la cámara. Verifica los permisos.')
    }
  }  // ===============================================
  // FUNCIÓN: Apagar cámara web
  // ===============================================
  const stopCamera = () => {
    // Detener detección si está activa
    if (isAnalyzing) {
      stopDetection()
    }
    
    // Detener timer de captura si existe
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    
    // Cerrar stream de cámara
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    
    // Resetear estadísticas
    setDetectionStats({
      frameCount: 0,
      totalDetections: 0,
      labelStats: {},
      startTime: null
    })
    
    setCameraOn(false)
    
    // Notificar al padre que la cámara está apagada
    if (onResult) {
      onResult({
        type: 'camera-off',
        message: 'Cámara desconectada'
      })
    }
    
    // Notificar al padre para detener análisis
    if (onAnalyzeToggle && isAnalyzing) {
      onAnalyzeToggle(false)
    }
  }

  // ===============================================
  // FUNCIÓN: Capturar frame y procesar detección
  // ===============================================
  const captureAndProcess = async () => {
    if (!videoRef.current || !videoRef.current.videoWidth) {
      console.warn("⚠️ Video no listo")
      return
    }

    try {
      // Crear canvas para capturar frame
      if (!canvasRef.current) {
        canvasRef.current = document.createElement('canvas')
      }
      
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      const video = videoRef.current
      
      // Configurar canvas con dimensiones del video
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      
      // Capturar frame actual
      ctx.drawImage(video, 0, 0)
      
      // Convertir a blob JPEG
      const blob = await new Promise(resolve => 
        canvas.toBlob(resolve, "image/jpeg", 0.8)
      )
      
      // Preparar FormData para envío
      const formData = new FormData()
      formData.append('file', blob, "frame.jpg")
      
      // Enviar al backend para procesamiento
      const response = await fetch(`${API_BASE}/process/image`, {
        method: "POST",
        body: formData
      })
      
      if (!response.ok) {
        throw new Error(`Error del servidor: ${response.status}`)
      }
      
      const result = await response.json()
      
      // Calcular tiempo transcurrido
      const currentTime = Date.now()
      const elapsed = (currentTime - lastProcessTime.current) / 1000
      lastProcessTime.current = currentTime
      
      // Actualizar estadísticas locales
      const newStats = {
        ...detectionStats,
        frameCount: detectionStats.frameCount + 1,
        totalDetections: detectionStats.totalDetections + (result.detections?.length || 0)
      }
      
      // Actualizar estadísticas de etiquetas
      if (result.detections && result.detections.length > 0) {
        const labelStats = { ...newStats.labelStats }
        
        result.detections.forEach(detection => {
          const label = detection.label || detection.class
          if (label) {
            if (!labelStats[label]) {
              labelStats[label] = { frames: 0, totalTime: 0 }
            }
            labelStats[label].frames += 1
            labelStats[label].totalTime += elapsed
          }
        })
        
        newStats.labelStats = labelStats
      }
      
      setDetectionStats(newStats)
        // Notificar al componente padre con los resultados
      if (onResult) {
        onResult({
          type: 'streaming-detection',
          detections: result.detections || [],
          annotated_image: result.annotated_jpg_base64,  // Corregir nombre del campo
          original_image: result.original_jpg_base64,
          stats: newStats.labelStats,
          frame_count: newStats.frameCount,
          timestamp: currentTime,
          has_detections: (result.detections?.length || 0) > 0
        })
      }
      
    } catch (error) {
      console.error("❌ Error al procesar frame:", error)
      setError(`Error de detección: ${error.message}`)
    }
  }
  // ===============================================
  // FUNCIÓN: Iniciar detección en tiempo real
  // ===============================================
  const startDetection = () => {
    if (!isCameraOn) {
      setError("Primero enciende la cámara")
      return
    }
    
    try {
      setError('')
      
      // Inicializar estadísticas
      setDetectionStats({
        frameCount: 0,
        totalDetections: 0,
        labelStats: {},
        startTime: Date.now()
      })
      
      lastProcessTime.current = Date.now()
      
      // Iniciar captura cada 250ms (4 FPS)
      timerRef.current = setInterval(captureAndProcess, 250)
      
      console.log("🎯 Detección en tiempo real iniciada")
      
    } catch (error) {
      console.error("❌ Error al iniciar detección:", error)
      setError(`Error al iniciar detección: ${error.message}`)
    }
  }
  // ===============================================
  // FUNCIÓN: Detener detección
  // ===============================================
  const stopDetection = () => {
    // Detener timer de captura
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    
    // Calcular estadísticas finales
    const totalTime = detectionStats.startTime ? 
      (Date.now() - detectionStats.startTime) / 1000 : 0
    
    const finalStats = {
      ...detectionStats,
      totalTime,
      avgDetectionsPerFrame: detectionStats.frameCount > 0 ? 
        detectionStats.totalDetections / detectionStats.frameCount : 0
    }
    
    // Notificar al padre con estadísticas finales
    if (onResult) {
      onResult({
        type: 'streaming-complete',
        final_statistics: finalStats,
        message: 'Análisis de streaming completado'
      })
    }
    
    console.log("✅ Detección finalizada:", finalStats)
  }
  // ===============================================
  // EFFECT: Manejar cambios en isAnalyzing
  // ===============================================
  useEffect(() => {
    if (isAnalyzing && isCameraOn) {
      startDetection()
    } else if (!isAnalyzing || !isCameraOn) {
      // Detener detección si no está analizando o la cámara está apagada
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [isAnalyzing, isCameraOn])

  // ===============================================
  // CLEANUP: Limpiar recursos al desmontar
  // ===============================================
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
    }
  }, [])
  // ===============================================
  // RENDER DEL COMPONENTE
  // ===============================================
  return (
    <div className="card">
      <h3>Streaming en Tiempo Real</h3>
      
      {/* Video preview - muestra lo que ve la cámara */}
      <div style={{ marginBottom: '1rem', textAlign: 'center' }}>
        <video 
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{
            width: '100%',
            maxWidth: '400px',
            height: '300px',
            backgroundColor: '#1a1a1a',
            borderRadius: '8px',
            objectFit: 'cover',
            border: '2px solid var(--border)'
          }}
        />
      </div>

      {/* Estadísticas en tiempo real */}
      {isAnalyzing && isCameraOn && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.5rem',
          backgroundColor: 'rgba(255, 255, 255, 0.05)',
          borderRadius: '6px',
          fontSize: '0.9rem',
          color: 'var(--white)'
        }}>
          <div>Frames procesados: {detectionStats.frameCount}</div>
          <div>Detecciones totales: {detectionStats.totalDetections}</div>
          {Object.keys(detectionStats.labelStats).length > 0 && (
            <div style={{ marginTop: '0.5rem' }}>
              <strong>Logos detectados:</strong>
              {Object.entries(detectionStats.labelStats).map(([label, stats], index) => (
                <div key={index} style={{ marginLeft: '1rem', fontSize: '0.8rem' }}>
                  {label}: {stats.frames} frames ({stats.totalTime.toFixed(1)}s)
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Botones de control */}
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
        {!isCameraOn ? (
          <button 
            className="button" 
            onClick={startCamera}
          >
            Encender Cámara
          </button>
        ) : (
          <button 
            className="button" 
            onClick={stopCamera}
          >
            Apagar Cámara
          </button>
        )}
      </div>

      {/* Mostrar mensajes de error si los hay */}
      {error && (
        <div style={{
          color: '#ff6b6b',
          fontSize: '0.9rem',
          marginTop: '0.5rem',
          textAlign: 'center',
          padding: '0.5rem',
          backgroundColor: 'rgba(255, 107, 107, 0.1)',
          borderRadius: '4px'
        }}>
          {error}
        </div>
      )}

      {/* Mostrar estado actual */}
      <div style={{
        fontSize: '0.9rem',
        color: 'var(--white)',
        marginTop: '0.5rem',
        textAlign: 'center',
        opacity: '0.8'
      }}>
        {!isCameraOn ? 
          'Enciende la cámara para comenzar' :
          isAnalyzing ? 
            'Analizando video en tiempo real...' :
            'Cámara lista. Presiona "Analizar" para comenzar la detección.'
        }
      </div>
    </div>
  )
}
