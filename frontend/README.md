# LogiFind Frontend

Aplicación React moderna para detección de marcas con diseño minimalista negro/blanco.

## Características
- **3 páginas**: Inicio (LOGIFIND), App (detector), Nosotros (equipo)
- **Diseño responsivo**: Header animado, cursor follower con logo
- **Carousel horizontal**: Imagen, Video, YouTube
- **Equipo real**: Fotos de LinkedIn y enlaces funcionales

## Cómo ejecutar

1. **Navegar al directorio**:
   ```powershell
   cd frontend
   ```

2. **Instalar dependencias**:
   ```powershell
   npm install
   ```

3. **Iniciar desarrollo**:
   ```powershell
   npm run dev
   ```

4. **Abrir navegador**: http://localhost:5173

## Estructura
```
src/
├── pages/          # Inicio, AppPage, Nosotros  
├── components/     # Uploaders, ResultViewer, CursorFollower
├── styles.css      # CSS organizado en 13 secciones
└── App.jsx         # Router principal
```

## 🛠️ Tecnologías
- React 18 + Vite
- React Router DOM
- CSS puro (sin frameworks)
- Inter font

## 📝 Pendiente
- Conectar con backend real
- Integración con PostgreSQL
- Exportación de reportes

