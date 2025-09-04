import React, { useState, useEffect } from 'react'
import ImageUploader from '../components/ImageUploader'
import VideoUploader from '../components/VideoUploader'
import YoutubeInput from '../components/YoutubeInput'
import StreamingCamera from '../components/StreamingCamera' 
import ResultViewer from '../components/ResultViewer'

export default function AppPage({data, setData, setJobId, jobId}) {
  // ===========================
  // Estados de la UI
  // ===========================
  const [activeOption, setActiveOption] = useState(0)   // 0=Imagen, 1=Video, 2=YouTube
  const [youtubeUrl, setYoutubeUrl] = useState('')      // URL ingresada por el usuario
  const [loading, setLoading] = useState(false)         // Spinner de procesamiento
  const [hasFile, setHasFile] = useState(false)         // Indica si se seleccionó archivo
  const [selectedFile, setSelectedFile] = useState(null)// Archivo seleccionado
  const [showResults, setShowResults] = useState(false)// Mostrar resultados en UI
  const [errorMessage, setErrorMessage] = useState('')  // Mensajes de error

  // ===========================
  // Opciones del carousel
  // ===========================
  const options = [
    { id: 0, title: 'Imagen', component: ImageUploader },
    { id: 1, title: 'Video', component: VideoUploader },
    { id: 2, title: 'YouTube', component: YoutubeInput },
    { id: 3, title: 'Streaming', component: StreamingCamera }
  ]

  // Navegación carousel
  const nextOption = () => setActiveOption((prev) => (prev + 1) % options.length)
  const prevOption = () => setActiveOption((prev) => (prev - 1 + options.length) % options.length)

  // ===========================
  // Función principal de procesamiento
  // ===========================
  const handleProcess = async () => {
    setErrorMessage('')

    // Validaciones por tipo de input
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
      if (activeOption === 2) {
        // -----------------------
        // Procesamiento YouTube
        // -----------------------
        const response = await fetch('http://localhost:8000/process/youtube', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: youtubeUrl })
        })

        if (!response.ok) throw new Error(`Error al procesar el video: ${response.statusText}`)
        const result = await response.json()
        if (result.error) throw new Error(result.error)

        // Guardamos la info inicial y job_id
        const sample = {
          video_url: youtubeUrl,
          detections: result.detections || [],
          total_video_time_segs: result.total_video_time_segs || 0
        }

        setJobId(result.job_id || `youtube-job-${Date.now()}`)
        setData(sample)
        setShowResults(true)

        // ===========================
        // Polling para estado del job de YouTube
        // ===========================
        const interval = setInterval(async () => {
          try {
            const statusResp = await fetch(`http://localhost:8000/status/${result.job_id}`)
            const statusData = await statusResp.json()
            if (statusData.status === 'completed') {
              setData(prev => ({ ...prev, detections: statusData.detections || [] }))
              clearInterval(interval)
            } else if (statusData.status === 'error') {
              setErrorMessage(`Error procesando video: ${statusData.error}`)
              clearInterval(interval)
            }
          } catch (err) {
            console.error('Error polling YouTube job:', err)
            clearInterval(interval)
          }
        }, 3000) // cada 3s

      } else if (activeOption === 1) {
        // -----------------------
        // Procesamiento Video local
        // -----------------------
        if (!selectedFile) throw new Error('No se ha seleccionado ningún archivo de video')

        const formData = new FormData()
        formData.append('file', selectedFile)

        const response = await fetch('http://localhost:8000/predict/mp4', { method: 'POST', body: formData })
        if (!response.ok) throw new Error(`Error al procesar el video: ${response.statusText}`)
        const result = await response.json()

        const sample = {
          video_file: selectedFile.name,
          video_url: URL.createObjectURL(selectedFile),
          detections: result.detections || []
        }

        setJobId(result.job_id || `video-job-${Date.now()}`)
        setData(sample)
        setShowResults(true)

      } else {
        // -----------------------
        // Procesamiento Imagen
        // -----------------------
        if (!selectedFile) throw new Error('No se ha seleccionado ninguna imagen')

        const formData = new FormData()
        formData.append('file', selectedFile)

        const response = await fetch('http://localhost:8000/process/image', { method: 'POST', body: formData })
        if (!response.ok) throw new Error(`Error al procesar la imagen: ${response.statusText}`)
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
      }
    } catch (error) {
      console.error('Error al procesar:', error)
      setErrorMessage(`Error: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  // Componente activo según carousel
  const ActiveComponent = options[activeOption].component

  return (
    <div className="page-container">
      {/* =========================
          Hero / Header
      ========================= */}
      <section className="hero hero--about">
        <h1>Detector de Logos</h1>
        <p>Sube tu contenido y detecta logotipos de marcas reconocidas</p>
      </section>

      <div className="app-layout">
        {/* =========================
            Carousel Section
        ========================= */}
        <div className="carousel-section">
          
          {/* Navegador de opciones */}
          <div className="carousel-container">
            <button className="carousel-btn prev" onClick={prevOption}>‹</button>
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
            <button className="carousel-btn next" onClick={nextOption}>›</button>
          </div>

          {/* =========================
              Active Uploader Component
          ========================= */}
          <div className="active-uploader">
            <ActiveComponent 
              onResult={(r) => {
                // Cuando se selecciona archivo (Imagen o Video)
                setHasFile(true)
                setSelectedFile(r)
                setShowResults(false)
                setErrorMessage('')
              }}
              onUrlChange={activeOption === 2 ? (url) => {
                // Cuando se ingresa YouTube
                setYoutubeUrl(url)
                setShowResults(false)
                setErrorMessage('')
              } : undefined}
            />
          </div>

          {/* =========================
              Botón Analizar y Error
          ========================= */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '2rem', marginBottom: '2rem' }}>
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

        {/* =========================
            Results Section
        ========================= */}
        {showResults && (
          <div className="results-section">
            <ResultViewer data={data} jobId={jobId} />
          </div>
        )}
      </div>
    </div>
  )
}
