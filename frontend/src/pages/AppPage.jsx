import React, { useState } from 'react'
import ImageUploader from '../components/ImageUploader'
import VideoUploader from '../components/VideoUploader'
import YoutubeInput from '../components/YoutubeInput'
import WebcamStream from '../components/WebcamStream'
import CamV2 from '../components/CamV2'
import ResultViewer from '../components/ResultViewer'
import ProcessingStatus from '../components/ProcessingStatus'
import AdvancedSettings from '../components/AdvancedSettings'
import { useApp } from '../contexts/AppContext'
import { useNotification } from '../contexts/NotificationContext'
import { useApi } from '../hooks/useApi'
import { useJobPolling } from '../hooks/useJobPolling'
import { useFileValidation } from '../hooks/useFileValidation'

export default function AppPage() {
  // ===========================
  // Contextos y hooks
  // ===========================
  const { state, actions } = useApp()
  const { actions: notificationActions } = useNotification()
  const { uploadFile, processYouTube, loading: apiLoading } = useApi()
  const { startPolling } = useJobPolling()
  const { validateFile, validateYouTubeUrl } = useFileValidation()

  // ===========================
  // Estados locales de la UI
  // ===========================
  const [hasFile, setHasFile] = useState(false)         // Indica si se seleccionó archivo
  const [showResults, setShowResults] = useState(false)// Mostrar resultados en UI
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false) // Mostrar configuración avanzada

  // ===========================
  // Opciones del carousel
  // ===========================
  const options = [
    { id: 0, title: 'Imagen', component: ImageUploader },
    { id: 1, title: 'Video', component: VideoUploader },
    { id: 2, title: 'YouTube', component: YoutubeInput },
    { id: 3, title: 'Webcam', component: WebcamStream },
    { id: 4, title: 'cam_v2', component: CamV2 }
  ]

  // Navegación carousel
  const nextOption = () => {
    const newOption = (state.activeOption + 1) % options.length
    actions.setActiveOption(newOption)
  }
  const prevOption = () => {
    const newOption = (state.activeOption - 1 + options.length) % options.length
    actions.setActiveOption(newOption)
  }

  // ===========================
  // Función principal de procesamiento
  // ===========================
  const handleProcess = async () => {
    actions.setError(null)

    // Validaciones mejoradas por tipo de input
    if (state.activeOption === 0) {
      if (!hasFile || !state.selectedFile) {
        notificationActions.showError('Por favor, selecciona una imagen primero')
        return
      }
      if (!validateFile(state.selectedFile, 'image')) {
        return
      }
    }
    if (state.activeOption === 1) {
      if (!hasFile || !state.selectedFile) {
        notificationActions.showError('Por favor, selecciona un video primero')
        return
      }
      if (!validateFile(state.selectedFile, 'video')) {
        return
      }
    }
    if (state.activeOption === 2) {
      if (!validateYouTubeUrl(state.youtubeUrl)) {
        return
      }
    }
    if (state.activeOption === 3) {
      // Webcam no requiere procesamiento tradicional - funciona en tiempo real
      notificationActions.showInfo('La webcam funciona en tiempo real. Usa los controles del componente.')
      return
    }
    if (state.activeOption === 4) {
      // cam_v2 no requiere procesamiento tradicional - funciona con endpoints directos
      notificationActions.showInfo('Cam V2 funciona con endpoints directos. Usa los controles del componente.')
      return
    }

    actions.setLoading(true)

    try {
      if (state.activeOption === 2) {
        // -----------------------
        // Procesamiento YouTube
        // -----------------------
        const { data: result, error } = await processYouTube(state.youtubeUrl)
        
        if (error) {
          actions.setError(error)
          return
        }

        // Guardamos la info inicial y job_id
        const sample = {
          video_url: state.youtubeUrl,
          detections: result.detections || [],
          total_video_time_segs: result.total_video_time_segs || 0
        }

        actions.setResults(sample)
        setShowResults(true)
        
        // Iniciar polling si hay job_id
        if (result.job_id) {
          startPolling(result.job_id)
        }

      } else if (state.activeOption === 1) {
        // -----------------------
        // Procesamiento Video local
        // -----------------------
        const { data: result, error } = await uploadFile(state.selectedFile, 'video')
        
        if (error) {
          actions.setError(error)
          return
        }

        const sample = {
          video_file: state.selectedFile.name,
          video_url: URL.createObjectURL(state.selectedFile),
          detections: result.detections || []
        }

        actions.setResults(sample)
        setShowResults(true)
        
        // Iniciar polling si hay job_id
        if (result.job_id) {
          startPolling(result.job_id)
        }

      } else {
        // -----------------------
        // Procesamiento Imagen
        // -----------------------
        const { data: result, error } = await uploadFile(state.selectedFile, 'image')
        
        if (error) {
          actions.setError(error)
          return
        }

        const sample = {
          image_url: URL.createObjectURL(state.selectedFile),
          detections: result.detections || [],
          annotated_jpg_base64: result.annotated_jpg_base64,
          original_jpg_base64: result.original_jpg_base64
        }

        actions.setResults(sample)
        setShowResults(true)
      }
    } catch (error) {
      console.error('Error al procesar:', error)
      actions.setError(error.message)
    } finally {
      actions.setLoading(false)
    }
  }

  // Componente activo según carousel
  const ActiveComponent = options[state.activeOption].component

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
          <div className="carousel-container">
            <button className="carousel-btn prev" onClick={prevOption}>‹</button>
            <div className="carousel-track">
              {options.map((option, index) => (
                <div 
                  key={option.id}
                  className={`carousel-item ${index === state.activeOption ? 'active' : ''}`}
                  onClick={() => actions.setActiveOption(index)}
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
                if (state.activeOption === 2) {
                  // YouTube: manejar URL
                  actions.setYoutubeUrl(r.url)
                  setHasFile(r.isValid && r.url.length > 0)
                } else {
                  // Imagen/Video: manejar archivo
                  setHasFile(true)
                  actions.setSelectedFile(r)
                }
                setShowResults(false)
                actions.setError(null)
              }}
              onUrlChange={state.activeOption === 2 ? (url) => {
                // Cuando se ingresa YouTube
                actions.setYoutubeUrl(url)
                setHasFile(url.length > 0 && url.match(/^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/) !== null)
                setShowResults(false)
                actions.setError(null)
              } : undefined}
            />
          </div>

          {/* =========================
              Botón Analizar y Error (No mostrar para Webcam)
          ========================= */}
          {state.activeOption !== 3 && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginTop: '2rem', marginBottom: '2rem' }}>
              {/* Botones de acción */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '300px' }}>
                {/* Botón de análisis */}
                <button 
                  className="button analyze-button" 
                  onClick={handleProcess}
                  disabled={state.loading || apiLoading}
                >
                  {(state.loading || apiLoading) ? 'Procesando...' : 'Analizar'}
                </button>
                
                {/* Botón de configuración avanzada */}
                <button
                  onClick={() => setShowAdvancedSettings(!showAdvancedSettings)}
                  style={{
                    width: '100%',
                    padding: '0.75rem 1.5rem',
                    fontSize: '0.95rem',
                    color: 'var(--white)',
                    backgroundColor: 'transparent',
                    border: '1px solid var(--gray-500)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    opacity: '0.8'
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = 'var(--gray-700)';
                    e.target.style.opacity = '1';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = 'transparent';
                    e.target.style.opacity = '0.8';
                  }}
                >
                  {showAdvancedSettings ? '🔧 Ocultar configuración' : '⚙️ Configuración avanzada'}
                </button>
              </div>
              
              {/* Estado del procesamiento */}
              <ProcessingStatus />
              
              {/* Configuración avanzada */}
              <AdvancedSettings 
                isVisible={showAdvancedSettings}
                onToggle={() => setShowAdvancedSettings(!showAdvancedSettings)}
              />
              
              {state.error && state.jobStatus !== 'error' && (
                <div style={{
                  color: 'var(--white)',
                  fontSize: '0.9rem',
                  marginTop: '0.5rem',
                  textAlign: 'center',
                  opacity: '0.8'
                }}>
                  {state.error}
                </div>
              )}
            </div>
          )}
        </div>

        {/* =========================
            Results Section
        ========================= */}
        {showResults && state.results && (
          <div className="results-section">
            <ResultViewer data={state.results} jobId={state.jobId} />
          </div>
        )}
      </div>
    </div>
  )
}
