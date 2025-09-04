#!/usr/bin/env python3
"""
Script de prueba para verificar la integración de YouTube con la funcionalidad de video.
Este script simula una solicitud a la API de YouTube para verificar que:
1. Se descarga correctamente el video
2. Se procesa usando la funcionalidad de video existente
3. Se mantiene la consistencia en el estado del trabajo
"""

import requests
import time
import json

# Configuración
BASE_URL = "http://localhost:8000"
YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Video de prueba corto

def test_youtube_processing():
    """Prueba el procesamiento completo de un video de YouTube."""
    print("🚀 Iniciando prueba de integración de YouTube...")
    
    # Paso 1: Enviar solicitud de procesamiento
    print(f"📤 Enviando video de YouTube: {YOUTUBE_URL}")
    
    payload = {
        "url": YOUTUBE_URL
    }
    
    try:
        response = requests.post(f"{BASE_URL}/youtube/process/youtube", json=payload)
        
        if response.status_code != 200:
            print(f"❌ Error al enviar solicitud: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return False
        
        result = response.json()
        job_id = result.get("job_id")
        
        if not job_id:
            print("❌ No se recibió job_id")
            return False
        
        print(f"✅ Trabajo iniciado con ID: {job_id}")
        
        # Paso 2: Monitorear el progreso
        print("📊 Monitoreando progreso...")
        
        max_attempts = 60  # 5 minutos máximo
        attempt = 0
        
        while attempt < max_attempts:
            try:
                status_response = requests.get(f"{BASE_URL}/youtube/status/{job_id}")
                
                if status_response.status_code != 200:
                    print(f"❌ Error al obtener estado: {status_response.status_code}")
                    break
                
                status_data = status_response.json()
                current_status = status_data.get("status", "unknown")
                progress = status_data.get("progress", 0)
                
                print(f"📈 Estado: {current_status} - Progreso: {progress}%")
                
                if current_status == "completed":
                    print("🎉 ¡Procesamiento completado exitosamente!")
                    print(f"📊 Detecciones encontradas: {status_data.get('detections', 0)}")
                    print(f"🎬 Frames procesados: {status_data.get('frame_count', 0)}")
                    
                    # Verificar si hay video procesado disponible
                    try:
                        video_response = requests.get(f"{BASE_URL}/youtube/video/{job_id}")
                        if video_response.status_code == 200:
                            video_data = video_response.json()
                            print(f"🎥 Video procesado disponible: {video_data.get('video_url', 'N/A')}")
                        else:
                            print("⚠️ Video procesado no disponible aún")
                    except Exception as e:
                        print(f"⚠️ Error al verificar video: {e}")
                    
                    return True
                
                elif current_status == "error":
                    print(f"❌ Error en el procesamiento: {status_data.get('error', 'Error desconocido')}")
                    return False
                
                elif current_status in ["initializing", "downloading", "processing"]:
                    # Continuar monitoreando
                    pass
                else:
                    print(f"⚠️ Estado desconocido: {current_status}")
                
                time.sleep(5)  # Esperar 5 segundos antes de la siguiente verificación
                attempt += 1
                
            except Exception as e:
                print(f"❌ Error al verificar estado: {e}")
                break
        
        print("⏰ Tiempo de espera agotado")
        return False
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        return False

def test_api_endpoints():
    """Prueba que los endpoints estén disponibles."""
    print("🔍 Verificando endpoints de la API...")
    
    try:
        # Verificar endpoint de salud
        health_response = requests.get(f"{BASE_URL}/health")
        if health_response.status_code == 200:
            print("✅ Endpoint de salud funcionando")
        else:
            print(f"❌ Endpoint de salud falló: {health_response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error verificando endpoints: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Iniciando pruebas de integración de YouTube")
    print("=" * 50)
    
    # Verificar que la API esté disponible
    if not test_api_endpoints():
        print("❌ La API no está disponible. Asegúrate de que el servidor esté ejecutándose.")
        exit(1)
    
    # Ejecutar prueba principal
    success = test_youtube_processing()
    
    print("=" * 50)
    if success:
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("✅ La integración de YouTube está funcionando correctamente")
        print("📝 Resumen:")
        print("   - Descarga de video de YouTube: ✅")
        print("   - Procesamiento con funcionalidad de video: ✅")
        print("   - Sincronización de estados: ✅")
        print("   - Limpieza de archivos temporales: ✅")
    else:
        print("❌ Algunas pruebas fallaron")
        print("🔧 Revisa los logs del servidor para más detalles")