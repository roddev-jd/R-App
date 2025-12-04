# Sistema de Páginas de Herramientas de Diseño

Este sistema crea páginas individuales para cada herramienta de diseño con coherencia visual completa con el frontend principal.

## 🎯 Características

- **Páginas individuales** para cada herramienta con descripción detallada
- **Soporte para videos de YouTube** embebidos
- **Botón de ejecución** que mantiene la funcionalidad original
- **Diseño coherente** con el tema principal de FlexStart
- **Navegación intuitiva** con breadcrumbs
- **Responsive design** para todos los dispositivos

## 📁 Estructura de Archivos

```
FlexStart/herramientas/
├── template.html              # Plantilla base para todas las páginas
├── generate_tool_pages.py     # Generador de páginas
├── update_video.py           # Script para actualizar videos
├── tools_config.json         # Configuración de herramientas
├── README.md                 # Esta documentación
└── [herramienta].html        # Páginas individuales generadas
```

## 🚀 Cómo Usar

### 1. Regenerar Todas las Páginas

```bash
cd FlexStart/herramientas
python3 generate_tool_pages.py
```

### 2. Agregar Video a una Herramienta

Una vez que grabes los videos de demostración en YouTube:

```bash
python3 update_video.py buscador_diseno "https://youtube.com/watch?v=TU_VIDEO_ID"
```

**Herramientas disponibles:**
- `buscador_diseno` - Buscador de Carpetas
- `RipleyDownloader` - Descargador Universal Ripley  
- `Dept` - Organizador por Departamentos
- `Encarpetar` - Monitor Encarpetador
- `Indexar` - Generador de Listados
- `Scrapper` - Descargador por Enlaces
- `miniaturas_diseno` - Generador de Miniaturas
- `Compresor` - Compresor de Imágenes

### 3. Personalizar Información de una Herramienta

Edita el archivo `generate_tool_pages.py` en la sección `TOOLS_CONFIG` y luego regenera las páginas.

## 🎨 Elementos Visuales

Cada página incluye:

- **Header con gradiente** matching el tema principal
- **Breadcrumb navigation** para fácil navegación
- **Descripción detallada** de la herramienta
- **Lista de características** principales
- **Sección de video** (placeholder hasta que agregues videos)
- **Botón de ejecución** prominente y funcional
- **Información rápida** en sidebar

## 🔧 Configuración del Backend

El backend FastAPI ya está configurado para servir estas páginas en:
- Ruta base: `/herramientas/`
- Ejemplo: `http://localhost:8000/herramientas/buscador_diseno.html`

## 🎬 Agregando Videos

Para agregar un video de YouTube:

1. Sube tu video a YouTube
2. Copia la URL completa (ej: `https://youtube.com/watch?v=ABC123`)
3. Ejecuta el comando de actualización:
   ```bash
   python3 update_video.py [tool_id] "[youtube_url]"
   ```

El sistema automáticamente:
- Extrae el ID del video
- Genera el código embed apropiado
- Actualiza la página HTML
- Guarda la configuración

## 📱 Responsive Design

Las páginas están optimizadas para:
- Desktop (1200px+)
- Tablet (768px - 1199px) 
- Mobile (< 768px)

## 🎯 Funcionalidad Mantenida

- **Ejecución de scripts** funciona igual que antes
- **Estados de loading** con spinners
- **Manejo de errores** robusto
- **Feedback visual** al usuario

## 🔄 Flujo de Usuario

1. Usuario hace clic en botón en la página principal
2. Se abre nueva pestaña con página de la herramienta
3. Usuario lee descripción y ve video demo
4. Usuario hace clic en "Ejecutar [Herramienta]"
5. Script se ejecuta como antes

## ✨ Beneficios

- **Mejor experiencia de usuario** con información detallada
- **Profesionalismo** mejorado con páginas dedicadas
- **Facilidad de mantenimiento** con sistema generador
- **Escalabilidad** fácil para nuevas herramientas
- **SEO optimizado** con meta tags apropiados

¡El sistema está listo para usar! Solo necesitas agregar los videos cuando los grabes.