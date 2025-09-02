// StreamingCamera.jsx - Componente para manejar la cámara web
// Este componente permite al usuario encender/apagar su cámara web
// Cuando la cámara está encendida, notifica al padre que está lista

import React, { useState, useRef, useEffect } from 'react'

export default function StreamingCamera({ onResult }) {  // Estados del componente
  const [isCameraOn, setCameraOn] = useState(false) // ¿Está la cámara encendida?
  const [error, setError] = useState('') // Mensajes de error
  const videoRef = useRef(null) // Referencia al elemento video HTML
  const streamRef = useRef(null) // Referencia al stream de la cámara

  // Función para encender la cámara
  const startCamera = async () => {
    try {
      setError('') // Limpiar errores previos
      
      // Pedir acceso a la cámara web del usuario
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: true, 
        audio: false 
      })
      
      // Guardar el stream para poder cerrarlo después
      streamRef.current = stream
      
      // Conectar el stream al elemento video HTML
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      
      // Actualizar el estado: cámara encendida
      setCameraOn(true)
      
      // Notificar al componente padre que la cámara está lista
      if (onResult) {
        onResult("camera-ready") // Le decimos que ya puede usar el botón Analizar
      }
      
    } catch (err) {
      // Si algo sale mal (usuario rechaza permisos, no hay cámara, etc.)
      console.error('Error accediendo a la cámara:', err)
      setError('No se pudo acceder a la cámara. Verifica los permisos.')
    }
  }

  // Función para apagar la cámara
  const stopCamera = () => {
    // Si hay un stream activo, cerrar todas las pistas (tracks)
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    
    // Limpiar el elemento video
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    
    // Actualizar estado: cámara apagada
    setCameraOn(false)
    setError('')
    
    // Notificar al padre que la cámara ya no está disponible
    if (onResult) {
      onResult("camera-off")
    }
  }

  // Cleanup: cerrar cámara cuando el componente se desmonte
  useEffect(() => {
    return () => {
      stopCamera() // Asegurar que cerramos la cámara al salir
    }
  }, [])

  return (
    <div className="card">
      <h3>Streaming en Tiempo Real</h3>
      
      {/* Video preview - muestra lo que ve la cámara */}
      <div style={{ marginBottom: '1rem' }}>
        <video 
          ref={videoRef}
          autoPlay
          muted
          playsInline
          style={{
            width: '100%',
            maxWidth: '400px',
            height: '300px',
            backgroundColor: '#000',
            borderRadius: '8px',
            objectFit: 'cover'
          }}
        />
      </div>

      {/* Botones de control */}
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
        {!isCameraOn ? (
          // Mostrar botón "Encender" cuando la cámara está apagada
          <button 
            className="button" 
            onClick={startCamera}
          >
            Encender Cámara
          </button>        ) : (
          // Mostrar botón "Apagar" cuando la cámara está encendida
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
          textAlign: 'center'
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
        {isCameraOn ? 
          'Cámara lista. Presiona "Analizar" para comenzar la detección.' : 
          'Enciende la cámara para comenzar'
        }
      </div>
    </div>
  )
}
