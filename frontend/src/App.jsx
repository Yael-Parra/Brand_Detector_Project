import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import ImageUploader from './components/ImageUploader'
import VideoUploader from './components/VideoUploader'
import YoutubeInput from './components/YoutubeInput'
import ResultViewer from './components/ResultViewer'
import CursorFollower from './components/CursorFollower'
import Inicio from './pages/Inicio'
import AppPage from './pages/AppPage'
import Nosotros from './pages/Nosotros'

export default function App(){
  const [data, setData] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)

  const toggleMenu = () => setMenuOpen(!menuOpen)
  return (
    <Router>
    <div className="app">
      {/* Seguidor del cursor con logo 6.png */}
      <CursorFollower />
      
      <header className="header">
        <div className="logo">
          <img src="/4.png" alt="LogiFind Logo" style={{height: '60px'}} />
        </div>
        
        <nav className={`nav ${menuOpen ? 'active' : ''}`}>
          <Link to="/" onClick={()=>setMenuOpen(false)} className="">Inicio</Link>
          <Link to="/app" onClick={()=>setMenuOpen(false)} className="">App</Link>
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
          <Route path="/app" element={<AppPage data={data} setData={setData} setJobId={setJobId} jobId={jobId} />} />
          <Route path="/nosotros" element={<Nosotros />} />
        </Routes>
      </main>

      <footer className="footer">
        <p>Brand Detector • LogiFind © 2025 • Powered by AI</p>
      </footer>
    </div>
    </Router>
  )
}
