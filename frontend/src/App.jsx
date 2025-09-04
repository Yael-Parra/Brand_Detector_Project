import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import CursorFollower from './components/CursorFollower'
import NotificationContainer from './components/NotificationContainer'
import ErrorBoundary from './components/ErrorBoundary'
import Inicio from './pages/Inicio'
import AppPage from './pages/AppPage'
import Nosotros from './pages/Nosotros'
import CamV2 from './components/CamV2'
import { AppProvider } from './contexts/AppContext'
import { NotificationProvider } from './contexts/NotificationContext'

export default function App(){
  const [menuOpen, setMenuOpen] = useState(false)

  const toggleMenu = () => setMenuOpen(!menuOpen)
  
  return (
    <NotificationProvider>
      <AppProvider>
        <Router>
          <ErrorBoundary>
            <div className="app">
              {/* Seguidor del cursor con logo 6.png */}
              <CursorFollower />
              {/* Contenedor de notificaciones */}
              <NotificationContainer />
      
      <header className="header">
        <div className="logo">
          <img src="/4.png" alt="LogiFind Logo" style={{height: '60px'}} />
        </div>
        
        <nav className={`nav ${menuOpen ? 'active' : ''}`}>
          <Link to="/" onClick={()=>setMenuOpen(false)} className="">Inicio</Link>
          <Link to="/app" onClick={()=>setMenuOpen(false)} className="">App</Link>
          <Link to="/cam-v2" onClick={()=>setMenuOpen(false)} className="">Cam V2</Link>
          <Link to="/nosotros" onClick={()=>setMenuOpen(false)} className="">Nosotros</Link>
        </nav>

        <div className={`hamburger ${menuOpen ? 'active' : ''}`} onClick={toggleMenu}>
          <span></span>
          <span></span>
          <span></span>
        </div>
      </header>

      <main className="main-content">
            <Routes>
              <Route path="/" element={<Inicio />} />
              <Route path="/app" element={<AppPage />} />
              <Route path="/cam-v2" element={<CamV2 />} />
              <Route path="/nosotros" element={<Nosotros />} />
            </Routes>
          </main>

          <footer className="footer">
            <p>Brand Detector • LogiFind © 2025 • Powered by AI</p>
          </footer>
            </div>
          </ErrorBoundary>
        </Router>
      </AppProvider>
    </NotificationProvider>
  )
}
