import React, { useEffect, useRef, useState } from 'react'

export default function ResultViewer({data, jobId}){
  const canvasRef = useRef()
  const videoRef = useRef()
  const [summary, setSummary] = useState(null)

  useEffect(()=>{
    if(!data) return
    setSummary(buildSummary(data))
    if(data.image_url){
      drawImage(data.image_url, data.detections||[])
    }
  },[data])
  function buildSummary(d){
    const totalDetections = (d.detections||[]).filter(x=>x.class==='logo-brand').length
    const frames = (d.detections||[]).filter(x=>x.class==='logo-brand')
    return { totalDetections, frames }
  }
  function drawImage(url, detections){
    const img = new Image()
    img.onload = ()=>{
      const canvas = canvasRef.current
      if(!canvas) return
      canvas.width = img.width
      canvas.height = img.height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(img,0,0)
      ctx.strokeStyle = '#ffffff'
      ctx.lineWidth = 4
      ctx.font = 'bold 16px Inter, sans-serif'
      detections.forEach(box=>{
        const [x,y,w,h] = box.bbox
        ctx.strokeRect(x,y,w,h)
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
        ctx.fillRect(x, y-30, 160, 30)
        ctx.fillStyle = '#000000'
        ctx.fillText(`${box.class} ${Math.round(box.score*100)}%`, x+8, y-8)
      })
    }
    img.src = url
  }

  return (
    <div className="card results">
      <h3>Resultados del Análisis</h3>
      
      {!data && (
        <div style={{textAlign: 'center', padding: '3rem 1rem', color: 'var(--white)'}}>
          <div style={{fontSize: '3rem', marginBottom: '1rem', color: 'var(--white)'}}>No hay resultados</div>
          <p>Selecciona una imagen, video o pega un enlace de YouTube para comenzar el análisis.</p>
        </div>
      )}

      {data && data.image_url && (
        <div className="preview">
          <canvas ref={canvasRef} style={{maxWidth: '100%', height: 'auto'}}></canvas>
        </div>
      )}

      {data && data.video_url && (
        <div className="preview">
          <video ref={videoRef} controls src={data.video_url} style={{maxWidth:'100%', borderRadius: '10px'}}/>          <div style={{marginTop: '1.5rem'}}>
            <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>⏱️ Timestamps con logos detectados:</h4>
            <div style={{background: 'var(--gray-dark)', padding: '1rem', borderRadius: '10px'}}>
              {(data.detections||[]).filter(d=>d.class==='logo-brand').map((det, i) => (
                <div key={i} style={{padding: '0.5rem 0', borderBottom: i < summary?.frames.length - 1 ? '1px solid var(--gray)' : 'none'}}>
                  <strong style={{color: 'var(--white)'}}>{det.timestamp}s</strong> - 
                  Confianza: {Math.round(det.score*100)}%
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {summary && (        <div style={{marginTop: '2rem', padding: '1.5rem', background: 'var(--gray-dark)', borderRadius: '15px'}}>
          <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>Resumen</h4>
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem'}}>
            <div>
              <div style={{fontSize: '2rem', color: 'var(--white)'}}>{summary.totalDetections}</div>
              <div style={{color: 'var(--white)'}}>Detecciones totales</div>
            </div>
            {data.total_video_time_segs && (
              <div>
                <div style={{fontSize: '2rem', color: 'var(--white)'}}>{data.total_video_time_segs}s</div>
                <div style={{color: 'var(--white)'}}>Duración total</div>
              </div>
            )}
          </div>
        </div>
      )}      {jobId && (
        <div style={{marginTop: '1rem', padding: '1rem', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '10px', border: '1px solid var(--white)'}}>
          <div style={{color: 'var(--white)', fontWeight: '600'}}>Job ID: {jobId}</div>
          <div style={{color: 'var(--white)', fontSize: '0.9rem'}}>Procesamiento en progreso...</div>
        </div>
      )}
    </div>
  )
}
