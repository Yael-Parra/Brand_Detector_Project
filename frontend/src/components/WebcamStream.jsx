import { useEffect, useRef, useState, useCallback } from "react";
import { useNotification } from "../contexts/NotificationContext";

const WebcamStream = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [processedFrame, setProcessedFrame] = useState(null);
  const [detections, setDetections] = useState([]);
  const [cameraStatus, setCameraStatus] = useState(null);
  const [streamingMode, setStreamingMode] = useState('websocket'); // 'websocket' o 'mjpeg'
  const [fps, setFps] = useState(5); // FPS para WebSocket
  
  const { addNotification } = useNotification();

  // Verificar estado de la cámara
  const checkCameraStatus = useCallback(async () => {
    try {
      const response = await fetch('/webcam/status');
      const status = await response.json();
      setCameraStatus(status);
      
      if (!status.camera_available) {
        addNotification('Cámara no disponible', 'error');
      } else if (!status.model_loaded) {
        addNotification('Modelo YOLO no cargado', 'warning');
      }
    } catch (error) {
      console.error('Error checking camera status:', error);
      addNotification('Error al verificar estado de la cámara', 'error');
    }
  }, [addNotification]);

  // Inicializar cámara del usuario
  const initializeCamera = useCallback(async () => {
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
      }
      
      addNotification('Cámara inicializada correctamente', 'success');
    } catch (error) {
      console.error('Error accessing camera:', error);
      addNotification('Error al acceder a la cámara: ' + error.message, 'error');
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
      setIsConnected(true);
      addNotification('Conectado al servidor de procesamiento', 'success');
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
          setProcessedFrame('data:image/jpeg;base64,' + data.frame);
        }
        
        if (data.detections) {
          setDetections(data.detections);
        }
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      addNotification('Desconectado del servidor', 'warning');
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      addNotification('Error de conexión WebSocket', 'error');
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
    } catch (error) {
      console.error('Error sending frame:', error);
    }
  }, []);

  // Iniciar streaming WebSocket
  const startWebSocketStreaming = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
    
    connectWebSocket();
    
    // Enviar frames a intervalos regulares
    intervalRef.current = setInterval(sendFrame, 1000 / fps);
    setIsStreaming(true);
    addNotification('Streaming WebSocket iniciado', 'success');
  }, [connectWebSocket, sendFrame, fps, addNotification]);

  // Detener streaming
  const stopStreaming = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setIsStreaming(false);
    setIsConnected(false);
    setProcessedFrame(null);
    setDetections([]);
    addNotification('Streaming detenido', 'info');
  }, [addNotification]);

  // Liberar cámara
  const releaseCamera = useCallback(async () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    
    try {
      await fetch('/webcam/release', { method: 'POST' });
    } catch (error) {
      console.error('Error releasing camera:', error);
    }
    
    addNotification('Cámara liberada', 'info');
  }, [addNotification]);

  // Efectos
  useEffect(() => {
    checkCameraStatus();
    
    return () => {
      stopStreaming();
      releaseCamera();
    };
  }, []);

  useEffect(() => {
    if (isStreaming && streamingMode === 'websocket') {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      intervalRef.current = setInterval(sendFrame, 1000 / fps);
    }
  }, [fps, isStreaming, streamingMode, sendFrame]);

  return (
    <div className="webcam-stream-container p-6 bg-gray-900 rounded-xl">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white mb-4">Detección en Tiempo Real - Webcam</h2>
        
        {/* Estado de la cámara */}
        {cameraStatus && (
          <div className="mb-4 p-3 rounded-lg bg-gray-800">
            <div className="flex items-center space-x-4 text-sm">
              <span className={`px-2 py-1 rounded ${
                cameraStatus.camera_available ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
              }`}>
                Cámara: {cameraStatus.camera_available ? 'Disponible' : 'No disponible'}
              </span>
              <span className={`px-2 py-1 rounded ${
                cameraStatus.model_loaded ? 'bg-green-600 text-white' : 'bg-yellow-600 text-white'
              }`}>
                Modelo: {cameraStatus.model_loaded ? 'Cargado' : 'No cargado'}
              </span>
              <span className={`px-2 py-1 rounded ${
                isConnected ? 'bg-green-600 text-white' : 'bg-gray-600 text-white'
              }`}>
                Conexión: {isConnected ? 'Conectado' : 'Desconectado'}
              </span>
            </div>
          </div>
        )}
        
        {/* Controles */}
        <div className="flex flex-wrap gap-3 mb-4">
          <button
            onClick={initializeCamera}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Inicializar Cámara
          </button>
          
          <button
            onClick={isStreaming ? stopStreaming : startWebSocketStreaming}
            disabled={!streamRef.current}
            className={`px-4 py-2 rounded-lg transition-colors ${
              isStreaming 
                ? 'bg-red-600 hover:bg-red-700 text-white' 
                : 'bg-green-600 hover:bg-green-700 text-white disabled:bg-gray-600'
            }`}
          >
            {isStreaming ? 'Detener Streaming' : 'Iniciar Streaming'}
          </button>
          
          <button
            onClick={releaseCamera}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Liberar Cámara
          </button>
        </div>
        
        {/* Configuración FPS */}
        <div className="flex items-center space-x-3 mb-4">
          <label className="text-white text-sm">FPS:</label>
          <input
            type="range"
            min="1"
            max="30"
            value={fps}
            onChange={(e) => setFps(parseInt(e.target.value))}
            className="w-32"
          />
          <span className="text-white text-sm">{fps}</span>
        </div>
      </div>
      
      {/* Videos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Video original */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-white">Cámara Original</h3>
          <div className="relative bg-black rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-auto max-h-96 object-contain"
            />
            <canvas
              ref={canvasRef}
              style={{ display: 'none' }}
            />
          </div>
        </div>
        
        {/* Video procesado */}
        <div className="space-y-3">
          <h3 className="text-lg font-semibold text-white">Detección YOLO</h3>
          <div className="relative bg-black rounded-lg overflow-hidden">
            {streamingMode === 'mjpeg' ? (
              <img
                src="/webcam/stream"
                alt="MJPEG Stream"
                className="w-full h-auto max-h-96 object-contain"
                onError={(e) => {
                  console.error('MJPEG stream error');
                  addNotification('Error en streaming MJPEG', 'error');
                }}
              />
            ) : processedFrame ? (
              <img
                src={processedFrame}
                alt="Processed Frame"
                className="w-full h-auto max-h-96 object-contain"
              />
            ) : (
              <div className="w-full h-96 flex items-center justify-center text-gray-400">
                {isStreaming ? 'Procesando...' : 'Inicia el streaming para ver detecciones'}
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Detecciones */}
      {detections.length > 0 && (
        <div className="mt-6 p-4 bg-gray-800 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-3">Detecciones Actuales</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {detections.map((detection, index) => (
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
    </div>
  );
};

export default WebcamStream;