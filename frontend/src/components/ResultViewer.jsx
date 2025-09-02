import React, { useEffect, useRef, useState } from 'react'

export default function ResultViewer({data, jobId}){
  const canvasRef = useRef()
  const videoRef = useRef()
  const [summary, setSummary] = useState(null)
  const [processingStatus, setProcessingStatus] = useState('')
  const [isLiveProcessing, setIsLiveProcessing] = useState(false)
  const statusCheckInterval = useRef(null)

  // Función para verificar el estado del procesamiento
  const checkProcessingStatus = async (id) => {
    if (!id) return
    
    try {
      console.log(`Verificando estado para job_id: ${id}`)
      const response = await fetch(`http://localhost:8000/status/${id}`)
      
      if (!response.ok) {
        console.error(`Error al obtener estado: ${response.status} ${response.statusText}`)
        setProcessingStatus(`Error al obtener estado: ${response.status}. Reintentando...`)
        
        // Si recibimos un 404, pero sabemos que es un trabajo válido, actualizamos la UI
        // para evitar confundir al usuario
        if (response.status === 404 && id && (id.startsWith('video-job-') || id.startsWith('youtube-job-'))) {
          console.log('Trabajo no encontrado en el servidor, pero parece válido. Mostrando información temporal.')
          setSummary(prev => ({
            ...prev,
            totalDetections: prev?.totalDetections || 0,
            processingProgress: prev?.processingProgress || 0
          }))
        }
        return
      }
      
      const statusData = await response.json()
      console.log(`Estado recibido para ${id}:`, statusData)
        
        // Actualizar el estado de procesamiento con información detallada
        if (statusData.status === 'processing') {
          // Mostrar progreso si está disponible
          if (statusData.progress) {
            setProcessingStatus(`Procesando: ${Math.round(statusData.progress)}%`)
          } else if (statusData.frame_count) {
            setProcessingStatus(`Procesando: ${statusData.frame_count} frames analizados`)
          } else {
            setProcessingStatus('Procesando video...')
          }
          
          // Actualizar el resumen con las detecciones en tiempo real
          if (statusData.detections && typeof statusData.detections === 'number') {
            // Crear un objeto para las etiquetas si está disponible
            const labelCounts = statusData.labels || {}
            
            setSummary(prev => ({
              ...prev,
              totalDetections: statusData.detections,
              processingProgress: statusData.progress || 0,
              labelCounts: labelCounts // Añadir conteo de etiquetas
            }))
          }
        } else if (statusData.status === 'completed') {
          // Si el procesamiento ha terminado, detener el intervalo
          clearInterval(statusCheckInterval.current)
          setProcessingStatus('Procesamiento completado')
          
          // Actualizar datos si es necesario
          if (statusData.detections) {
            // Obtener las etiquetas detectadas
            let labelCounts = {}
            
            // Manejar diferentes formatos de respuesta
            if (statusData.labels) {
              // Si tenemos etiquetas directamente
              labelCounts = statusData.labels
            } else if (typeof statusData.detections === 'object') {
              // Si las detecciones están en formato de objeto
              labelCounts = Object.keys(statusData.detections).reduce((acc, key) => {
                acc[key] = statusData.detections[key].frames || 0
                return acc
              }, {})
            }
            
            // Actualizar con los resultados finales
            setSummary(prev => ({
              ...prev,
              totalDetections: typeof statusData.detections === 'number' 
                ? statusData.detections 
                : Object.values(statusData.detections).reduce((sum, item) => sum + (item.frames || 0), 0),
              labelCounts: labelCounts,
              processingProgress: 100
            }))
          }
        } else if (statusData.status === 'error') {
          clearInterval(statusCheckInterval.current)
          setProcessingStatus(`Error: ${statusData.error || 'Error desconocido'}`)
        }
    } catch (error) {
      console.error('Error al verificar estado:', error)
      
      // Manejar errores de red o conexión
      setProcessingStatus(`Error de conexión: ${error.message}. Reintentando...`)
      
      // Si es un error de red pero tenemos un jobId válido, actualizar la UI con información temporal
      if (id && (id.startsWith('video-job-') || id.startsWith('youtube-job-'))) {
        console.log('Error de red con jobId válido. Mostrando información temporal.')
        setSummary(prev => ({
          ...prev,
          totalDetections: prev?.totalDetections || 0,
          processingProgress: prev?.processingProgress || 0
        }))
      }
    }
  }

  // Efecto para iniciar la verificación de estado cuando hay un jobId
  useEffect(() => {
    if (jobId) {
      console.log(`Iniciando monitoreo para job_id: ${jobId}`)
      
      // Limpiar intervalo anterior si existe
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current)
      }
      
      // Verificar estado inmediatamente
      checkProcessingStatus(jobId)
      
      // Configurar intervalo para verificar estado cada 2 segundos (más frecuente)
      statusCheckInterval.current = setInterval(() => {
        checkProcessingStatus(jobId)
      }, 2000)
      
      // Si es un trabajo de YouTube o video MP4, activar modo de procesamiento en vivo
      if (jobId.startsWith('youtube-job-') || jobId.startsWith('video-job-')) {
        setIsLiveProcessing(true)
        console.log(`Modo de procesamiento en vivo activado para ${jobId}`)
      }
      
      // Establecer un timeout de seguridad para detener el intervalo después de 10 minutos
      const safetyTimeout = setTimeout(() => {
        if (statusCheckInterval.current) {
          console.log('Timeout de seguridad alcanzado, deteniendo verificación de estado')
          clearInterval(statusCheckInterval.current)
          setProcessingStatus('Tiempo de espera agotado. El procesamiento puede continuar en segundo plano.')
        }
      }, 10 * 60 * 1000) // 10 minutos
      
      return () => {
        if (statusCheckInterval.current) {
          clearInterval(statusCheckInterval.current)
        }
        clearTimeout(safetyTimeout)
      }
    }
  }, [jobId])

  useEffect(()=>{
    if(!data) return
    setSummary(buildSummary(data))
    if(data.image_url){
      drawImage(data.image_url, data.detections||[])
    }
  },[data])
  
  // Efecto para configurar el reproductor de video en tiempo real
  useEffect(() => {
    if (isLiveProcessing && data && data.video_url && videoRef.current) {
      const video = videoRef.current
      
      // Configurar el video para reproducción automática
      video.autoplay = true
      video.muted = false // Permitir audio
      video.controls = true
      
      // Manejar errores de reproducción
      const handleVideoError = (e) => {
        console.error('Error en la reproducción del video:', e)
        setProcessingStatus('Error al reproducir el video')
      }
      
      video.addEventListener('error', handleVideoError)
      
      return () => {
        video.removeEventListener('error', handleVideoError)
      }
    }
  }, [isLiveProcessing, data])
  
  function buildSummary(d){
    const totalDetections = (d.detections||[]).filter(x=>x.class==='logo-brand').length
    const frames = (d.detections||[]).filter(x=>x.class==='logo-brand')
    
    // Crear un objeto para contar las etiquetas detectadas
    const labelCounts = {}
    if (d.detections && Array.isArray(d.detections)) {
      d.detections.forEach(detection => {
        if (detection.class) {
          labelCounts[detection.class] = (labelCounts[detection.class] || 0) + 1
        }
      })
    }
    
    return { totalDetections, frames, labelCounts }
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
      
      {!data && !jobId && (
        <div style={{textAlign: 'center', padding: '3rem 1rem', color: 'var(--white)'}}>
          <div style={{fontSize: '3rem', marginBottom: '1rem', color: 'var(--white)'}}>No hay resultados</div>
          <p>Selecciona una imagen, video o pega un enlace de YouTube para comenzar el análisis.</p>
        </div>
      )}

      {jobId && (
        <div style={{marginTop: '1rem', padding: '1rem', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '10px', border: '1px solid var(--white)'}}>
          <div style={{color: 'var(--white)', fontWeight: '600'}}>Job ID: {jobId}</div>
          <div style={{color: 'var(--white)', fontSize: '0.9rem'}}>{processingStatus || 'Procesamiento en progreso...'}</div>
          
          {/* Barra de progreso para procesamiento en tiempo real */}
          {isLiveProcessing && summary && summary.processingProgress !== undefined && (
            <div style={{marginTop: '0.5rem', background: 'var(--gray-dark)', borderRadius: '5px', height: '10px', position: 'relative'}}>
              <div 
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  height: '100%',
                  width: `${summary.processingProgress}%`,
                  background: 'var(--primary)',
                  borderRadius: '5px'
                }}
              ></div>
              <span style={{position: 'absolute', right: '5px', top: '-18px', fontSize: '0.8rem', color: 'var(--white)'}}>
                {Math.round(summary.processingProgress)}%
              </span>
            </div>
          )}
          
          {/* Mostrar detecciones en tiempo real */}
          {isLiveProcessing && summary && summary.totalDetections !== undefined && (
            <div style={{marginTop: '0.5rem', color: 'var(--white)'}}>
              <p>Detecciones encontradas: {summary.totalDetections}</p>
            </div>
          )}
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
              <div style={{fontSize: '2rem', color: 'var(--white)'}}>{summary.totalDetections || 0}</div>
              <div style={{color: 'var(--white)'}}>Detecciones totales</div>
            </div>
            {data.total_video_time_segs && (
              <div>
                <div style={{fontSize: '2rem', color: 'var(--white)'}}>{data.total_video_time_segs}s</div>
                <div style={{color: 'var(--white)'}}>Duración total</div>
              </div>
            )}
          </div>
          
          {/* Sección de etiquetas detectadas */}
          {summary.labelCounts && Object.keys(summary.labelCounts).length > 0 && (
            <div style={{marginTop: '1.5rem'}}>
              <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>Etiquetas detectadas</h4>
              <div style={{background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '10px'}}>
                {Object.entries(summary.labelCounts).map(([label, count], index) => (
                  <div key={index} style={{display: 'flex', justifyContent: 'space-between', padding: '0.5rem 0', borderBottom: index < Object.keys(summary.labelCounts).length - 1 ? '1px solid rgba(255,255,255,0.1)' : 'none'}}>
                    <span style={{color: 'var(--white)', fontWeight: '500'}}>{label}</span>
                    <span style={{color: 'var(--white)', fontWeight: '700'}}>{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
