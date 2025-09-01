import React, { useState } from 'react'

export default function YoutubeInput({onResult, onUrlChange}){
  const [url, setUrl] = useState('')
  const [isValidUrl, setIsValidUrl] = useState(true)

  function handleChange(e) {
    const newUrl = e.target.value
    setUrl(newUrl)
    
    // Validar si es una URL de YouTube válida
    const isValid = newUrl === '' || 
      newUrl.match(/^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/) !== null
    
    setIsValidUrl(isValid)
    
    if(onUrlChange) onUrlChange(newUrl)
  }

  return (
    <div className="card">
      <h3>YouTube</h3>
      <input 
        value={url} 
        onChange={handleChange} 
        placeholder="https://youtube.com/watch?v=..." 
        type="text"
        style={{
          border: !isValidUrl ? '2px solid #ff3333' : 'none'
        }}
      />
      <div style={{fontSize: '0.9rem', color: isValidUrl ? 'var(--white)' : '#ff3333', marginTop: '0.5rem'}}>
        {isValidUrl ? 'Pega el enlace completo del video' : 'Por favor, ingresa una URL de YouTube válida'}
      </div>
    </div>
  )
}
