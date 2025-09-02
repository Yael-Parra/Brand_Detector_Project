import React, { useRef } from 'react'

export default function ImageUploader({onResult}){
  const ref = useRef()
  async function handleFile(e){
    const file = e.target.files[0]
    if(!file) return
    // Solo notificar que hay archivo, no procesar aún
    onResult(file)
  }

  return (
    <div className="card">
      <h3>Imagen</h3>
      <input ref={ref} type="file" accept="image/*" onChange={handleFile} />      <div style={{fontSize: '0.9rem', color: 'var(--white)', marginTop: '0.5rem'}}>
        Formatos: JPG, PNG, WEBP
      </div>
    </div>
  )
}
