import React, { useEffect, useRef, useState } from 'react'

export default function ResultViewer({data: initialData, jobId}){
  const canvasRef = useRef()
  const videoRef = useRef()
  const [data, setData] = useState(initialData)
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
          if (statusData.detections) {
            // Verificar si detections es un número o un array
            if (typeof statusData.detections === 'number') {
              // Formato antiguo: detections es un número
              const labelCounts = statusData.labels || {}
              
              setSummary(prev => ({
                ...prev,
                totalDetections: statusData.detections,
                processingProgress: statusData.progress || 0,
                labelCounts: labelCounts // Añadir conteo de etiquetas
              }))
              
              // Si el procesamiento está completo, actualizar los datos
              if ((statusData.progress || 0) >= 100 && !data) {
                setData({
                  detections: statusData.detections_list || [],
                  video_url: processingVideoUrl // Usar la URL del video que ya tenemos
                })
              }
            } else if (Array.isArray(statusData.detections)) {
              // Formato nuevo: detections es un array de objetos con detecciones
              // Calcular el conteo de etiquetas a partir del array de detecciones
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
                detectionsList: statusData.detections // Guardar la lista de detecciones
              }))
              
              // Si el procesamiento está completo, actualizar los datos
              if ((statusData.progress || 0) >= 100 && !data) {
                setData({
                  detections: statusData.detections,
                  video_url: processingVideoUrl // Usar la URL del video que ya tenemos
                })
              }
            }
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
            
            // Actualizar los datos con el resultado final si no existen
            if (!data) {
              console.log('Obteniendo URL del video procesado con force_processed=true')
              // Obtener la URL del video procesado con un nuevo timestamp para evitar caché
              fetch(`http://localhost:8000/video/${id}?force_processed=true`)
                .then(response => response.ok ? response.json() : null)
                .then(videoData => {
                  if (videoData && videoData.video_url) {
                    // Añadir timestamp para forzar recarga del video procesado
                    const videoUrlWithTimestamp = `${videoData.video_url}?t=${new Date().getTime()}`
                    console.log('URL del video procesado con timestamp:', videoUrlWithTimestamp)
                    console.log('Información completa del video procesado:', videoData)
                    
                    // Verificar si es realmente el video procesado
                    if (videoData.video_info && videoData.video_info.is_processed) {
                      console.log('✅ Confirmado: Es el video procesado')
                    } else if (videoData.video_info && videoData.video_info.is_original) {
                      console.warn('⚠️ Advertencia: Se está usando el video original como fallback')
                    }
                    
                    // Convertir la URL a blob para mejorar la compatibilidad
                    console.log('Convirtiendo URL a blob para mejorar compatibilidad:', videoUrlWithTimestamp)
                    fetch(`http://localhost:8000${videoUrlWithTimestamp}`)
                      .then(response => response.blob())
                      .then(blob => {
                        const blobUrl = URL.createObjectURL(blob)
                        console.log('URL de blob creada:', blobUrl)
                        
                        setData({
                          detections: Array.isArray(statusData.detections) ? statusData.detections : statusData.detections_list || [],
                          video_url: blobUrl,
                          video_info: videoData.video_info // Guardar la información del video
                        })
                      })
                      .catch(error => {
                        console.error('Error al convertir a blob:', error)
                        // Fallback a URL directa si falla la conversión a blob
                        setData({
                          detections: Array.isArray(statusData.detections) ? statusData.detections : statusData.detections_list || [],
                          video_url: videoUrlWithTimestamp,
                          video_info: videoData.video_info
                        })
                      })
                  } else {
                    // Fallback al video que ya tenemos si no podemos obtener uno nuevo
                    console.warn('No se pudo obtener la URL del video procesado, usando fallback')
                    setData({
                      detections: Array.isArray(statusData.detections) ? statusData.detections : statusData.detections_list || [],
                      video_url: processingVideoUrl
                    })
                  }
                })
                .catch(error => {
                  console.error('Error al obtener URL del video procesado:', error)
                  // Usar la URL que ya tenemos como fallback
                  setData({
                    detections: Array.isArray(statusData.detections) ? statusData.detections : statusData.detections_list || [],
                    video_url: processingVideoUrl
                  })
                })
            }
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

  // Estado para almacenar la URL del video durante el procesamiento
  const [processingVideoUrl, setProcessingVideoUrl] = useState(null)

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
        
        // Solicitar la URL del video para reproducción durante el procesamiento
        fetch(`http://localhost:8000/video/${jobId}?force_original=true`)
          .then(response => {
            if (response.ok) {
              return response.json()
            }
            throw new Error('No se pudo obtener la URL del video')
          })
          .then(data => {
            if (data.video_url) {
              console.log('URL de video obtenida para reproducción durante procesamiento:', data.video_url)
              // Añadir un parámetro de timestamp para evitar caché del navegador
              const videoUrlWithTimestamp = `${data.video_url}?t=${new Date().getTime()}`
              console.log('URL con timestamp para evitar caché:', videoUrlWithTimestamp)
              
              // Convertir la URL a blob para mejorar la compatibilidad
              console.log('Convirtiendo URL a blob para mejorar compatibilidad:', videoUrlWithTimestamp)
              fetch(`http://localhost:8000${videoUrlWithTimestamp}`)
                .then(response => response.blob())
                .then(blob => {
                  const blobUrl = URL.createObjectURL(blob)
                  console.log('URL de blob creada para video original:', blobUrl)
                  setProcessingVideoUrl(blobUrl)
                })
                .catch(error => {
                  console.error('Error al convertir a blob:', error)
                  // Fallback a URL directa si falla la conversión a blob
                  setProcessingVideoUrl(videoUrlWithTimestamp)
                })
            }
          })
          .catch(error => {
            console.error('Error al obtener URL del video:', error)
          })
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
    // Usar el campo label en lugar de class para las detecciones
    // Filtrar solo las detecciones con confianza > 75%
    const filteredDetections = (d.detections || []).filter(detection => {
      const score = detection.score ? detection.score * 100 : 0;
      return score > 75;
    });
    
    const totalDetections = filteredDetections.length;
    const frames = filteredDetections;
    
    // Crear un objeto para contar las etiquetas detectadas
    const labelCounts = {}
    if (filteredDetections && Array.isArray(filteredDetections)) {
      filteredDetections.forEach(detection => {
        if (detection.label) {
          labelCounts[detection.label] = (labelCounts[detection.label] || 0) + 1
        } else if (detection.class) {
          // Mantener compatibilidad con el formato anterior
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
      
      // Filtrar solo las detecciones con confianza > 75%
      const filteredDetections = detections.filter(box => {
        const score = box.score ? box.score * 100 : 0;
        return score > 75;
      });
      
      filteredDetections.forEach(box=>{
        // Verificar si tenemos bbox_xyxy (formato nuevo) o bbox (formato antiguo)
        let x, y, w, h;
        if (box.bbox_xyxy) {
          // Formato nuevo: [x1, y1, x2, y2]
          const [x1, y1, x2, y2] = box.bbox_xyxy;
          x = x1;
          y = y1;
          w = x2 - x1;
          h = y2 - y1;
        } else if (box.bbox) {
          // Formato antiguo: [x, y, w, h]
          [x, y, w, h] = box.bbox;
        } else {
          // No hay información de bounding box
          return;
        }
        
        ctx.strokeRect(x, y, w, h)
        ctx.fillStyle = 'rgba(255, 255, 255, 0.8)'
        ctx.fillRect(x, y-30, 160, 30)
        ctx.fillStyle = '#000000'
        
        // Usar label si está disponible, sino usar class
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
              
              {/* Mostrar etiquetas detectadas en tiempo real */}
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
          )}
        </div>
      )}

      {data && data.image_url && (
        <div className="preview">
          {/* Mostrar la imagen original y la imagen procesada lado a lado */}
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
              <div style={{width: '100%', overflow: 'auto', maxHeight: '100vh'}}>
                <canvas ref={canvasRef} style={{maxWidth: 'none', width: 'auto', height: 'auto', borderRadius: '10px'}}></canvas>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* El video procesado se mostrará después del resumen */}
      
      {/* Durante el procesamiento, solo mostrar la caja de estado */}
      {/* El video procesado se mostrará solo cuando el procesamiento esté completo */}

      {summary && (
        <div style={{marginTop: '2rem', padding: '1.5rem', background: 'var(--gray-dark)', borderRadius: '15px'}}>
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
      
      {/* Mostrar video procesado después del resumen cuando el procesamiento está completo */}
      {data && (data.video_url || processingVideoUrl) && processingStatus === 'Procesamiento completado' && (
        <div className="preview" style={{marginTop: '2rem'}}>
          <h4 style={{color: 'var(--white)', marginBottom: '1rem'}}>Video Procesado</h4>
          
          {/* Información de diagnóstico del video */}
          <div style={{background: 'rgba(0,0,0,0.2)', padding: '0.5rem', borderRadius: '5px', marginBottom: '1rem', fontSize: '0.8rem'}}>
            <div><strong>URL del video:</strong> {data.video_url || processingVideoUrl}</div>
            <div><strong>Tipo:</strong> {data.video_url ? 'Procesado final' : 'Durante procesamiento'}</div>
            {data.video_info && (
              <>
                <div><strong>Ruta:</strong> {data.video_info.path}</div>
                <div><strong>Tamaño:</strong> {(data.video_info.size / 1024 / 1024).toFixed(2)} MB</div>
                <div><strong>Tipo de video:</strong> {data.video_info.type}</div>
                <div><strong>Es procesado:</strong> {data.video_info.is_processed ? 'Sí' : 'No'}</div>
                <div><strong>Es original:</strong> {data.video_info.is_original ? 'Sí' : 'No'}</div>
                <div><strong>Estado del trabajo:</strong> {data.video_info.job_status}</div>
              </>
            )}
            <div style={{display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap'}}>
              <button 
                onClick={() => {
                  const videoElement = videoRef.current;
                  if (videoElement) {
                    videoElement.load();
                    videoElement.play();
                    console.log('Video recargado manualmente');
                  }
                }}
                style={{background: '#444', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer'}}
              >
                Recargar video
              </button>
              <button 
                onClick={() => {
                  // Mostrar información detallada en la consola
                  console.log('=== DIAGNÓSTICO DETALLADO DEL VIDEO ===');
                  console.log('URL actual:', data.video_url || processingVideoUrl);
                  console.log('Información del video:', data.video_info);
                  console.log('Es blob URL:', (data.video_url || processingVideoUrl).startsWith('blob:'));
                  console.log('JobID:', jobId);
                  console.log('Estado de procesamiento:', processingStatus);
                  
                  // Verificar si hay caché del navegador para esta URL
                  const videoElement = videoRef.current;
                  if (videoElement) {
                    console.log('Estado del elemento video:');
                    console.log('- readyState:', videoElement.readyState);
                    console.log('- networkState:', videoElement.networkState);
                    console.log('- currentSrc:', videoElement.currentSrc);
                    console.log('- error:', videoElement.error);
                  }
                  
                  alert('Información de diagnóstico enviada a la consola del navegador (F12)');
                }}
                style={{background: '#17a2b8', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer'}}
              >
                Diagnóstico consola
              </button>
              <button 
                onClick={() => {
                  // Crear un nuevo elemento video con una URL única para evitar caché
                  const videoElement = videoRef.current;
                  if (videoElement && (data.video_url || processingVideoUrl)) {
                    const timestamp = new Date().getTime();
                    const newUrl = `${data.video_url || processingVideoUrl}?nocache=${timestamp}`;
                    console.log('Limpiando caché del video con nueva URL:', newUrl);
                    
                    // Actualizar la URL del video con un parámetro único
                    videoElement.src = newUrl;
                    videoElement.load();
                    videoElement.play();
                    
                    // Actualizar los datos para que la UI refleje la nueva URL
                    if (data.video_url) {
                      setData(prevData => ({
                        ...prevData,
                        video_url: newUrl
                      }));
                    } else {
                      setProcessingVideoUrl(newUrl);
                    }
                  }
                }}
                style={{background: '#6c757d', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer'}}
              >
                Limpiar caché
              </button>
              <button 
                onClick={() => {
                  if (jobId) {
                    console.log('Verificando estado detallado del video');
                    // Asegurarse de usar la URL correcta para la API
                    const apiUrl = `/status/${jobId}?include_video_info=true`;
                    console.log('Consultando API:', apiUrl);
                    fetch(apiUrl)
                      .then(response => response.json())
                      .then(data => {
                        console.log('Información detallada del video:', data);
                        alert(`Información del trabajo:\n\n` +
                              `- Estado: ${data.status}\n` +
                              `- Progreso: ${data.progress}%\n` +
                              `- Detecciones: ${data.detections || 0}\n` +
                              `- Archivo: ${data.file_name}\n\n` +
                              `Información completa en la consola.`);
                      })
                      .catch(error => {
                        console.error('Error al verificar estado:', error);
                        alert('Error al verificar el estado del video');
                      });
                  } else {
                    alert('No hay un trabajo activo para verificar');
                  }
                }}
                style={{background: '#28a745', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer', marginRight: '0.5rem'}}
              >
                Verificar estado
              </button>
              <button 
                onClick={() => {
                  if (jobId) {
                    console.log('Verificando archivos de video en el servidor');
                    fetch(`/api/status/${jobId}?include_video_info=true`)
                      .then(response => response.json())
                      .then(data => {
                        console.log('Información de archivos de video:', data.video_files_info);
                        
                        // Formatear la información de los archivos
                        let originalInfo = 'No disponible';
                        let processedInfo = 'No disponible';
                        
                        if (data.video_files_info && data.video_files_info.original) {
                          const original = data.video_files_info.original;
                          originalInfo = `Existe: ${original.exists ? 'SÍ' : 'NO'}\n` +
                                         `Tamaño: ${original.size} bytes\n` +
                                         `Ruta: ${original.path}\n` +
                                         `Modificado: ${original.last_modified}`;
                        }
                        
                        if (data.video_files_info && data.video_files_info.processed) {
                          const processed = data.video_files_info.processed;
                          processedInfo = `Existe: ${processed.exists ? 'SÍ' : 'NO'}\n` +
                                          `Tamaño: ${processed.size} bytes\n` +
                                          `Ruta: ${processed.path}\n` +
                                          `Modificado: ${processed.last_modified}`;
                        }
                        
                        alert(`INFORMACIÓN DE ARCHIVOS DE VIDEO\n\n` +
                              `VIDEO ORIGINAL:\n${originalInfo}\n\n` +
                              `VIDEO PROCESADO:\n${processedInfo}`);
                      })
                      .catch(error => {
                        console.error('Error al verificar archivos:', error);
                        alert('Error al verificar los archivos de video');
                      });
                  } else {
                    alert('No hay un trabajo activo para verificar');
                  }
                }}
                style={{background: '#17a2b8', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer'}}
              >
                Verificar archivos
              </button>
              <button 
                onClick={() => {
                  if (jobId) {
                    console.log('Forzando video procesado');
                    fetch(`http://localhost:8000/video/${jobId}?force_processed=true`)
                      .then(response => response.ok ? response.json() : null)
                      .then(videoData => {
                        if (videoData && videoData.video_url) {
                          const videoUrlWithTimestamp = `${videoData.video_url}?t=${new Date().getTime()}`;
                          console.log('URL del video procesado forzado:', videoUrlWithTimestamp);
                          console.log('Información del video:', videoData.video_info);
                          
                          // Obtener la duración del video cuando esté disponible
                          const getDuration = (videoElement) => {
                            if (videoElement && videoElement.duration) {
                              const duration = videoElement.duration;
                              const minutes = Math.floor(duration / 60);
                              const seconds = Math.floor(duration % 60);
                              return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
                            }
                            return 'Desconocida';
                          };
                          
                          // Convertir la URL a blob para mejorar la compatibilidad
                          console.log('Convirtiendo URL a blob para mejorar compatibilidad:', videoUrlWithTimestamp);
                          fetch(`http://localhost:8000${videoUrlWithTimestamp}`)
                            .then(response => response.blob())
                            .then(blob => {
                              const blobUrl = URL.createObjectURL(blob);
                              console.log('URL de blob creada para video procesado:', blobUrl);
                              
                              // Actualizar el video y la información de diagnóstico
                              const videoElement = videoRef.current;
                              if (videoElement) {
                                videoElement.src = blobUrl;
                                videoElement.load();
                                videoElement.play();
                                
                                // Actualizar la duración cuando el video esté cargado
                                videoElement.onloadedmetadata = () => {
                                  const videoDuration = getDuration(videoElement);
                                  console.log('Duración del video procesado:', videoDuration);
                                  
                                  // Actualizar los datos con la nueva información y mantener las métricas
                                  setData(prevData => ({
                                    ...prevData,
                                    video_url: blobUrl,
                                    video_info: {
                                      ...videoData.video_info,
                                      duration: videoDuration
                                    },
                                    is_processed_video: true
                                  }));
                                };
                              } else {
                                // Actualizar los datos con la nueva información y mantener las métricas
                                setData(prevData => ({
                                  ...prevData,
                                  video_url: blobUrl,
                                  video_info: {
                                    ...videoData.video_info,
                                    duration: videoDuration,
                                    codec: videoData.video_info?.codec || 'Desconocido',
                                    size: videoData.video_info?.size || 0,
                                    width: videoElement.videoWidth,
                                    height: videoElement.videoHeight
                                  },
                                  is_processed_video: true
                                }));
                              }
                            })
                            .catch(error => {
                              console.error('Error al convertir a blob:', error);
                              // Fallback a URL directa si falla la conversión a blob
                              const videoElement = videoRef.current;
                              if (videoElement) {
                                videoElement.src = `http://localhost:8000${videoUrlWithTimestamp}`;
                                videoElement.load();
                                videoElement.play();
                                
                                // Actualizar la duración cuando el video esté cargado
                                videoElement.onloadedmetadata = () => {
                                  const videoDuration = getDuration(videoElement);
                                  console.log('Duración del video procesado:', videoDuration);
                                  
                                  // Actualizar los datos con la URL directa y mantener las métricas
                                  setData(prevData => ({
                                    ...prevData,
                                    video_url: `http://localhost:8000${videoUrlWithTimestamp}`,
                                    video_info: {
                                      ...videoData.video_info,
                                      duration: videoDuration
                                    },
                                    is_processed_video: true
                                  }));
                                };
                              } else {
                                // Actualizar los datos con la URL directa y mantener las métricas
                                setData(prevData => ({
                                  ...prevData,
                                  video_url: `http://localhost:8000${videoUrlWithTimestamp}`,
                                  video_info: videoData.video_info,
                                  is_processed_video: true
                                }));
                              }
                            });
                        }
                      })
                      .catch(error => console.error('Error al forzar video procesado:', error));
                  }
                }}
                style={{background: '#007bff', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer'}}
              >
                Forzar video procesado
              </button>
              <button 
                onClick={() => {
                  if (jobId) {
                    console.log('Forzando video original');
                    fetch(`http://localhost:8000/video/${jobId}?force_original=true`)
                      .then(response => response.ok ? response.json() : null)
                      .then(videoData => {
                        if (videoData && videoData.video_url) {
                          const videoUrlWithTimestamp = `${videoData.video_url}?t=${new Date().getTime()}`;
                          console.log('URL del video original forzado:', videoUrlWithTimestamp);
                          console.log('Información del video:', videoData.video_info);
                          
                          // Obtener la duración del video cuando esté disponible
                          const getDuration = (videoElement) => {
                            if (videoElement && videoElement.duration) {
                              const duration = videoElement.duration;
                              const minutes = Math.floor(duration / 60);
                              const seconds = Math.floor(duration % 60);
                              return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
                            }
                            return 'Desconocida';
                          };
                          
                          // Convertir la URL a blob para mejorar la compatibilidad
                          console.log('Convirtiendo URL a blob para mejorar compatibilidad:', videoUrlWithTimestamp);
                          fetch(`http://localhost:8000${videoUrlWithTimestamp}`)
                            .then(response => response.blob())
                            .then(blob => {
                              const blobUrl = URL.createObjectURL(blob);
                              console.log('URL de blob creada para video original:', blobUrl);
                              
                              // Actualizar el video y la información de diagnóstico
                              const videoElement = videoRef.current;
                              if (videoElement) {
                                videoElement.src = blobUrl;
                                videoElement.load();
                                videoElement.play();
                                
                                // Actualizar la duración cuando el video esté cargado
                                videoElement.onloadedmetadata = () => {
                                  const videoDuration = getDuration(videoElement);
                                  console.log('Duración del video original:', videoDuration);
                                  
                                  // Actualizar los datos con la nueva información y mantener las métricas
                                  setData(prevData => ({
                                    ...prevData,
                                    video_url: blobUrl,
                                    video_info: {
                                      ...videoData.video_info,
                                      duration: videoDuration,
                                      codec: videoData.video_info?.codec || 'Desconocido',
                                      size: videoData.video_info?.size || 0,
                                      width: videoElement.videoWidth,
                                      height: videoElement.videoHeight
                                    },
                                    is_processed_video: false
                                  }));
                                };
                              } else {
                                // Actualizar los datos con la nueva información y mantener las métricas
                                setData(prevData => ({
                                  ...prevData,
                                  video_url: blobUrl,
                                  video_info: videoData.video_info,
                                  is_processed_video: false
                                }));
                              }
                            })
                            .catch(error => {
                              console.error('Error al convertir a blob:', error);
                              // Fallback a URL directa si falla la conversión a blob
                              const videoElement = videoRef.current;
                              if (videoElement) {
                                videoElement.src = videoUrlWithTimestamp;
                                videoElement.load();
                                videoElement.play();
                              }
                              
                              setData(prevData => ({
                                ...prevData,
                                video_url: videoUrlWithTimestamp,
                                video_info: videoData.video_info
                              }));
                            });
                        }
                      })
                      .catch(error => console.error('Error al forzar video original:', error));
                  }
                }}
                style={{background: '#dc3545', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer'}}
              >
                Forzar video original
              </button>
            </div>
          </div>
          
          <video 
            ref={videoRef} 
            controls 
            key={`video-${new Date().getTime()}`} /* Añadir key con timestamp para forzar recreación del elemento */
            src={data.video_url || processingVideoUrl} 
            style={{maxWidth:'100%', borderRadius: '10px'}}
            onError={(e) => {
              console.error('Error al cargar el video:', e);
              alert('Error al cargar el video. Intente recargar o usar los botones de diagnóstico.');
            }}
            onLoadedData={() => {
              console.log('Video cargado correctamente:', data.video_url || processingVideoUrl);
              // Verificar si es un blob URL (video sin procesar)
              if ((data.video_url || processingVideoUrl).startsWith('blob:')) {
                console.warn('⚠️ ADVERTENCIA: Se está usando un blob URL, lo que indica que podría ser el video sin procesar');
              }
            }}
          />
          <div style={{marginTop: '1.5rem'}}>
            <div style={{marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#2a2a2a', borderRadius: '5px'}}>
              <h4 style={{margin: '0 0 0.5rem 0', color: 'var(--white)'}}>Información del video actual:</h4>
              
              {/* Mostrar información básica del video */}
              <div style={{marginBottom: '0.5rem', color: 'var(--white)', backgroundColor: '#3a3a3a', padding: '0.5rem', borderRadius: '5px'}}>
                <p style={{margin: '0 0 0.25rem 0'}}>
                  <strong>Tipo:</strong> {data.is_processed_video ? '🔄 Video Procesado' : '📹 Video Original'}
                </p>
                {data.video_info && (
                  <>
                    {data.video_info.duration && (
                      <p style={{margin: '0 0 0.25rem 0'}}>
                        <strong>Duración:</strong> {data.video_info.duration}
                      </p>
                    )}
                    {data.video_info.width && data.video_info.height && (
                      <p style={{margin: '0 0 0.25rem 0'}}>
                        <strong>Resolución:</strong> {data.video_info.width}x{data.video_info.height}
                      </p>
                    )}
                    {data.video_info.codec && (
                      <p style={{margin: '0 0 0.25rem 0'}}>
                        <strong>Codec:</strong> {data.video_info.codec}
                      </p>
                    )}
                    {data.video_info.size && (
                      <p style={{margin: '0 0 0.25rem 0'}}>
                        <strong>Tamaño:</strong> {(data.video_info.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    )}
                    <p style={{margin: '0 0 0.25rem 0'}}>
                      <strong>Detecciones:</strong> {summary?.totalDetections || 0}
                    </p>
                  </>
                )}
              </div>
              
              <button 
                onClick={() => {
                  const videoElement = videoRef.current;
                  if (videoElement) {
                    // Obtener información detallada del elemento video
                    const info = {
                      currentSrc: videoElement.currentSrc,
                      readyState: videoElement.readyState,
                      networkState: videoElement.networkState,
                      duration: videoElement.duration,
                      videoWidth: videoElement.videoWidth,
                      videoHeight: videoElement.videoHeight,
                      error: videoElement.error,
                      isBlob: videoElement.currentSrc.startsWith('blob:'),
                      isProcessed: videoElement.currentSrc.includes('force_processed=true'),
                      isOriginal: videoElement.currentSrc.includes('force_original=true'),
                    };
                    
                    console.log('=== INFORMACIÓN DEL ELEMENTO VIDEO ===', info);
                    
                    // Mostrar información en un alert formateado
                    const message = `Información del video:\n\n` +
                      `- URL: ${info.currentSrc}\n` +
                      `- Es blob: ${info.isBlob}\n` +
                      `- Forzado como: ${info.isProcessed ? 'PROCESADO' : info.isOriginal ? 'ORIGINAL' : 'NINGUNO'}\n` +
                      `- Estado: ${['HAVE_NOTHING', 'HAVE_METADATA', 'HAVE_CURRENT_DATA', 'HAVE_FUTURE_DATA', 'HAVE_ENOUGH_DATA'][info.readyState]}\n` +
                      `- Red: ${['EMPTY', 'IDLE', 'LOADING', 'NO_SOURCE'][info.networkState]}\n` +
                      `- Dimensiones: ${info.videoWidth}x${info.videoHeight}\n` +
                      `- Duración: ${info.duration ? info.duration.toFixed(2) + 's' : 'N/A'}\n` +
                      `- Error: ${info.error ? 'SÍ' : 'NO'}\n\n` +
                      `Información completa en la consola.`;
                    
                    alert(message);
                  }
                }}
                style={{background: '#28a745', border: 'none', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '3px', cursor: 'pointer', marginRight: '0.5rem'}}
              >
                Verificar video actual
              </button>
            </div>
            
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
    </div>
  )
}
