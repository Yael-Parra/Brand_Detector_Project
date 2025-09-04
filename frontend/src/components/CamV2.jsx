import { useEffect, useRef, useState, useCallback } from "react";
import { useNotification } from "../contexts/NotificationContext";

const CamV2 = () => {
  const wsRef = useRef(null);
  const mjpegRef = useRef(null);
  const canvasRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  
  const [isWSConnected, setIsWSConnected] = useState(false);
  const [isMJPEGActive, setIsMJPEGActive] = useState(false);
  const [wsDetections, setWsDetections] = useState([]);
  const [wsProcessedFrame, setWsProcessedFrame] = useState(null);
  const [cameraStatus, setCameraStatus] = useState(null);
  const [fps, setFps] = useState(5);
  const [wsStats, setWsStats] = useState({ framesSent: 0, framesReceived: 0 });
  
  const { actions } = useNotification();
  const { addNotification } = actions;

  // Verificar estado de la cámara
  const checkCameraStatus = useCallback(async () => {
    try {
      const response = await fetch('/webcam/status');
      const status = await response.json();
      setCameraStatus(status);
    } catch (error) {
      console.error('Error checking camera status:', error);
      addNotification('Error al verificar estado de la cámara', 'error');
    }
  }, [addNotification]);

  // Inicializar cámara local para WebSocket
  const initializeLocalCamera = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 30 }
        } 
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        addNotification('Cámara local inicializada para WebSocket', 'success');
      }
    } catch (error) {
      console.error('Error accessing local camera:', error);
      addNotification('Error al acceder a la cámara local: ' + error.message, 'error');
    }
  }, [addNotification]);

  // Conectar WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const ws = new WebSocket('ws://localhost:8000/webcam/ws');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsWSConnected(true);
      addNotification('WebSocket conectado', 'success');
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.error) {
          console.error('Server error:', data.error);
          addNotification('Error del servidor: ' + data.error, 'error');
          return;
        }
        
        if (data.frame) {
          setWsProcessedFrame('data:image/jpeg;base64,' + data.frame);
          setWsStats(prev => ({ ...prev, framesReceived: prev.framesReceived + 1 }));
        }
        
        if (data.detections) {
          setWsDetections(data.detections);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsWSConnected(false);
      addNotification('WebSocket desconectado', 'warning');
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      addNotification('Error de WebSocket', 'error');
    };
    
    wsRef.current = ws;
  }, [addNotification]);

  // Enviar frame via WebSocket
  const sendFrame = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }
    
    const canvas = canvasRef.current;
    const video = videoRef.current;
    
    if (!canvas || !video || video.videoWidth === 0) {
      return;
    }
    
    const ctx = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    try {
      const frame = canvas.toDataURL('image/jpeg', 0.8).split(',')[1];
      wsRef.current.send(frame);
      setWsStats(prev => ({ ...prev, framesSent: prev.framesSent + 1 }));
    } catch (error) {
      console.error('Error sending frame:', error);
    }
  }, []);

  // Iniciar WebSocket streaming
  const startWebSocketStreaming = useCallback(() => {
    if (!streamRef.current) {
      addNotification('Primero inicializa la cámara local', 'warning');
      return;
    }
    
    connectWebSocket();
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    
    intervalRef.current = setInterval(sendFrame, 1000 / fps);
    addNotification('WebSocket streaming iniciado', 'success');
  }, [connectWebSocket, sendFrame, fps, addNotification]);

  // Detener WebSocket streaming
  const stopWebSocketStreaming = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsWSConnected(false);
    setWsProcessedFrame(null);
    setWsDetections([]);
    addNotification('WebSocket streaming detenido', 'info');
  }, [addNotification]);

  // Iniciar MJPEG streaming
  const startMJPEGStreaming = useCallback(() => {
    setIsMJPEGActive(true);
    addNotification('MJPEG streaming iniciado', 'success');
  }, [addNotification]);

  // Detener MJPEG streaming
  const stopMJPEGStreaming = useCallback(() => {
    setIsMJPEGActive(false);
    addNotification('MJPEG streaming detenido', 'info');
  }, [addNotification]);

  // Liberar recursos
  const cleanup = useCallback(() => {
    stopWebSocketStreaming();
    stopMJPEGStreaming();
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, [stopWebSocketStreaming, stopMJPEGStreaming]);

  // Efectos
  useEffect(() => {
    checkCameraStatus();
    
    return () => {
      // Cleanup al desmontar el componente
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
      
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, []); // Sin dependencias para evitar bucles

  useEffect(() => {
    if (isWSConnected && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = setInterval(sendFrame, 1000 / fps);
    }
  }, [fps, isWSConnected]); // Removido sendFrame de las dependencias

  return (
    <div className="cam-v2-container p-6 bg-gray-900 rounded-xl">
      <div className="mb-6">
        <h2 className="text-3xl font-bold text-white mb-4">Cam V2 - Streaming Endpoints</h2>
        <p className="text-gray-300 mb-4">
          Visualización directa de los endpoints de streaming MJPEG y WebSocket
        </p>
        
        {/* Estado del sistema */}
        {cameraStatus && (
          <div className="mb-4 p-3 rounded-lg bg-gray-800">
            <div className="flex items-center space-x-4 text-sm">
              <span className={`px-2 py-1 rounded ${
                cameraStatus.camera_available ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
              }`}>
                Backend Cam: {cameraStatus.camera_available ? 'Disponible' : 'No disponible'}
              </span>
              <span className={`px-2 py-1 rounded ${
                cameraStatus.model_loaded ? 'bg-green-600 text-white' : 'bg-yellow-600 text-white'
              }`}>
                YOLO: {cameraStatus.model_loaded ? 'Cargado' : 'No cargado'}
              </span>
              <span className={`px-2 py-1 rounded ${
                isWSConnected ? 'bg-green-600 text-white' : 'bg-gray-600 text-white'
              }`}>
                WebSocket: {isWSConnected ? 'Conectado' : 'Desconectado'}
              </span>
              <span className={`px-2 py-1 rounded ${
                isMJPEGActive ? 'bg-green-600 text-white' : 'bg-gray-600 text-white'
              }`}>
                MJPEG: {isMJPEGActive ? 'Activo' : 'Inactivo'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Controles */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Controles WebSocket */}
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-xl font-semibold text-white mb-4">WebSocket Streaming</h3>
          <div className="space-y-3">
            <button
              onClick={initializeLocalCamera}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Inicializar Cámara Local
            </button>
            
            <div className="flex items-center space-x-3">
              <label className="text-white text-sm">FPS:</label>
              <input
                type="range"
                min="1"
                max="30"
                value={fps}
                onChange={(e) => setFps(parseInt(e.target.value))}
                className="flex-1"
              />
              <span className="text-white text-sm w-8">{fps}</span>
            </div>
            
            <button
              onClick={isWSConnected ? stopWebSocketStreaming : startWebSocketStreaming}
              disabled={!streamRef.current}
              className={`w-full px-4 py-2 rounded-lg transition-colors ${
                isWSConnected 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-green-600 hover:bg-green-700 text-white disabled:bg-gray-600'
              }`}
            >
              {isWSConnected ? 'Detener WebSocket' : 'Iniciar WebSocket'}
            </button>
            
            {/* Estadísticas WebSocket */}
            <div className="text-sm text-gray-300">
              <p>Frames enviados: {wsStats.framesSent}</p>
              <p>Frames recibidos: {wsStats.framesReceived}</p>
            </div>
          </div>
        </div>

        {/* Controles MJPEG */}
        <div className="bg-gray-800 p-4 rounded-lg">
          <h3 className="text-xl font-semibold text-white mb-4">MJPEG Streaming</h3>
          <div className="space-y-3">
            <p className="text-gray-300 text-sm">
              Streaming directo desde el backend sin cámara local
            </p>
            
            <button
              onClick={isMJPEGActive ? stopMJPEGStreaming : startMJPEGStreaming}
              className={`w-full px-4 py-2 rounded-lg transition-colors ${
                isMJPEGActive 
                  ? 'bg-red-600 hover:bg-red-700 text-white' 
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
            >
              {isMJPEGActive ? 'Detener MJPEG' : 'Iniciar MJPEG'}
            </button>
            
            <div className="text-sm text-gray-300">
              <p>Endpoint: /webcam/stream</p>
              <p>Formato: multipart/x-mixed-replace</p>
            </div>
          </div>
        </div>
      </div>

      {/* Visualización de streams */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cámara local (para WebSocket) */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-white">Cámara Local (WebSocket)</h3>
          <div className="relative bg-black rounded-lg overflow-hidden">
            {streamRef.current ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-auto max-h-64 object-contain"
              />
            ) : (
              <div className="w-full h-64 flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <div className="text-4xl mb-2">📹</div>
                  <p>Cámara no inicializada</p>
                </div>
              </div>
            )}
            <canvas ref={canvasRef} style={{ display: 'none' }} />
          </div>
        </div>

        {/* MJPEG Stream */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-white">MJPEG Stream</h3>
          <div className="relative bg-black rounded-lg overflow-hidden">
            {isMJPEGActive ? (
              <img
                ref={mjpegRef}
                src="/webcam/stream"
                alt="MJPEG Stream"
                className="w-full h-auto max-h-64 object-contain"
                onError={(e) => {
                  console.error('MJPEG stream error');
                  addNotification('Error en streaming MJPEG', 'error');
                }}
                onLoad={() => {
                  console.log('MJPEG stream loaded');
                }}
              />
            ) : (
              <div className="w-full h-64 flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <div className="text-4xl mb-2">📺</div>
                  <p>MJPEG inactivo</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* WebSocket Processed */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-white">WebSocket Procesado</h3>
          <div className="relative bg-black rounded-lg overflow-hidden">
            {wsProcessedFrame ? (
              <img
                src={wsProcessedFrame}
                alt="WebSocket Processed Frame"
                className="w-full h-auto max-h-64 object-contain"
              />
            ) : (
              <div className="w-full h-64 flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <div className="text-4xl mb-2">🤖</div>
                  <p>{isWSConnected ? 'Esperando frames...' : 'WebSocket desconectado'}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Detecciones WebSocket */}
      {wsDetections.length > 0 && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-3">Detecciones WebSocket</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {wsDetections.map((detection, index) => (
              <div key={index} className="bg-gray-700 p-3 rounded-lg">
                <div className="text-white font-medium">{detection.class}</div>
                <div className="text-gray-300 text-sm">
                  Confianza: {(detection.confidence * 100).toFixed(1)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Información técnica */}
      <div className="mt-6 p-4 bg-gray-800 rounded-lg">
        <h3 className="text-lg font-semibold text-white mb-3">Información Técnica</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-300">
          <div>
            <h4 className="font-medium text-white mb-2">MJPEG Endpoint</h4>
            <p>URL: <code className="bg-gray-700 px-1 rounded">/webcam/stream</code></p>
            <p>Método: GET</p>
            <p>Content-Type: multipart/x-mixed-replace</p>
          </div>
          <div>
            <h4 className="font-medium text-white mb-2">WebSocket Endpoint</h4>
            <p>URL: <code className="bg-gray-700 px-1 rounded">ws://localhost:8000/webcam/ws</code></p>
            <p>Protocolo: WebSocket</p>
            <p>Formato: JSON + Base64</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CamV2;