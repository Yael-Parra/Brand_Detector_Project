import React, { useState } from 'react'
import ImageUploader from '../components/ImageUploader'
import VideoUploader from '../components/VideoUploader'
import YoutubeInput from '../components/YoutubeInput'
import ResultViewer from '../components/ResultViewer'

export default function AppPage({data, setData, setJobId, jobId}){
  const [activeOption, setActiveOption] = useState(0)
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [hasFile, setHasFile] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [showResults, setShowResults] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const options = [
    { id: 0, title: 'Imagen', component: ImageUploader },
    { id: 1, title: 'Video', component: VideoUploader },
    { id: 2, title: 'YouTube', component: YoutubeInput }
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

    setLoading(true)
    
    try {
      if (activeOption === 2) { 
        // Procesar video de YouTube
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
        
        // Crear un objeto de datos con la información recibida
        const sample = {
          video_url: youtubeUrl,
          detections: result.detections || [],
          total_video_time_segs: result.total_video_time_segs || 0
        }
        
        setJobId(`youtube-job-${Date.now()}`)
        setData(sample)
        setShowResults(true)
      } else if (activeOption === 1) { // Video MP4
        if (!selectedFile) {
          throw new Error('No se ha seleccionado ningún archivo de video')
        }
        
        // Crear un FormData para enviar el archivo
        const formData = new FormData()
        formData.append('file', selectedFile)
        
        // Enviar el archivo al backend
        const response = await fetch('http://localhost:8000/predict/mp4', {
          method: 'POST',
          body: formData
        })
        
        if (!response.ok) {
          throw new Error(`Error al procesar el video: ${response.statusText}`)
        }
        
        const result = await response.json()
        
        // Crear un objeto de datos con la información recibida
        const sample = {
          video_file: selectedFile.name,
          detections: result.detections || []
        }
        
        setJobId(result.job_id || `video-job-${Date.now()}`)
        setData(sample)
        setShowResults(true)
      } else { // Imagen
        if (!selectedFile) {
          throw new Error('No se ha seleccionado ninguna imagen')
        }
        
        // Crear un FormData para enviar el archivo
        const formData = new FormData()
        formData.append('file', selectedFile)
        
        // Enviar el archivo al backend
        const response = await fetch('http://localhost:8000/process/image', {
          method: 'POST',
          body: formData
        })
        
        if (!response.ok) {
          throw new Error(`Error al procesar la imagen: ${response.statusText}`)
        }
        
        const result = await response.json()
        
        // Crear un objeto de datos con la información recibida
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
          </div>          {/* Active Component */}
          <div className="active-uploader">
            <ActiveComponent 
              onResult={(r, id) => {
                setHasFile(true)
                setSelectedFile(r) // Guardar el archivo seleccionado
                setShowResults(false) 
                setErrorMessage('')
              }}
              onUrlChange={activeOption === 2 ? (url) => {
                setYoutubeUrl(url)
                setHasFile(!!url.trim())
                setShowResults(false)
                setErrorMessage('')
              } : undefined}
            />
          </div>          {/*Button */}
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
