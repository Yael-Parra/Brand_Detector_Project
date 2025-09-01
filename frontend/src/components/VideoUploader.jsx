import React from 'react'

export default function VideoUploader({onResult}){  async function handleFile(e){
    const file = e.target.files[0]
    if(!file) return
    // Solo notificar que hay archivo, no procesar aún
    onResult(file)
  }

  return (
    <div className="card">
      <h3>Video</h3>
      <input type="file" accept="video/*" onChange={handleFile} />
      <div style={{fontSize: '0.9rem', color: 'var(--white)', marginTop: '0.5rem'}}>
        Formatos: MP4, AVI, MOV
      </div>
    </div>
  )
}
