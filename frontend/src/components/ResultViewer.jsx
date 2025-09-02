import React, { useEffect, useRef, useState } from 'react'

export default function ResultViewer({data, jobId}){
  const canvasRef = useRef()
  const streamingCanvasRef = useRef() // Canvas específico para streaming
  const videoRef = useRef()
  const [summary, setSummary] = useState(null)
  const [processingStatus, setProcessingStatus] = useState('')
  const [isLiveProcessing, setIsLiveProcessing] = useState(false)
  const statusCheckInterval = useRef(null)

  // ===============================================
  // FUNCIONES ESPECÍFICAS PARA STREAMING
  // ===============================================
  
  // Construir resumen específico para streaming
  function buildStreamingSummary(streamingData) {
    const detections = streamingData.detections || []
    const totalDetections = detections.length
    
    // Contar etiquetas en el frame actual
    const labelCounts = {}
    detections.forEach(detection => {
      const label = detection.label || detection.class
      if (label) {
        labelCounts[label] = (labelCounts[label] || 0) + 1
      }
    })
    
    return {
      totalDetections,
      labelCounts,
      frameCount: streamingData.frame_count || 0,
      hasDetections: streamingData.has_detections || false,
      timestamp: streamingData.timestamp || Date.now()
    }
  }
    // Mostrar imagen anotada del streaming directamente
  function drawStreamingImage(annotatedImageBase64) {
    if (!annotatedImageBase64 || !streamingCanvasRef.current) return
    
    const img = new Image()
    img.onload = () => {
      const canvas = streamingCanvasRef.current
      if (!canvas) return
      
      // Configurar tamaño máximo más pequeño para mejor presentación
      const maxWidth = 480   // Reducido de 800 a 480
      const maxHeight = 360  // Reducido de 600 a 360
      
      let { width, height } = img
      
      // Calcular escala manteniendo proporción
      const scaleX = maxWidth / width
      const scaleY = maxHeight / height
      const scale = Math.min(scaleX, scaleY, 1) // No aumentar si ya es pequeño
      
      const newWidth = Math.floor(width * scale)
      const newHeight = Math.floor(height * scale)
      
      // Configurar canvas con las nuevas dimensiones
      canvas.width = newWidth
      canvas.height = newHeight
      
      // Configurar estilos CSS para responsividad
      canvas.style.width = `${newWidth}px`
      canvas.style.height = `${newHeight}px`
      canvas.style.maxWidth = '100%'
      canvas.style.height = 'auto'
      
      const ctx = canvas.getContext('2d')
      
      // Limpiar canvas antes de dibujar
      ctx.clearRect(0, 0, newWidth, newHeight)
      
      // Dibujar imagen escalada
      ctx.drawImage(img, 0, 0, newWidth, newHeight)
    }
    img.src = `data:image/jpeg;base64,${annotatedImageBase64}`
  }

  const checkProcessingStatus = async (id) => {
    if (!id) return
    
    try {
      console.log(`Verificando estado para job_id: ${id}`)
      const response = await fetch(`http://localhost:8000/status/${id}`)
      
      if (!response.ok) {
        console.error(`Error al obtener estado: ${response.status} ${response.statusText}`)
        setProcessingStatus(`Error al obtener estado: ${response.status}. Reintentando...`)
        
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
        
        if (statusData.status === 'processing') {
          if (statusData.progress) {
            setProcessingStatus(`Procesando: ${Math.round(statusData.progress)}%`)
          } else if (statusData.frame_count) {
            setProcessingStatus(`Procesando: ${statusData.frame_count} frames analizados`)
          } else {
            setProcessingStatus('Procesando video...')
          }
          
          if (statusData.detections) {
            if (typeof statusData.detections === 'number') {
              const labelCounts = statusData.labels || {}
              
              setSummary(prev => ({
                ...prev,
                totalDetections: statusData.detections,
                processingProgress: statusData.progress || 0,
                labelCounts: labelCounts
              }))
              
              if ((statusData.progress || 0) >= 100 && !data) {
                setData({
                  detections: statusData.detections_list || [],
                  video_url: processingVideoUrl
                })
              }
            } else if (Array.isArray(statusData.detections)) {
              const labelCounts = {}
              statusData.detections.forEach(detection => {
                if (detection.label) {
                  labelCounts[detection.label] = (labelCounts[detection.label] || 0) + 1
                }
              })
              
              setSummary(prev => ({
                ...prev,
                totalDetections: statusData.detections.length,
                processingProgress: statusData.progress || 0,
                labelCounts: labelCounts,
                detectionsList: statusData.detections
              }))
              
              if ((statusData.progress || 0) >= 100 && !data) {
                setData({
                  detections: statusData.detections,
                  video_url: processingVideoUrl
                })
              }
            }
          }
        } else if (statusData.status === 'completed') {
          clearInterval(statusCheckInterval.current)
          setProcessingStatus('Procesamiento completado')
          
          if (statusData.detections) {
            let labelCounts = {}
            
            if (statusData.labels) {
              labelCounts = statusData.labels
            } else if (typeof statusData.detections === 'object') {
              labelCounts = Object.keys(statusData.detections).reduce((acc, key) => {
                acc[key] = statusData.detections[key].frames || 0
                return acc
              }, {})
            }
            
            setSummary(prev => ({
              ...prev,
              totalDetections: typeof statusData.detections === 'number' 
                ? statusData.detections 
                : Object.values(statusData.detections).reduce((sum, item) => sum + (item.frames || 0), 0),
              labelCounts: labelCounts,
              processingProgress: 100
            }))
            
            if (!data) {
              setData({
                detections: Array.isArray(statusData.detections) ? statusData.detections : statusData.detections_list || [],
                video_url: processingVideoUrl
              })
            }
          }
        } else if (statusData.status === 'error') {
          clearInterval(statusCheckInterval.current)
          setProcessingStatus(`Error: ${statusData.error || 'Error desconocido'}`)
        }
    } catch (error) {
      console.error('Error al verificar estado:', error)
      
      setProcessingStatus(`Error de conexión: ${error.message}. Reintentando...`)
      
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

  const [processingVideoUrl, setProcessingVideoUrl] = useState(null)

  useEffect(() => {
    if (jobId) {
      console.log(`Iniciando monitoreo para job_id: ${jobId}`)
      
      if (statusCheckInterval.current) {
        clearInterval(statusCheckInterval.current)
      }
      
      checkProcessingStatus(jobId)
      
      statusCheckInterval.current = setInterval(() => {
        checkProcessingStatus(jobId)
      }, 2000)
      
      if (jobId.startsWith('youtube-job-') || jobId.startsWith('video-job-')) {
        setIsLiveProcessing(true)
        console.log(`Modo de procesamiento en vivo activado para ${jobId}`)
        
        fetch(`http://localhost:8000/video/${jobId}`)
          .then(response => {
            if (response.ok) {
              return response.json()
            }
            throw new Error('No se pudo obtener la URL del video')
          })
          .then(data => {
            if (data.video_url) {
              console.log('URL de video obtenida para reproducción durante procesamiento:', data.video_url)
              setProcessingVideoUrl(data.video_url)
            }
          })
          .catch(error => {
            console.error('Error al obtener URL del video:', error)
          })
      }
      
      const safetyTimeout = setTimeout(() => {
        if (statusCheckInterval.current) {
          console.log('Timeout de seguridad alcanzado, deteniendo verificación de estado')
          clearInterval(statusCheckInterval.current)
          setProcessingStatus('Tiempo de espera agotado. El procesamiento puede continuar en segundo plano.')
        }
      }, 10 * 60 * 1000)
      
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
    
    // Manejar datos de streaming en tiempo real
    if(data.type === 'streaming-detection') {
      setSummary(buildStreamingSummary(data))
      
      // Mostrar imagen anotada si está disponible
      if(data.annotated_image) {
        drawStreamingImage(data.annotated_image)
      }
    } else {
      // Manejar datos de imagen/video normales
      setSummary(buildSummary(data))
      if(data.image_url){
        drawImage(data.image_url, data.detections||[])
      }
    }
  },[data])
  
  useEffect(() => {
    if (isLiveProcessing && data && data.video_url && videoRef.current) {
      const video = videoRef.current
      
      video.autoplay = true
      video.muted = false
      video.controls = true
      
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
    const totalDetections = (d.detections||[]).length
    const frames = (d.detections||[])
    
    const labelCounts = {}
    if (d.detections && Array.isArray(d.detections)) {
      d.detections.forEach(detection => {
        if (detection.label) {
          labelCounts[detection.label] = (labelCounts[detection.label] || 0) + 1
        } else if (detection.class) {
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
        let x, y, w, h;
        if (box.bbox_xyxy) {
          const [x1, y1, x2, y2] = box.bbox_xyxy;
          x = x1;
          y = y1;
          w = x2 - x1;
          h = y2 - y1;
        } else if (box.bbox) {
          [x, y, w, h] = box.bbox;
        } else {
          return;
        }
        
        ctx.strokeRect(x, y, w, h)
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
        ctx.fillRect(x, y-30, 160, 30)
        ctx.fillStyle = '#000000'
        
        const label = box.label || box.class || 'desconocido';
        const score = box.score ? Math.round(box.score*100) : 0;
        ctx.fillText(`${label} ${score}%`, x+8, y-8)
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
          
          {isLiveProcessing && summary && summary.totalDetections !== undefined && (
            <div style={{marginTop: '0.5rem', color: 'var(--white)'}}>
              <p>Detecciones encontradas: {summary.totalDetections}</p>
              
              {summary.labelCounts && Object.keys(summary.labelCounts).length > 0 && (
                <div style={{marginTop: '0.5rem'}}>
                  <p>Etiquetas detectadas:</p>
                  <div style={{background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '5px', marginTop: '0.5rem'}}>
                    {Object.entries(summary.labelCounts).map(([label, count], index) => (
                      <div key={index} style={{display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0'}}>
                        <span>{label}</span>
                        <span style={{fontWeight: 'bold'}}>{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}        </div>
      )}      {/* Sección específica para streaming en tiempo real */}
      {data && data.type === 'streaming-detection' && (
        <div className="preview">
          <h4 style={{color: 'var(--white)', marginBottom: '1rem', textAlign: 'center'}}>Detección en Tiempo Real</h4>
          
          {/* Contenedor del canvas para streaming */}
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            marginBottom: '1.5rem',
            padding: '1rem',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '15px',
            border: '1px solid var(--border)'
          }}>
            <canvas 
              ref={streamingCanvasRef} 
              style={{
                borderRadius: '10px',
                border: '2px solid var(--white)',
                boxShadow: '0 4px 15px rgba(0, 0, 0, 0.3)',
                display: 'block'
              }}
            />
          </div>
            {/* Estadísticas del frame actual - Layout mejorado */}
          {summary && (
            <div style={{
              background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05))', 
              padding: '1.5rem', 
              borderRadius: '15px',
              marginTop: '1rem',
              border: '1px solid rgba(255, 255, 255, 0.1)'
            }}>
              {/* Grid de estadísticas principales */}
              <div style={{
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
                gap: '1rem',
                marginBottom: '1rem'
              }}>
                <div style={{
                  textAlign: 'center',
                  padding: '0.75rem',
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: '10px'
                }}>
                  <div style={{fontSize: '1.8rem', color: '#64B5F6', fontWeight: 'bold'}}>
                    {summary.frameCount || 0}
                  </div>
                  <div style={{color: 'var(--white)', fontSize: '0.85rem', opacity: '0.9'}}>Frames</div>
                </div>
                <div style={{
                  textAlign: 'center',
                  padding: '0.75rem',
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: '10px'
                }}>
                  <div style={{fontSize: '1.8rem', color: '#81C784', fontWeight: 'bold'}}>
                    {summary.totalDetections || 0}
                  </div>
                  <div style={{color: 'var(--white)', fontSize: '0.85rem', opacity: '0.9'}}>Detecciones</div>
                </div>
                <div style={{
                  textAlign: 'center',
                  padding: '0.75rem',
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: '10px'
                }}>
                  <div style={{
                    fontSize: '1.8rem', 
                    color: summary.hasDetections ? '#4CAF50' : '#FF8A65', 
                    fontWeight: 'bold'
                  }}>
                    {summary.hasDetections ? '●' : '○'}
                  </div>
                  <div style={{color: 'var(--white)', fontSize: '0.85rem', opacity: '0.9'}}>
                    {summary.hasDetections ? 'Activo' : 'Inactivo'}
                  </div>
                </div>
              </div>
                {/* Sección de etiquetas detectadas */}
              {summary.labelCounts && Object.keys(summary.labelCounts).length > 0 ? (
                <div>
                  <h5 style={{
                    color: 'var(--white)', 
                    marginBottom: '0.75rem',
                    fontSize: '1rem',
                    fontWeight: '600',
                    textAlign: 'center'
                  }}>
                    Logos detectados:
                  </h5>
                  <div style={{
                    background: 'rgba(0, 0, 0, 0.3)', 
                    padding: '0.75rem', 
                    borderRadius: '10px',
                    border: '1px solid rgba(255, 255, 255, 0.1)'
                  }}>
                    {Object.entries(summary.labelCounts).map(([label, count], index) => (
                      <div key={index} style={{
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        padding: '0.5rem 0.75rem',
                        margin: '0.25rem 0',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: '8px',
                        border: '1px solid rgba(255, 255, 255, 0.1)'
                      }}>
                        <span style={{color: 'var(--white)', fontWeight: '500'}}>{label}</span>
                        <span style={{
                          color: '#FFD54F', 
                          fontWeight: 'bold',
                          background: 'rgba(255, 213, 79, 0.2)',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '12px',
                          fontSize: '0.9rem'
                        }}>
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{
                  textAlign: 'center',
                  padding: '1rem',
                  background: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: '10px',
                  border: '1px solid rgba(255, 255, 255, 0.1)'
                }}>
                  <div style={{
                    color: '#90A4AE',
                    fontSize: '0.9rem',
                    fontStyle: 'italic'
                  }}>
                    No se detectaron logos en este frame
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {data && data.image_url && (
        <div className="preview">
          <div style={{display: 'flex', flexDirection: 'row', gap: '20px', flexWrap: 'wrap'}}>
            {data.original_jpg_base64 && (
              <div style={{flex: '1', minWidth: '300px'}}>
                <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>Imagen Original</h4>
                <img 
                  src={`data:image/jpeg;base64,${data.original_jpg_base64}`} 
                  alt="Imagen Original" 
                  style={{maxWidth: '100%', height: 'auto', borderRadius: '10px'}}
                />
              </div>
            )}
            <div style={{flex: '1', minWidth: '300px'}}>
              <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>Imagen Procesada</h4>
              <canvas ref={canvasRef} style={{maxWidth: '100%', height: 'auto', borderRadius: '10px'}}></canvas>
            </div>
          </div>
        </div>
      )}

      {data && (data.video_url || processingVideoUrl) && (
        <div className="preview">
          <video 
            ref={videoRef} 
            controls 
            src={data.video_url || processingVideoUrl} 
            style={{maxWidth:'100%', borderRadius: '10px'}}
          />
          <div style={{marginTop: '1.5rem'}}>
            <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>⏱️ Timestamps con logos detectados:</h4>
            <div style={{background: 'var(--gray-dark)', padding: '1rem', borderRadius: '10px'}}>
              {(data.detections||[]).map((det, i) => (
                <div key={i} style={{padding: '0.5rem 0', borderBottom: i < summary?.frames.length - 1 ? '1px solid var(--gray)' : 'none'}}>
                  <strong style={{color: 'var(--white)'}}>{det.timestamp}s</strong> - 
                  {det.label || det.class}: {Math.round(det.score*100)}%
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {!data && isLiveProcessing && processingVideoUrl && (
        <div className="preview">
          <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>Video en procesamiento:</h4>
          <video 
            ref={videoRef} 
            controls 
            autoPlay 
            src={processingVideoUrl} 
            style={{maxWidth:'100%', borderRadius: '10px'}}
          />
          <div style={{marginTop: '0.5rem', color: 'var(--white)', fontSize: '0.9rem'}}>
            El video se está procesando. Las detecciones se mostrarán cuando se complete el procesamiento.
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
