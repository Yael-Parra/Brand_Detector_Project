
<h1 align="center">Brand Detector Project</h1>

<p align="center">
  Summary
</p>

---

## 🧭 Table of Contents

- [📌 Project Overview](#-project-overview)
- [📎 Useful links](#-useful-links)
- [🎯 Target Audience](#-target-audience)
- [⚙️ General Project Overview](#️-general-project-overview)
- [🚀 Future features & Implementations](#-future-features--implementations)
- [🛠️ Tools & Technologies](#-tools--technologies)
- [🧪 Model Architecture](#-model-architecture)
- [📁 Project Structure](#-project-structure)
- [✍ Deployment Instructions](#-deployment-instructions)
- [👩 Contributors](#-contributors)

---

## 📌 Project Overview

<p align="justify">  
  
Este proyecto de <strong>Computer Vision</strong> está diseñado para <strong>detectar</strong> y <strong>analizar</strong> la aparición de <strong>logos</strong> en <strong>imágenes</strong>, <strong>vídeos</strong>, <strong>enlaces</strong> o <strong>streaming en vivo</strong>, utilizando un modelo <strong>YOLO</strong> entrenado con <strong>Roboflow</strong> e integrado en un backend <strong>FastAPI</strong>. El sistema <strong>procesa</strong> el contenido, <strong>identifica</strong> las marcas, <strong>calcula</strong> el tiempo total y el porcentaje de aparición, y <strong>almacena</strong> los resultados en una base de datos <strong>PostgreSQL (Neon)</strong> estructurada en dos tablas: <strong>videos</strong>, que registra metadatos como tipo, nombre y duración del vídeo; y <strong>logo_detector</strong>, que guarda las detecciones con información como nombre de la marca, número de frames detectados, <em>FPS</em> y porcentaje de aparición, vinculadas al vídeo correspondiente. El frontend, desarrollado con <strong>React</strong> + <strong>Vite</strong>, ofrece una interfaz intuitiva para <strong>subir</strong> o <strong>capturar</strong> contenido y <strong>visualizar</strong> los resultados procesados.
</p>


---
## 📎 Useful links

- https://app.roboflow.com/test1mrm/customlogomercedez-hxxq6/overview 
---

## 🎯 Target Audience

- **Equipos de marketing y publicidad** que necesiten medir la exposición de marcas.
- **Medios y transmisiones en vivo** que quieran monitorear logos en su contenido.
- **Organizaciones deportivas** y eventos para evaluar visibilidad de patrocinadores.
  
---

## 🔧 General Project Overview

Este proyecto de **Computer Vision** permite la **detección y análisis de logos** en imágenes, vídeos, enlaces o streaming en vivo, utilizando un modelo **YOLO** entrenado con **Roboflow** e integrado en un backend **FastAPI**.  
El sistema procesa el contenido, identifica marcas, calcula métricas de aparición y almacena los resultados en una base de datos **PostgreSQL (Neon)**.  
El frontend, desarrollado con **React + Vite**, ofrece una interfaz intuitiva para subir o capturar contenido y visualizar los resultados.

### Features

| ✅ Pros                                                                 | ❌ Cons                                                                                  |
|-------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| Detección en tiempo real de logos en múltiples formatos                 | Requiere hardware con GPU para un rendimiento óptimo                                     |
| Integración completa backend (FastAPI) + frontend (React + Vite)        | Entrenamiento del modelo dependiente de datasets de calidad                              |
| Métricas detalladas: tiempo total, porcentaje de aparición, FPS         | Procesamiento de vídeos largos puede ser más lento                                       |
| Base de datos estructurada con historial de detecciones                 |                       |
| Escalable y adaptable a nuevos logos o marcas                           |                              |

---

## 🧠 Architecture & Services


- **Frontend:** React + Vite para carga de contenido y visualización de resultados.  
- **Backend:** FastAPI para procesar peticiones y ejecutar el modelo YOLO.  
- **Modelo de IA:** YOLO entrenado con Roboflow para detección de logos.  
- **Base de datos:** PostgreSQL (Neon) para almacenar metadatos y resultados.  
- **Servicios adicionales:** Integración con streaming en vivo y análisis en tiempo real.  

---

## 🚀 Future Features & Implementations

### Planned Improvements
-
-


---

## 🛠️ Tools & Technologies

### ⚙️ Backend

![React](https://img.shields.io/badge/-React-ffffff?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/-Vite-ffffff?logo=vite&logoColor=black)
![FastAPI](https://img.shields.io/badge/-FastAPI-ffffff?logo=fastapi&logoColor=black)
![Roboflow](https://img.shields.io/badge/-Roboflow-ffffff?logo=roboflow&logoColor=black)
![Python](https://img.shields.io/badge/-Python-ffffff?logo=python&logoColor=black)
![YOLO](https://img.shields.io/badge/-YOLO-ffffff?logo=yolo&logoColor=black)
![Neon](https://img.shields.io/badge/-Neon-ffffff?logo=neon&logoColor=black)


### 🌐 Web UI & Interfaces

-

---

## 🧪 Model Architecture



<p align="center">
  <img src=https://github.com/Yael-Parra/Brand_Detector_Project/issues/5#issuecomment-3245008872" alt="System Architecture Diagram" width="700"/>
</p>


## 📁 Project Structure

```
📦 Brand_Detector_Project  
├── 📁 backend                                   
│   └── 📁 database
│   └── 📁 models
│   └── 📁 services
│   └── 📁 HACE FALTA CONTINUAR ESTO!
│   └── 🗒️ main.py     
│
├── 📁 frontend
│   └── 📁 public
│   └── 📁 src
│        └── 📁 components
│        └── 📁 pages
│        └── 🗒️ App.jsx
│        └── 🗒️ main.jsx
│        └── 🗒️ styles.css
├── README.md                
├── requirements.txt        
├── .env_example                     
├── .gitignore              
  

```
---

## ✍ Deployment Instructions


🧪 1. Clone the repository

    git clone https://github.com/your-username/your-repo.git
    cd your-repo

🔐 2. Configure environment variables

Create a .env file in the project root and add your variables (e.g.):

  
📦 3. Install the requirements

    pip install -r requirements.txt


---
## 👩‍💻 Contributors
We are AI students with a heart and passion for building better solutions for real problems.
Feel free to explore, fork, or connect with us for ideas, feedback, or collaborations.


| Name                  | GitHub                                                                                                                     | LinkedIn                                                                                                                                             |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Yael Parra**        | [![GitHub](https://img.shields.io/badge/GitHub-ffffff?logo=github&logoColor=black)](https://github.com/Yael-Parra)         | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=black)](https://www.linkedin.com/in/yael-parra/)                   |
| **Max Belrtán**       | [![GitHub](https://img.shields.io/badge/GitHub-ffffff?logo=github&logoColor=black)](https://github.com/mr-melenas)         | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/max-beltran/)                   |
| **Alla Haruty**       | [![GitHub](https://img.shields.io/badge/GitHub-ffffff?logo=github&logoColor=black)](https://github.com/alharuty)         | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/allaharuty/)                   |
| **Stephany Ángeles**  | [![GitHub](https://img.shields.io/badge/GitHub-ffffff?logo=github&logoColor=black)](https://github.com/stephyangeles)         | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/stephyangeles/)                   |
| **Orlando Alcalá**    | [![GitHub](https://img.shields.io/badge/GitHub-ffffff?logo=github&logoColor=black)](https://github.com/odar1997)         | [![LinkedIn](https://img.shields.io/badge/LinkedIn-0A66C2?logo=linkedin&logoColor=white)]([https://www.linkedin.com/in/yael-parra/](https://www.linkedin.com/in/orlando-david-71417411b/))                   |
