// ===============================================
// AppPage.jsx - Página principal del detector de logos
// ===============================================
// Maneja 4 tipos de análisis: Imagen, Video, YouTube y Streaming
import React, { useState } from 'react'
import ImageUploader from '../components/ImageUploader'
import VideoUploader from '../components/VideoUploader'
import YoutubeInput from '../components/YoutubeInput'
import StreamingCamera from '../components/StreamingCamera' 
import ResultViewer from '../components/ResultViewer'

export default function AppPage({data, setData, setJobId, jobId}){
  
  // ===============================================
  // ESTADOS DEL COMPONENTE
  // ===============================================
  const [activeOption, setActiveOption] = useState(0)      // Opción activa del carousel (0-3)
  const [youtubeUrl, setYoutubeUrl] = useState('')         // URL de YouTube
  const [loading, setLoading] = useState(false)            // Estado de carga
  const [hasFile, setHasFile] = useState(false)            // Si hay input listo
  const [selectedFile, setSelectedFile] = useState(null)   // Archivo seleccionado
  const [showResults, setShowResults] = useState(false)    // Mostrar resultados
  const [errorMessage, setErrorMessage] = useState('')     // Mensajes de error

  // ===============================================
  // CONFIGURACIÓN DEL CAROUSEL
  // ===============================================
  const options = [
    { id: 0, title: 'Imagen', component: ImageUploader },
    { id: 1, title: 'Video', component: VideoUploader },
    { id: 2, title: 'YouTube', component: YoutubeInput },
    { id: 3, title: 'Streaming', component: StreamingCamera }
  ]
  // ===============================================
  // FUNCIONES DE NAVEGACIÓN
  // ===============================================
  const nextOption = () => {
    setActiveOption((prev) => (prev + 1) % options.length)
  }
  
  const prevOption = () => {
    setActiveOption((prev) => (prev - 1 + options.length) % options.length)
  }
  
  // ===============================================
  // FUNCIÓN PRINCIPAL - PROCESAR SEGÚN TIPO
  // ===============================================
  const handleProcess = async () => {
    setErrorMessage('')
    
    // Validaciones previas según opción activa
    if (activeOption === 0 && !hasFile) {
      setErrorMessage('Por favor, selecciona una imagen primero')
      return
    }
    if (activeOption === 1 && !hasFile) {
      setErrorMessage('Por favor, selecciona un video primero')
      return
    }
    if (activeOption === 2 && !youtubeUrl.trim()) {
      setErrorMessage('Por favor, ingresa un enlace de YouTube primero')
      return
    }
    if (activeOption === 3 && !hasFile) {
      setErrorMessage('Por favor, enciende la cámara primero')
      return
    }

    setLoading(true)
    
    try {
      // ===============================================
      // PROCESAR SEGÚN TIPO DE OPCIÓN
      // ===============================================
      
      if (activeOption === 0) {
        // IMAGEN - Enviar al backend
        if (!selectedFile) {
          throw new Error('No se ha seleccionado ninguna imagen')
        }
        
        const formData = new FormData()
        formData.append('file', selectedFile)
        
        const response = await fetch('http://localhost:8000/process/image', {
          method: 'POST',
          body: formData
        })
        
        if (!response.ok) {
          throw new Error(`Error al procesar la imagen: ${response.statusText}`)
        }
        
        const result = await response.json()
        
        const sample = {
          image_url: URL.createObjectURL(selectedFile),
          detections: result.detections || [],
          annotated_jpg_base64: result.annotated_jpg_base64,
          original_jpg_base64: result.original_jpg_base64
        }
        
        setJobId(null)
        setData(sample)
        setShowResults(true)
        
      } else if (activeOption === 1) {
        // VIDEO - Enviar archivo al backend
        if (!selectedFile) {
          throw new Error('No se ha seleccionado ningún archivo de video')
        }
        
        const formData = new FormData()
        formData.append('file', selectedFile)
        
        const response = await fetch('http://localhost:8000/predict/mp4', {
          method: 'POST',
          body: formData
        })
        
        if (!response.ok) {
          throw new Error(`Error al procesar el video: ${response.statusText}`)
        }
        
        const result = await response.json()
        
        const sample = {
          video_file: selectedFile.name,
          video_url: URL.createObjectURL(selectedFile),
          detections: result.detections || []
        }
        
        setJobId(result.job_id || `video-job-${Date.now()}`)
        setData(sample)
        setShowResults(true)
        
      } else if (activeOption === 2) {
        // YOUTUBE - Enviar URL al backend
        const response = await fetch('http://localhost:8000/process/youtube', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ url: youtubeUrl })
        })
        
        if (!response.ok) {
          throw new Error(`Error al procesar el video: ${response.statusText}`)
        }
        
        const result = await response.json()
        
        if (result.error) {
          throw new Error(result.error)
        }
        
        const sample = {
          video_url: youtubeUrl,
          detections: result.detections || [],
          total_video_time_segs: result.total_video_time_segs || 0
        }
        
        setJobId(`youtube-job-${Date.now()}`)
        setData(sample)
        setShowResults(true)
        
      } else if (activeOption === 3) {
        // STREAMING - Iniciar análisis en tiempo real
        console.log('Iniciando streaming de detección...')
        
        // TODO: Conexión real con backend de streaming
        setTimeout(() => {
          const streamingData = {
            type: 'streaming',
            detections: [
              { class: 'logo-brand', score: 0.92, bbox: [100,60,80,80] }
            ],
            streaming_active: true
          }
          setJobId('streaming-' + Date.now())
          setData(streamingData)
          setShowResults(true)
        }, 1000)
      }
      
    } catch (error) {
      console.error('Error al procesar:', error)
      setErrorMessage(`Error: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }
  // ===============================================
  // MANEJADORES DE EVENTOS DE COMPONENTES HIJOS
  // ===============================================
  const handleComponentResult = (result, id) => {
    if (result === "camera-ready") {
      // Cámara lista para streaming
      setHasFile(true)
      setShowResults(false)
      setErrorMessage('')
    } else if (result === "camera-off") {
      // Cámara apagada
      setHasFile(false)
      setShowResults(false)
      setErrorMessage('')
    } else {
      // Archivo subido (imagen/video)
      setHasFile(true)
      setSelectedFile(result)
      setShowResults(false)
      setErrorMessage('')
    }
  }

  const handleUrlChange = (url) => {
    // Solo para YouTube - actualizar URL
    setYoutubeUrl(url)
    setHasFile(!!url.trim())
    setShowResults(false)
    setErrorMessage('')
  }

  // ===============================================
  // COMPONENTE DINÁMICO SEGÚN OPCIÓN ACTIVA
  // ===============================================
  const ActiveComponent = options[activeOption].component
  // ===============================================
  // RENDER DEL COMPONENTE
  // ===============================================
  return (
    <div className="page-container">
      {/* Header principal */}
      <section className="hero hero--about">
        <h1>Detector de Logos</h1>
        <p>Sube tu contenido y detecta logotipos de marcas reconocidas</p>
      </section>

      <div className="app-layout">
        {/* Sección del carousel y controles */}
        <div className="carousel-section">
          
          {/* Navegador de opciones */}
          <div className="carousel-container">
            <button className="carousel-btn prev" onClick={prevOption}>
              ‹
            </button>
            
            <div className="carousel-track">
              {options.map((option, index) => (
                <div 
                  key={option.id}
                  className={`carousel-item ${index === activeOption ? 'active' : ''}`}
                  onClick={() => setActiveOption(index)}
                >
                  <h3>{option.title}</h3>
                </div>
              ))}
            </div>

            <button className="carousel-btn next" onClick={nextOption}>
              ›
            </button>
          </div>

          {/* Componente activo según opción seleccionada */}
          <div className="active-uploader">
            <ActiveComponent 
              onResult={handleComponentResult}
              onUrlChange={activeOption === 2 ? handleUrlChange : undefined}
            />
          </div>

          {/* Botón de análisis y mensajes de error */}
          <div style={{
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            marginTop: '2rem', 
            marginBottom: '2rem'
          }}>
            <button 
              className="button analyze-button" 
              onClick={handleProcess}
              disabled={loading}
            >
              {loading ? 'Procesando...' : 'Analizar'}
            </button>
            
            {errorMessage && (
              <div style={{
                color: 'var(--white)', 
                fontSize: '0.9rem', 
                marginTop: '0.5rem',
                textAlign: 'center',
                opacity: '0.8'
              }}>
                {errorMessage}
              </div>
            )}
          </div>
        </div>

        {/* Sección de resultados */}
        {showResults && (
          <div className="results-section">
            <ResultViewer data={data} jobId={jobId} />
          </div>
        )}
      </div>
    </div>
  )
}
