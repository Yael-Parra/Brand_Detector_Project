import React from 'react'
import { Link } from 'react-router-dom'

export default function Inicio(){
  return (
    <div className="page-container">
      <section className="hero-main">
        <div className="hero-content">
          <h1 className="main-title">LOGI<br/>FIND</h1>
          <div className="tech-badges">
            <span className="badge">ROBOFLOW</span>
            <span className="badge">NEON</span>
            <span className="badge">FASTAPI</span>
          </div>
        </div>
        <div className="hero-description">
          <p>Tecnología avanzada de detección de logotipos usando inteligencia artificial. Analiza imágenes, videos y contenido multimedia con precisión profesional.</p>
          <Link to="/app" className="button cta-button">Comenzar Análisis</Link>
        </div>
      </section>
    </div>
  )
}
