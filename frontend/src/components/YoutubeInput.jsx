import React, { useState } from 'react'
import { useApp } from '../contexts/AppContext'
import { useApi } from '../hooks/useApi'
import { useNotification } from '../contexts/NotificationContext'

export default function YoutubeInput({ onResult, onUrlChange }) {
  const [url, setUrl] = useState('')
  const [isValidUrl, setIsValidUrl] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)
  
  const { setJobId, setStatus, setResults, setSelectedFile } = useApp()
  const { processYouTube } = useApi()
  const { addNotification } = useNotification()

  function handleChange(e) {
    const newUrl = e.target.value
    setUrl(newUrl)
    
    // Validar si es una URL de YouTube válida
    const isValid = newUrl === '' || 
      newUrl.match(/^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/) !== null
    
    setIsValidUrl(isValid)
    
    if (onUrlChange) onUrlChange(newUrl)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && isValidUrl && url) {
      // Solo actualizar el contexto, el procesamiento lo maneja AppPage
      if (onResult) {
        onResult({
          url: url,
          type: 'youtube',
          isValid: isValidUrl
        })
      }
    }
  }

  return (
    <div className="card">
      <h3>YouTube</h3>
      <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
        <input 
          value={url} 
          onChange={handleChange}
          onKeyPress={handleKeyPress}
          placeholder="https://youtube.com/watch?v=..." 
          type="text"
          disabled={isProcessing}
          style={{
            border: !isValidUrl ? '2px solid #ff3333' : 'none',
            flex: 1,
            opacity: isProcessing ? 0.7 : 1
          }}
        />
        {/* El botón de procesamiento se maneja desde AppPage */}
      </div>
      <div style={{
        fontSize: '0.9rem', 
        color: isValidUrl ? 'var(--white)' : '#ff3333', 
        marginTop: '0.5rem'
      }}>
        {isValidUrl ? 
          'Pega el enlace completo del video y presiona "Analizar"' : 
          'Por favor, ingresa una URL de YouTube válida'
        }
      </div>
    </div>
  )
}
