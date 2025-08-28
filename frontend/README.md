# Frontend - LogiFind

Interfaz React (Vite) con diseño oscuro (fondo negro), controles y tarjetas en negro con bordes blancos, y navegación por rutas (react-router).

## Estado actual
- Diseño en paleta monocroma: fondo negro, texto y bordes en blanco. Los grises solo se usan como acento en estados hover/active de botones.
- Eliminadas las referencias/emojis innecesarios de la interfaz.
- Tipografía: Inter (weights: 700 para títulos, 400 para texto normal).
- Navegación basada en rutas con `react-router-dom` (páginas: `/`, `/app`, `/nosotros`).
- Páginas separadas en `src/pages/` (Inicio, AppPage, Nosotros).
- UI responsiva con menú hamburguesa; en móvil la página Inicio queda alineada a la izquierda según diseño.
- Título principal (`LOGIFIND`) aumentado para presencia visual; tech badges compactos.

## Estructura de archivos (relevantes)
- `src/App.jsx` — Router, header/footer y layout general
- `src/pages/Inicio.jsx` — Página de inicio (LOGIFIND)
- `src/pages/AppPage.jsx` — Interfaz del detector (uploaders + resultados)
- `src/pages/Nosotros.jsx` — Información del equipo
- `src/components/` — `ImageUploader`, `VideoUploader`, `YoutubeInput`, `ResultViewer`
- `src/styles.css` — Estilos globales 

## Dependencias
- react 18
- react-dom
- vite
- react-router-dom (añadido para enrutamiento de páginas)

## Cómo ejecutar (desarrollo)
1. Instalar dependencias:
   powershell> npm install
2. Iniciar servidor de desarrollo:
   powershell> npm run dev
3. Abrir en navegador: http://localhost:5173 (o la URL que Vite muestre)

> Nota: si desplegarás en un servidor estático y no quieres configurar rewrite rules, considera usar `HashRouter`.

## Cambios de diseño importantes
- Se reajustaron estados hover para que los grises aparezcan solo en interacciones (hover/active).
- Mobile: Inicio alineado a la izquierda, badges en fila/compactos y CTA alineado a la izquierda.

## Integración pendiente
- Conectar con backend real para reemplazar simulaciones de detección.
- Conectar a PostgreSQL (tablas `videos`, `processes`) — backend ya contiene scripts de creación.
- Añadir exportación de reportes y autenticación según necesidades.

## Developer notes
- Para cambiar la paleta o restaurar grises en algún bloque, revisar `src/styles.css` las variables en `:root`.
- El archivo `frontend/package.json` contiene la dependencia `react-router-dom`; si se crea build, probar rutas en el servidor que sirva index.html en todas las rutas.

