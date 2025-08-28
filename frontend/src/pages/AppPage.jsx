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
    
    setTimeout(() => {
      let sample
      if (activeOption === 2) { 
        sample = {
          video_url: youtubeUrl,
          detections: [
            { class: 'logo-brand', score: 0.81, bbox: [60,50,100,100], timestamp: 15 },
            { class: 'logo-brand', score: 0.75, bbox: [200,80,90,90], timestamp: 45 }
          ],
          total_video_time_segs: 120
        }
        setJobId('youtube-job-42')
      } else {
        // Para imagen y video (simulado)
        sample = {
          detections: [
            { class: 'logo-brand', score: 0.88, bbox: [80,40,120,120], timestamp: activeOption === 1 ? 3.2 : null }
          ]
        }
        setJobId(activeOption === 1 ? 'video-job-1' : null)
      }
      
      setData(sample)
      setShowResults(true)
      setLoading(false)
    }, 2000)
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
