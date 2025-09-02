import React, { useState } from 'react'
import ImageUploader from '../components/ImageUploader'
import VideoUploader from '../components/VideoUploader'
import YoutubeInput from '../components/YoutubeInput'
import StreamingCamera from '../components/StreamingCamera' // Importar nuestro nuevo componente
import ResultViewer from '../components/ResultViewer'

export default function AppPage({data, setData, setJobId, jobId}){
  const [activeOption, setActiveOption] = useState(0)
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [hasFile, setHasFile] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  // Array de opciones disponibles en el carousel
  // Cada opción tiene un id, título y el componente que se renderiza
  const options = [
    { id: 0, title: 'Imagen', component: ImageUploader },
    { id: 1, title: 'Video', component: VideoUploader },
    { id: 2, title: 'YouTube', component: YoutubeInput },
    { id: 3, title: 'Streaming', component: StreamingCamera } // Nueva opción agregada
  ]

  const nextOption = () => {
    setActiveOption((prev) => (prev + 1) % options.length)
  }
  const prevOption = () => {
    setActiveOption((prev) => (prev - 1 + options.length) % options.length)
  }
  
  const handleProcess = async () => {
    setErrorMessage('')
    
    // Validaciones según la opción activa
    // Cada opción tiene sus propios requisitos antes de poder procesar
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
      // Para streaming, hasFile se pone en true cuando la cámara está encendida
      setErrorMessage('Por favor, enciende la cámara primero')
      return
    }    setLoading(true)
    
    // Procesar según el tipo de opción seleccionada
    try {
      if (activeOption === 2) { 
        // Opción YouTube - simulado por ahora
        setTimeout(() => {
          const sample = {
            video_url: youtubeUrl,
            detections: [
              { class: 'logo-brand', score: 0.81, bbox: [60,50,100,100], timestamp: 15 },
              { class: 'logo-brand', score: 0.75, bbox: [200,80,90,90], timestamp: 45 }
            ],
            total_video_time_segs: 120
          }
          setJobId('youtube-job-42')
          setData(sample)
          setShowResults(true)
          setLoading(false)
        }, 2000)
        
      } else if (activeOption === 3) {
        // Opción STREAMING - Aquí conectamos con el backend
        console.log('Iniciando streaming de detección...')
        
        // TODO: Aquí irá la conexión real con el backend
        // Por ahora simulamos datos de streaming
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
          setLoading(false)
        }, 1000)
        
      } else {
        // Opción Imagen y Video - simulado
        setTimeout(() => {
          const sample = {
            detections: [
              { class: 'logo-brand', score: 0.88, bbox: [80,40,120,120], timestamp: activeOption === 1 ? 3.2 : null }
            ]
          }
          setJobId(activeOption === 1 ? 'video-job-1' : null)
          setData(sample)
          setShowResults(true)
          setLoading(false)
        }, 2000)
      }
      
    } catch (error) {
      // Si algo sale mal, mostrar el error
      console.error('Error al procesar:', error)
      setErrorMessage(`Error: ${error.message}`)
      setLoading(false)
    }
  }

  const shouldShowButton = () => {
    return true // Siempre visible
  }

  const ActiveComponent = options[activeOption].component

  return (
    <div className="page-container">
      <section className="hero hero--about">
        <h1>Detector de Logos</h1>
        <p>Sube tu contenido y detecta logotipos de marcas reconocidas</p>
      </section>

      <div className="app-layout">
        {/* Carousel Section */}
        <div className="carousel-section">
          <div className="carousel-container">
            <button className="carousel-btn prev" onClick={prevOption}>
              ‹
            </button>
            
            <div className="carousel-track">
              {options.map((option, index) => (                <div 
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
          </div>          {/* Active Component - Aquí se renderiza el componente seleccionado */}
          <div className="active-uploader">
            <ActiveComponent 
              onResult={(r, id) => {
                // Esta función se ejecuta cuando el componente hijo notifica algo
                
                if (r === "camera-ready") {
                  // Caso especial: la cámara está lista para streaming
                  setHasFile(true) // Permitir que se active el botón Analizar
                  setShowResults(false) 
                  setErrorMessage('')
                } else if (r === "camera-off") {
                  // Caso especial: la cámara se apagó
                  setHasFile(false) // Deshabilitar el botón Analizar
                  setShowResults(false)
                  setErrorMessage('')
                } else {
                  // Casos normales: imagen o video subido
                  setHasFile(true)
                  setShowResults(false) 
                  setErrorMessage('')
                }
              }}
              onUrlChange={activeOption === 2 ? (url) => {
                // Solo para YouTube: actualizar URL
                setYoutubeUrl(url)
                setHasFile(!!url.trim())
                setShowResults(false)
                setErrorMessage('')
              } : undefined}
            />
          </div>{/*Button */}
          {shouldShowButton() && (
            <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '2rem', marginBottom: '2rem'}}>
              <button 
                className="button analyze-button" 
                onClick={handleProcess}
                disabled={loading}
              >
                {loading ? 'Procesando...' : 'Analizar'}
              </button>
              
              {/* Error Message */}
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
          )}
        </div>{/* Results Section */}
        {showResults && (
          <div className="results-section">
            <ResultViewer data={data} jobId={jobId} />
          </div>
        )}
      </div>
    </div>
  )
}
