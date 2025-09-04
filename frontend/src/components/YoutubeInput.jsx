import React, { useState } from 'react'

export default function YoutubeInput({onResult, onUrlChange}){
  const [url, setUrl] = useState('')

  function handleChange(e) {
    const newUrl = e.target.value
    setUrl(newUrl)
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
      />
      <div style={{fontSize: '0.9rem', color: 'var(--white)', marginTop: '0.5rem'}}>
        Pega el enlace completo del video
      </div>
    </div>
  )
}
