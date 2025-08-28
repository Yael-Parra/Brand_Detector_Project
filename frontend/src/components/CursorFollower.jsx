import React, { useEffect, useState } from 'react'

export default function CursorFollower() {
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    let timeoutId

    const handleMouseMove = (e) => {
      // Actualizar posición con un pequeño offset para que no tape el cursor
      setPosition({ 
        x: e.clientX + 20, 
        y: e.clientY + 20 
      })
      
      // Mostrar el logo seguidor
      if (!isVisible) {
        setIsVisible(true)
      }

      // Ocultar después de inactividad (3 segundos)
      clearTimeout(timeoutId)
      timeoutId = setTimeout(() => {
        setIsVisible(false)
      }, 3000)
    }

    const handleMouseLeave = () => {
      setIsVisible(false)
    }

    // Agregar event listeners
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseleave', handleMouseLeave)

    // Cleanup
    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseleave', handleMouseLeave)
      clearTimeout(timeoutId)
    }
  }, [isVisible])

  return (
    <div 
      className={`cursor-follower ${isVisible ? 'visible' : ''}`}
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
      }}
    >
      {/* seguidor */}
      <img 
        src="/6.png" 
        alt="LogiFind Cursor" 
        className="cursor-logo"
      />
    </div>
  )
}