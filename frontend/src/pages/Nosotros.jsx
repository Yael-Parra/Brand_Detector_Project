import React from 'react'

export default function Nosotros(){
  return (
    <div className="page-container">      <section className="hero hero--about">
        <h1>Nosotros</h1>
        <p>Desarrollamos soluciones de IA para la detección automática de marcas y logotipos</p>
      </section>

      <div className="about-content">
        <div className="feature-card">
          <h3>Tecnología Avanzada</h3>
          <p>Utilizamos modelos YOLO de última generación para la detección precisa de logotipos y marcas comerciales.</p>
        </div>
        <div className="feature-card">
          <h3>Múltiples Formatos</h3>
          <p>Procesamos imágenes, videos locales y contenido de YouTube con la misma eficiencia y precisión.</p>
        </div>        <div className="feature-card">
          <h3>Análisis Detallado</h3>
          <p>Generamos reportes completos con timestamps, porcentajes y estadísticas detalladas de aparición.</p>
        </div>
      </div>      {/* Team Section */}
      <section className="team-section">
        <h2>Nuestro Equipo</h2>        <div className="team-grid">
          <div className="team-member">
            <div className="team-photo">
              <img src="https://media.licdn.com/dms/image/v2/D4E03AQHx7efz_Zemtw/profile-displayphoto-shrink_800_800/profile-displayphoto-shrink_800_800/0/1730202395873?e=1759363200&v=beta&t=x6uIOBjwpp3FdjPdhRm8GTwoABn0HLy39mqmxgSuABo" alt="Alla Haruntyunyan" />
            </div>
            <h3>Alla Haruntyunyan</h3>
            <p>Machine Learning Engineer</p>
            <a href="https://www.linkedin.com/in/allaharuty/" className="linkedin-icon" aria-label="LinkedIn de Alla Haruntyunyan">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
            </a>
          </div>          <div className="team-member">
            <div className="team-photo">
              <img src="https://media.licdn.com/dms/image/v2/D4D03AQETH6oSCpNIlw/profile-displayphoto-shrink_800_800/B4DZTmJf4DGcAc-/0/1739028037709?e=1759363200&v=beta&t=7383Ahumgfe7P1jxrOSyfZcl1cSPM90c-EgxNF_GagM" alt="Max Beltrán" />
            </div>
            <h3>Max Beltrán</h3>
            <p>Especialista en IA</p>
            <a href="https://www.linkedin.com/in/max-beltran/" className="linkedin-icon" aria-label="LinkedIn de Max Beltrán">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
            </a>
          </div>          <div className="team-member">
            <div className="team-photo">
              <img src="https://media.licdn.com/dms/image/v2/D4D03AQEuoD4ly_zB1Q/profile-displayphoto-shrink_800_800/B4DZUqi_4LHwAc-/0/1740175575379?e=1759363200&v=beta&t=G2PY74-gEGK73d23IPRbD6DIiKpR4WGvRnMEpoVrLh0" alt="Stephany Lizarraga" />
            </div>
            <h3>Stephany Lizarraga</h3>
            <p>Frontend Developer</p>
            <a href="https://www.linkedin.com/in/stephyangeles/" className="linkedin-icon" aria-label="LinkedIn de Stephany Lizarraga">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
            </a>
          </div>          <div className="team-member">
            <div className="team-photo">
              <img src="https://media.licdn.com/dms/image/v2/D4D03AQF0xDVaIh1DQw/profile-displayphoto-crop_800_800/B4DZgJyUldGsAQ-/0/1752510843587?e=1759363200&v=beta&t=jgijB8R0R4togGIHFxhjbRP0WQdf8K2SMjAPvPtUTGE" alt="Yael Parra" />
            </div>
            <h3>Yael Parra</h3>
            <p>Backend Developer</p>
            <a href="https://www.linkedin.com/in/yael-parra/" className="linkedin-icon" aria-label="LinkedIn de Yael Parra">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
            </a>
          </div>          <div className="team-member">
            <div className="team-photo">
              <img src="https://www.linkedin.com/in/orlando-alcala/overlay/photo/" alt="Orlando Alcalá" />
            </div>
            <h3>Orlando Alcalá</h3>
            <p>Data Scientist</p>
            <a href="https://www.linkedin.com/in/orlando-alcala/" className="linkedin-icon" aria-label="LinkedIn de Orlando Alcalá">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}
