#!/usr/bin/env python3
"""
Script de prueba para verificar los endpoints de webcam streaming
"""

import requests
import json
import time

def test_webcam_endpoints():
    """Prueba los endpoints de webcam"""
    base_url = "http://localhost:8000"
    
    print("🔍 Probando endpoints de webcam...\n")
    
    # 1. Probar estado de la webcam
    print("1. Verificando estado de la webcam...")
    try:
        response = requests.get(f"{base_url}/webcam/status")
        if response.status_code == 200:
            status = response.json()
            print(f"   ✅ Estado: {status}")
            
            if status.get('camera_available'):
                print("   📹 Cámara disponible")
            else:
                print("   ❌ Cámara no disponible")
                
            if status.get('model_loaded'):
                print("   🤖 Modelo YOLO cargado")
            else:
                print("   ⚠️  Modelo YOLO no cargado")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
    
    print()
    
    # 2. Probar endpoint de streaming MJPEG
    print("2. Verificando endpoint de streaming MJPEG...")
    try:
        response = requests.get(f"{base_url}/webcam/stream", stream=True, timeout=5)
        if response.status_code == 200:
            print("   ✅ Endpoint de streaming MJPEG disponible")
            print(f"   📺 Content-Type: {response.headers.get('content-type')}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.Timeout:
        print("   ⏱️  Timeout (normal para streaming)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 3. Probar liberación de cámara
    print("3. Probando liberación de cámara...")
    try:
        response = requests.post(f"{base_url}/webcam/release")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Cámara liberada: {result.get('message')}")
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    
    # 4. Verificar que los endpoints estén en la documentación
    print("4. Verificando documentación de API...")
    try:
        response = requests.get(f"{base_url}/docs")
        if response.status_code == 200:
            print("   ✅ Documentación disponible en /docs")
        else:
            print(f"   ❌ Error accediendo a docs: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()
    print("🎯 Pruebas completadas!")
    print("\n📋 Resumen de endpoints disponibles:")
    print("   • GET  /webcam/status  - Estado de la cámara")
    print("   • GET  /webcam/stream  - Streaming MJPEG")
    print("   • WS   /webcam/ws      - WebSocket para frames")
    print("   • POST /webcam/release - Liberar cámara")
    print("\n🌐 URLs para probar:")
    print(f"   • Frontend: http://localhost:5173")
    print(f"   • Backend:  {base_url}")
    print(f"   • Docs:     {base_url}/docs")
    print(f"   • Stream:   {base_url}/webcam/stream")

if __name__ == "__main__":
    test_webcam_endpoints()