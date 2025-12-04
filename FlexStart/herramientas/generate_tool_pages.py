#!/usr/bin/env python3
"""
Generador de páginas individuales para herramientas de diseño
Mantiene la coherencia visual con el frontend principal
"""

import os
import json

# Configuración de herramientas con toda la información necesaria
TOOLS_CONFIG = {
    "buscador_diseno": {
        "name": "Buscador de Carpetas",
        "subtitle": "Herramienta para buscar y copiar carpetas automáticamente",
        "category": "Administración de Archivos",
        "type": "Herramienta Python",
        "icon": "bi bi-search",
        "script_id": "buscador_diseno",
        "long_description": """
        <p>Esta herramienta te permite buscar carpetas específicas basándose en una planilla Excel o CSV y copiarlas automáticamente a un destino seleccionado.</p>
        <p>Es especialmente útil para:</p>
        <ul>
            <li>Automatizar la búsqueda de carpetas por códigos SKU</li>
            <li>Copiar múltiples carpetas de manera eficiente</li>
            <li>Filtrar carpetas por departamentos específicos</li>
            <li>Generar reportes de las operaciones realizadas</li>
        </ul>
        """,
        "features": [
            "Búsqueda automática basada en planillas Excel/CSV",
            "Copia masiva de carpetas encontradas",
            "Filtrado por departamentos",
            "Interfaz gráfica intuitiva",
            "Reportes detallados de operaciones",
            "Soporte para múltiples formatos de archivo"
        ],
        "video_url": ""  # Se llenará cuando grabes el video
    },
    
    "RipleyDownloader": {
        "name": "Descargador Universal Ripley",
        "subtitle": "Descarga automática de imágenes desde múltiples fuentes",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-cloud-download-fill",
        "script_id": "RipleyDownloader",
        "long_description": """
        <p>Herramienta completa para la descarga automática de imágenes de productos desde diferentes fuentes de Ripley.</p>
        <p>Características destacadas:</p>
        <ul>
            <li>Soporte para múltiples países (Chile, Perú)</li>
            <li>Descarga desde planillas Excel con códigos SKU</li>
            <li>Manejo inteligente de errores y reintentos</li>
            <li>Interfaz moderna con progreso en tiempo real</li>
        </ul>
        """,
        "features": [
            "Descarga desde planillas Excel",
            "Soporte multi-país (Chile/Perú)",
            "Sistema de reintentos automáticos",
            "Interfaz moderna con Bootstrap",
            "Progreso en tiempo real",
            "Manejo robusto de errores de conexión",
            "Organización automática de archivos"
        ],
        "video_url": ""
    },
    
    "Dept": {
        "name": "Organizador por Departamentos",
        "subtitle": "Organiza archivos automáticamente por departamentos",
        "category": "Administración de Archivos",
        "type": "Herramienta Python",
        "icon": "bi bi-archive-fill",
        "script_id": "Dept",
        "long_description": """
        <p>Automatiza la organización de archivos clasificándolos por departamentos según códigos predefinidos.</p>
        <p>Ideal para:</p>
        <ul>
            <li>Organizar grandes volúmenes de archivos por departamento</li>
            <li>Clasificación automática basada en códigos SKU</li>
            <li>Mantenimiento de estructura organizacional</li>
        </ul>
        """,
        "features": [
            "Clasificación automática por departamentos",
            "Reconocimiento de códigos SKU",
            "Creación automática de estructura de carpetas",
            "Procesamiento por lotes",
            "Interfaz gráfica simple"
        ],
        "video_url": ""
    },
    
    "Encarpetar": {
        "name": "Monitor Encarpetador",
        "subtitle": "Monitorea y organiza archivos automáticamente",
        "category": "Administración de Archivos", 
        "type": "Herramienta Python",
        "icon": "bi bi-eyeglasses",
        "script_id": "Encarpetar",
        "long_description": """
        <p>Sistema de monitoreo que observa carpetas y organiza automáticamente los archivos que se agreguen.</p>
        <p>Funcionalidades principales:</p>
        <ul>
            <li>Monitoreo en tiempo real de carpetas</li>
            <li>Organización automática de archivos nuevos</li>
            <li>Reglas personalizables de clasificación</li>
        </ul>
        """,
        "features": [
            "Monitoreo en tiempo real",
            "Organización automática",
            "Reglas personalizables",
            "Notificaciones de actividad",
            "Interfaz de control simple"
        ],
        "video_url": ""
    },
    
    "Indexar": {
        "name": "Generador de Listados",
        "subtitle": "Crea listados Excel de estructuras de carpetas",
        "category": "Administración de Archivos",
        "type": "Herramienta Python", 
        "icon": "bi bi-card-checklist",
        "script_id": "Indexar",
        "long_description": """
        <p>Genera listados detallados en Excel de estructuras de carpetas, extrayendo códigos SKU y organizando la información.</p>
        <p>Características:</p>
        <ul>
            <li>Escaneo completo de estructuras de carpetas</li>
            <li>Extracción automática de códigos SKU</li>
            <li>Exportación a formato Excel</li>
            <li>Datos organizados y listos para análisis</li>
        </ul>
        """,
        "features": [
            "Escaneo recursivo de carpetas",
            "Extracción de códigos SKU",
            "Exportación a Excel",
            "Interfaz moderna con CustomTkinter", 
            "Datos estructurados y organizados"
        ],
        "video_url": ""
    },
    
    "Scrapper": {
        "name": "Descargador por Enlaces",
        "subtitle": "Descarga archivos desde URLs específicas",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-binoculars-fill", 
        "script_id": "Scrapper",
        "long_description": """
        <p>Herramienta especializada para descargar archivos desde enlaces web específicos de manera automatizada.</p>
        <p>Ideal para:</p>
        <ul>
            <li>Descarga masiva desde listas de URLs</li>
            <li>Extracción de contenido web automatizada</li>
            <li>Procesamiento de enlaces desde planillas</li>
        </ul>
        """,
        "features": [
            "Descarga desde listas de URLs",
            "Manejo robusto de conexiones",
            "Soporte para múltiples formatos",
            "Sistema de reintentos",
            "Progreso visual detallado"
        ],
        "video_url": ""
    },
    
    "miniaturas_diseno": {
        "name": "Generador de Miniaturas",
        "subtitle": "Crea miniaturas optimizadas de imágenes",
        "category": "Gestión de Imágenes",
        "type": "Herramienta Python",
        "icon": "bi bi-aspect-ratio",
        "script_id": "miniaturas_diseno", 
        "long_description": """
        <p>Genera miniaturas de alta calidad para imágenes, optimizando el tamaño y manteniendo la calidad visual.</p>
        <p>Funcionalidades:</p>
        <ul>
            <li>Procesamiento por lotes de imágenes</li>
            <li>Múltiples tamaños de salida</li>
            <li>Optimización automática de calidad</li>
            <li>Preservación de proporciones</li>
        </ul>
        """,
        "features": [
            "Procesamiento por lotes",
            "Múltiples tamaños personalizables",
            "Optimización de calidad automática", 
            "Preservación de aspectos",
            "Formatos de salida variados",
            "Interfaz gráfica intuitiva"
        ],
        "video_url": ""
    },
    
    "Compresor": {
        "name": "Compresor de Imágenes",
        "subtitle": "Reduce el tamaño de archivos sin perder calidad",
        "category": "Gestión de Imágenes",
        "type": "Herramienta Python",
        "icon": "bi bi-file-earmark-zip-fill",
        "script_id": "Compresor",
        "long_description": """
        <p>Comprime imágenes de manera inteligente, reduciendo significativamente el tamaño de archivo mientras mantiene una calidad visual aceptable.</p>
        <p>Características avanzadas:</p>
        <ul>
            <li>Algoritmos de compresión optimizados</li>
            <li>Control granular de calidad</li>
            <li>Procesamiento por lotes eficiente</li>
            <li>Comparación antes/después</li>
        </ul>
        """,
        "features": [
            "Compresión inteligente",
            "Control de calidad ajustable",
            "Procesamiento por lotes",
            "Vista previa de resultados",
            "Múltiples algoritmos de compresión",
            "Estadísticas de reducción de tamaño"
        ],
        "video_url": ""
    },
    
    "Prod-Selector": {
        "name": "Selector de Producción",
        "subtitle": "Selecciona productos para requerimientos específicos",
        "category": "Administración de Archivos",
        "type": "Herramienta Python",
        "icon": "bi bi-check2-circle",
        "script_id": "Prod-Selector",
        "long_description": """
        <p>Herramienta especializada para seleccionar productos específicos basándose en requerimientos y criterios predefinidos.</p>
        <p>Ideal para:</p>
        <ul>
            <li>Filtrar productos por características específicas</li>
            <li>Generar listas de productos para campañas</li>
            <li>Automatizar la selección de inventario</li>
            <li>Crear reportes de productos seleccionados</li>
        </ul>
        """,
        "features": [
            "Filtrado avanzado de productos",
            "Criterios de selección personalizables",
            "Exportación de listas seleccionadas",
            "Interfaz gráfica intuitiva",
            "Reportes detallados",
            "Integración con bases de datos"
        ],
        "video_url": ""
    },
    
    "SVC-OK": {
        "name": "Separador SVC",
        "subtitle": "Separa y migra productos en estado OK",
        "category": "Administración de Archivos",
        "type": "Herramienta Python",
        "icon": "bi bi-bookmarks-fill",
        "script_id": "SVC-OK",
        "long_description": """
        <p>Herramienta que identifica y separa los productos SVC que están en estado OK para su posterior migración o procesamiento.</p>
        <p>Funcionalidades principales:</p>
        <ul>
            <li>Análisis automático de estados SVC</li>
            <li>Separación de productos OK</li>
            <li>Migración automatizada a carpetas de producción</li>
            <li>Generación de reportes de estado</li>
        </ul>
        """,
        "features": [
            "Detección automática de productos OK",
            "Separación inteligente por estado",
            "Migración automatizada",
            "Reportes de procesamiento",
            "Validación de integridad",
            "Interfaz de monitoreo"
        ],
        "video_url": ""
    },
    
    "TeamSearch": {
        "name": "Buscador de Equipo",
        "subtitle": "Busca y gestiona información del equipo de trabajo",
        "category": "Administración de Archivos",
        "type": "Herramienta Python",
        "icon": "bi bi-microsoft-teams",
        "script_id": "TeamSearch",
        "long_description": """
        <p>Sistema de búsqueda que permite encontrar y gestionar información relacionada con el equipo de trabajo y sus asignaciones.</p>
        <p>Características destacadas:</p>
        <ul>
            <li>Búsqueda avanzada de miembros del equipo</li>
            <li>Gestión de asignaciones de trabajo</li>
            <li>Consulta de disponibilidad</li>
            <li>Reportes de productividad</li>
        </ul>
        """,
        "features": [
            "Búsqueda avanzada de team members",
            "Gestión de asignaciones",
            "Consulta de estados de trabajo",
            "Reportes de productividad",
            "Interfaz moderna y eficiente",
            "Integración con sistemas de gestión"
        ],
        "video_url": ""
    },
    
    "Renamer-PH": {
        "name": "Renombrador Padre-Hijo",
        "subtitle": "Renombra archivos con relación padre-hijo",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-arrow-bar-right",
        "script_id": "Renamer-PH",
        "long_description": """
        <p>Herramienta especializada en renombrar archivos manteniendo la relación jerárquica padre-hijo entre productos.</p>
        <p>Funcionalidades clave:</p>
        <ul>
            <li>Reconocimiento de relaciones padre-hijo</li>
            <li>Renombrado masivo con preservación de jerarquía</li>
            <li>Validación de nomenclatura</li>
            <li>Reportes de cambios realizados</li>
        </ul>
        """,
        "features": [
            "Detección automática de relaciones P-H",
            "Renombrado masivo inteligente",
            "Preservación de estructura jerárquica",
            "Validación de nomenclatura",
            "Reportes detallados de cambios",
            "Interfaz gráfica moderna"
        ],
        "video_url": ""
    },
    
    "Renamer-Rimage": {
        "name": "Renombrador Rimage",
        "subtitle": "Renombrador específico para imágenes Rimage",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-arrows-expand-vertical",
        "script_id": "Renamer-Rimage",
        "long_description": """
        <p>Renombrador especializado para imágenes del sistema Rimage, aplicando nomenclaturas específicas y estándares de la plataforma.</p>
        <p>Características específicas:</p>
        <ul>
            <li>Nomenclatura específica para Rimage</li>
            <li>Validación de formatos de imagen</li>
            <li>Procesamiento por lotes</li>
            <li>Integración con workflows Rimage</li>
        </ul>
        """,
        "features": [
            "Nomenclatura específica Rimage",
            "Validación de formatos",
            "Procesamiento masivo",
            "Integración con workflows",
            "Reportes de conversión",
            "Interfaz optimizada"
        ],
        "video_url": ""
    },
    
    "Renamer-ImgFile": {
        "name": "Renombrador de Imágenes",
        "subtitle": "Renombra imágenes según estructura de carpetas",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-check2-square",
        "script_id": "Renamer-ImgFile",
        "long_description": """
        <p>Herramienta que renombra imágenes automáticamente basándose en la estructura de carpetas donde se encuentran.</p>
        <p>Funcionalidades principales:</p>
        <ul>
            <li>Renombrado automático por ubicación</li>
            <li>Extracción de información de rutas</li>
            <li>Mantenimiento de organización</li>
            <li>Procesamiento recursivo</li>
        </ul>
        """,
        "features": [
            "Renombrado automático por carpeta",
            "Extracción de metadata de rutas",
            "Procesamiento recursivo",
            "Preservación de organización",
            "Validación de nombres",
            "Reportes de procesamiento"
        ],
        "video_url": ""
    },
    
    "Renamer-Muestras": {
        "name": "Renombrador de Muestras",
        "subtitle": "Renombra archivos para columna Muestras",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-bookmark-check",
        "script_id": "Renamer-Muestras",
        "long_description": """
        <p>Renombrador específico para archivos de muestras, aplicando nomenclatura compatible con sistemas de gestión de muestras.</p>
        <p>Características especializadas:</p>
        <ul>
            <li>Nomenclatura específica para muestras</li>
            <li>Integración con columnas de datos</li>
            <li>Validación de formatos</li>
            <li>Organización automática</li>
        </ul>
        """,
        "features": [
            "Nomenclatura específica de muestras",
            "Integración con bases de datos",
            "Validación automática",
            "Organización inteligente",
            "Reportes de procesamiento",
            "Interfaz especializada"
        ],
        "video_url": ""
    },
    
    "lastImage": {
        "name": "Monitor Última Imagen",
        "subtitle": "Monitorea y añade la última imagen procesada",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-align-end",
        "script_id": "lastImage",
        "long_description": """
        <p>Sistema de monitoreo que detecta y añade automáticamente la última imagen procesada a los conjuntos de trabajo.</p>
        <p>Funcionalidades de monitoreo:</p>
        <ul>
            <li>Monitoreo en tiempo real</li>
            <li>Detección de nuevas imágenes</li>
            <li>Añadido automático al flujo</li>
            <li>Notificaciones de actividad</li>
        </ul>
        """,
        "features": [
            "Monitoreo en tiempo real",
            "Detección automática de imágenes",
            "Integración automática al flujo",
            "Notificaciones push",
            "Historial de actividad",
            "Interfaz de control intuitiva"
        ],
        "video_url": ""
    },
    
    "Insert": {
        "name": "Monitor de Inserción",
        "subtitle": "Inserta imágenes correlativas automáticamente",
        "category": "Gestión de Mejoras",
        "type": "Herramienta Python",
        "icon": "bi bi-box-arrow-in-right",
        "script_id": "Insert",
        "long_description": """
        <p>Monitor automatizado que inserta imágenes correlativas en secuencias de trabajo, manteniendo el orden y correlación apropiados.</p>
        <p>Características avanzadas:</p>
        <ul>
            <li>Detección de secuencias correlativas</li>
            <li>Inserción automática ordenada</li>
            <li>Validación de correlaciones</li>
            <li>Monitoreo continuo</li>
        </ul>
        """,
        "features": [
            "Detección de secuencias",
            "Inserción automática ordenada",
            "Validación de correlaciones",
            "Monitoreo continuo",
            "Reportes de inserción",
            "Interfaz de supervisión"
        ],
        "video_url": ""
    },
    
    "Convertidor": {
        "name": "Convertidor de Formato",
        "subtitle": "Convierte imágenes entre diferentes formatos",
        "category": "Gestión de Imágenes",
        "type": "Herramienta Python",
        "icon": "bi bi-columns",
        "script_id": "Convertidor",
        "long_description": """
        <p>Convertidor versátil que transforma imágenes entre múltiples formatos manteniendo la calidad y optimizando para diferentes usos.</p>
        <p>Capacidades de conversión:</p>
        <ul>
            <li>Múltiples formatos de entrada y salida</li>
            <li>Optimización automática de calidad</li>
            <li>Procesamiento por lotes</li>
            <li>Preservación de metadatos</li>
        </ul>
        """,
        "features": [
            "Soporte para múltiples formatos",
            "Optimización automática",
            "Procesamiento por lotes",
            "Preservación de metadatos",
            "Control de calidad granular",
            "Vista previa de conversiones"
        ],
        "video_url": ""
    },
    
    "RotateImg": {
        "name": "Rotador de Imágenes",
        "subtitle": "Rota imágenes automáticamente",
        "category": "Gestión de Imágenes",
        "type": "Herramienta Python",
        "icon": "bi bi-arrow-counterclockwise",
        "script_id": "RotateImg",
        "long_description": """
        <p>Herramienta especializada en rotar imágenes con precisión, tanto manual como automáticamente basándose en metadatos EXIF.</p>
        <p>Funcionalidades de rotación:</p>
        <ul>
            <li>Rotación automática por EXIF</li>
            <li>Rotación manual en ángulos específicos</li>
            <li>Procesamiento por lotes</li>
            <li>Preservación de calidad</li>
        </ul>
        """,
        "features": [
            "Rotación automática EXIF",
            "Ángulos personalizables",
            "Procesamiento masivo",
            "Preservación de calidad",
            "Vista previa en tiempo real",
            "Corrección de orientación"
        ],
        "video_url": ""
    },
    
    "Multi-Tags-moda-producto": {
        "name": "Asignador de Tags",
        "subtitle": "Asigna tags automáticamente a productos de moda",
        "category": "Gestión de Imágenes",
        "type": "Herramienta Python",
        "icon": "bi bi-postage-heart-fill",
        "script_id": "Multi-Tags-moda-producto",
        "long_description": """
        <p>Sistema inteligente de etiquetado que asigna tags relevantes a productos de moda y otros productos de manera automática.</p>
        <p>Capacidades de etiquetado:</p>
        <ul>
            <li>Reconocimiento automático de categorías</li>
            <li>Tags específicos para moda y productos</li>
            <li>Procesamiento por lotes</li>
            <li>Base de datos de tags actualizable</li>
        </ul>
        """,
        "features": [
            "Etiquetado automático inteligente",
            "Tags específicos por categoría",
            "Procesamiento masivo",
            "Base de datos actualizable",
            "Validación de tags",
            "Reportes de etiquetado"
        ],
        "video_url": ""
    }
}

def generate_video_content(video_url):
    """Genera el contenido del video según si hay URL o no"""
    if video_url and video_url.strip():
        # Si hay URL de video, crear iframe de YouTube
        if "youtube.com/watch?v=" in video_url:
            video_id = video_url.split("watch?v=")[1].split("&")[0]
            return f'<iframe src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
        elif "youtu.be/" in video_url:
            video_id = video_url.split("youtu.be/")[1].split("?")[0]
            return f'<iframe src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
    
    # Placeholder para cuando no hay video
    return '''
    <div class="video-placeholder">
        <i class="bi bi-play-circle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
        <h5>Video próximamente</h5>
        <p class="mb-0">El video demostrativo se agregará pronto</p>
    </div>
    '''

def generate_features_html(features_list):
    """Convierte la lista de características en HTML"""
    return "\n".join([f"<li>{feature}</li>" for feature in features_list])

def get_html_template():
    """Retorna el template HTML completo para las páginas de herramientas."""
    return '''<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="utf-8">
  <meta content="width=device-width, initial-scale=1.0" name="viewport">
  <title>{{TOOL_NAME}} - P&C Suite</title>
  <meta name="description" content="{{TOOL_DESCRIPTION}}">
  <meta name="keywords" content="{{TOOL_KEYWORDS}}">

  <!-- Favicons -->
  <link href="/assets_flexstart/img/favicon.png" rel="icon">
  <link href="/assets_flexstart/img/apple-touch-icon.png" rel="apple-touch-icon">

  <!-- Fonts -->
  <link href="https://fonts.googleapis.com" rel="preconnect">
  <link href="https://fonts.gstatic.com" rel="preconnect" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,100;0,300;0,400;0,500;0,700;0,900;1,100;1,300;1,400;1,500;1,700;1,900&family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&family=Nunito:ital,wght@0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap" rel="stylesheet">

  <!-- Vendor CSS Files -->
  <link href="/assets_flexstart/vendor/bootstrap/css/bootstrap.min.css" rel="stylesheet">
  <link href="/assets_flexstart/vendor/bootstrap-icons/bootstrap-icons.css" rel="stylesheet">
  <link href="/assets_flexstart/vendor/aos/aos.css" rel="stylesheet">
  <link href="/assets_flexstart/vendor/glightbox/css/glightbox.min.css" rel="stylesheet">
  <link href="/assets_flexstart/vendor/swiper/swiper-bundle.min.css" rel="stylesheet">

  <!-- Main CSS File -->
  <link href="/assets_flexstart/css/main.css" rel="stylesheet">

  <!-- Custom CSS for tool pages -->
  <style>
    .tool-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 60px 0 50px;
      margin-top: 60px;
    }

    .tool-content {
      padding: 40px 0;
    }

    .tool-description {
      font-size: 1rem;
      line-height: 1.8;
      margin-bottom: 30px;
    }

    .video-container {
      position: relative;
      width: 100%;
      padding-bottom: 56.25%; /* 16:9 aspect ratio */
      height: 0;
      background: #f8f9fa;
      border-radius: 8px;
      margin-bottom: 30px;
    }

    .video-container iframe {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      border-radius: 8px;
    }

    .video-placeholder {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      color: #6c757d;
    }

    .execute-section {
      background: #f8f9fa;
      padding: 30px;
      border-radius: 10px;
      margin-top: 30px;
    }

    .btn-execute {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border: none;
      padding: 15px 40px;
      font-size: 1.1rem;
      font-weight: 600;
      color: white;
      border-radius: 50px;
      transition: all 0.3s ease;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .btn-execute:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
      color: white;
    }

    .btn-execute:disabled {
      opacity: 0.7;
      transform: none;
    }

    .breadcrumb-custom {
      background: transparent;
      padding: 0;
      margin-bottom: 10px;
    }

    .tool-header h1 {
      margin-bottom: 0.5rem !important;
    }

    .tool-header .lead {
      margin-bottom: 1rem !important;
    }

    .breadcrumb-custom .breadcrumb-item + .breadcrumb-item::before {
      color: rgba(255, 255, 255, 0.7);
    }

    .breadcrumb-custom .breadcrumb-item a {
      color: rgba(255, 255, 255, 0.8);
      text-decoration: none;
    }

    .breadcrumb-custom .breadcrumb-item a:hover {
      color: white;
    }

    .breadcrumb-custom .breadcrumb-item.active {
      color: white;
    }

    .features-list {
      list-style: none;
      padding: 0;
    }

    .features-list li {
      padding: 10px 0;
      border-bottom: 1px solid #e9ecef;
      position: relative;
      padding-left: 30px;
    }

    .features-list li:before {
      content: "✓";
      color: #667eea;
      font-weight: bold;
      position: absolute;
      left: 0;
    }

    .features-list li:last-child {
      border-bottom: none;
    }
  </style>
</head>

<body class="tool-page">

  <header id="header" class="header d-flex align-items-center fixed-top">
    <div class="container-fluid container-xl position-relative d-flex align-items-center">

      <a href="/" class="logo d-flex align-items-center me-auto">
        <img src="/assets_flexstart/img/logo.png" alt="">
        <h1 class="sitename">RIPLEY APPS</h1>
      </a>

      <nav id="navmenu" class="navmenu">
        <ul>
          <li><a href="/#hero">Inicio</a></li>
          <li><a class="btn-getstarted flex-md-shrink-0" href="/reportes" target="_blank">Reportes</a></li>
          <li><a href="/#diseno">Diseño</a></li>
          <li><a href="/#redaccion">Redacción</a></li>
        </ul>
        <i class="mobile-nav-toggle d-xl-none bi bi-list"></i>
      </nav>
    </div>
  </header>

  <main class="main">

    <!-- Tool Header Section -->
    <section class="tool-header">
      <div class="container">
        <!-- Breadcrumb -->
        <nav aria-label="breadcrumb">
          <ol class="breadcrumb breadcrumb-custom">
            <li class="breadcrumb-item"><a href="/">Inicio</a></li>
            <li class="breadcrumb-item"><a href="/#diseno">Diseño</a></li>
            <li class="breadcrumb-item active" aria-current="page">{{TOOL_NAME}}</li>
          </ol>
        </nav>

        <div class="row align-items-center">
          <div class="col-lg-8">
            <h1 class="display-4 mb-3" data-aos="fade-up">{{TOOL_NAME}}</h1>
            <p class="lead mb-4" data-aos="fade-up" data-aos-delay="100">{{TOOL_SUBTITLE}}</p>
            <div class="d-flex align-items-center" data-aos="fade-up" data-aos-delay="200">
              <span class="badge bg-light text-dark me-3">{{TOOL_CATEGORY}}</span>
              <span class="text-light">
                <i class="{{TOOL_ICON}} me-2"></i>{{TOOL_TYPE}}
              </span>
            </div>
          </div>
          <div class="col-lg-4 text-center" data-aos="fade-left" data-aos-delay="300">
            <div class="tool-icon-large">
              <i class="{{TOOL_ICON}}" style="font-size: 4rem; opacity: 0.3;"></i>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Tool Content Section -->
    <section class="tool-content">
      <div class="container">
        <div class="row">
          <div class="col-lg-8">

            <!-- Description -->
            <div class="mb-5" data-aos="fade-up">
              <h2 class="h3 mb-4">¿Qué hace esta herramienta?</h2>
              <div class="tool-description">
                {{TOOL_LONG_DESCRIPTION}}
              </div>
            </div>

            <!-- Features -->
            <div class="mb-5" data-aos="fade-up" data-aos-delay="100">
              <h3 class="h4 mb-4">Características principales:</h3>
              <ul class="features-list">
                {{TOOL_FEATURES}}
              </ul>
            </div>

            <!-- Video Section -->
            <div class="mb-5" data-aos="fade-up" data-aos-delay="200">
              <h3 class="h4 mb-4">Video demostrativo</h3>
              <div class="video-container">
                {{VIDEO_CONTENT}}
              </div>
            </div>

          </div>

          <div class="col-lg-4">

            <!-- Execute Section -->
            <div class="execute-section sticky-top" style="top: 100px;" data-aos="fade-up" data-aos-delay="300">
              <h4 class="mb-3">Descargar herramienta</h4>
              <p class="text-muted mb-4">Haz clic en el botón para descargar esta herramienta como archivo ZIP.</p>

              <div class="d-grid">
                <button class="btn btn-execute" id="downloadBtn" data-script-id="{{SCRIPT_ID}}">
                  <i class="bi bi-download me-2"></i>Descargar {{TOOL_NAME}}
                </button>
              </div>

              <div class="mt-4 text-center">
                <small class="text-muted">
                  <i class="bi bi-info-circle me-1"></i>
                  Se descargará un archivo ZIP con todos los archivos necesarios
                </small>
              </div>
            </div>

            <!-- Quick Info -->
            <div class="mt-4" data-aos="fade-up" data-aos-delay="400">
              <div class="card">
                <div class="card-body">
                  <h6 class="card-title">Información rápida</h6>
                  <ul class="list-unstyled mb-0">
                    <li><strong>Categoría:</strong> {{TOOL_CATEGORY}}</li>
                    <li><strong>Tipo:</strong> {{TOOL_TYPE}}</li>
                    <li><strong>Archivo:</strong> {{SCRIPT_ID}}.py</li>
                  </ul>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>
    </section>

  </main>

  <footer id="footer" class="footer">
    <div class="container copyright text-center mt-4">
      <p>© <span>Copyright</span> <strong class="px-1 sitename">Ripley APP</strong> <span>Todos los derechos reservados</span></p>
      <div class="credits">
        Diseñado por <a href="https://rjresolve.cl/">Rodrigo Jara Duarte</a> y Publicación & contenido.
      </div>
    </div>
  </footer>

  <!-- Scroll Top -->
  <a href="#" id="scroll-top" class="scroll-top d-flex align-items-center justify-content-center"><i class="bi bi-arrow-up-short"></i></a>

  <!-- Vendor JS Files -->
  <script src="/assets_flexstart/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
  <script src="/assets_flexstart/vendor/aos/aos.js"></script>
  <script src="/assets_flexstart/vendor/glightbox/js/glightbox.min.js"></script>

  <!-- Main JS File -->
  <script src="/assets_flexstart/js/main.js"></script>

  <!-- Custom JS for tool download -->
  <script>
    document.addEventListener('DOMContentLoaded', function() {
      const downloadBtn = document.getElementById('downloadBtn');

      if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
          const scriptId = this.dataset.scriptId;

          // Disable button and show spinner
          this.disabled = true;
          const originalContent = this.innerHTML;
          this.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"></div>Preparando descarga...';

          // Trigger download
          const downloadUrl = `/api/download-tool/${scriptId}`;

          fetch(downloadUrl)
            .then(response => {
              if (!response.ok) {
                return response.json().then(err => { throw new Error(err.detail || 'Error al descargar la herramienta.') });
              }
              return response.blob();
            })
            .then(blob => {
              // Create download link
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `${scriptId}.zip`;
              document.body.appendChild(a);
              a.click();
              window.URL.revokeObjectURL(url);
              a.remove();

              // Show success message
              this.innerHTML = '<i class="bi bi-check-circle me-2"></i>¡Descargado!';
              setTimeout(() => {
                this.innerHTML = originalContent;
                this.disabled = false;
              }, 2000);
            })
            .catch(error => {
              console.error('Error al descargar:', error);
              alert(`Error al descargar la herramienta: ${error.message}`);
              this.innerHTML = originalContent;
              this.disabled = false;
            });
        });
      }
    });
  </script>

</body>

</html>'''

def generate_tool_page(tool_id, config):
    """Genera una página HTML para una herramienta específica"""

    # Obtener directorio actual del script
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Obtener template
    template_content = get_html_template()

    # Reemplazar placeholders
    replacements = {
        '{{TOOL_NAME}}': config['name'],
        '{{TOOL_SUBTITLE}}': config['subtitle'],
        '{{TOOL_DESCRIPTION}}': config['subtitle'],
        '{{TOOL_KEYWORDS}}': f"{config['name']}, {config['category']}, herramienta, automatización",
        '{{TOOL_CATEGORY}}': config['category'],
        '{{TOOL_TYPE}}': config['type'],
        '{{TOOL_ICON}}': config['icon'],
        '{{SCRIPT_ID}}': config['script_id'],
        '{{TOOL_LONG_DESCRIPTION}}': config['long_description'],
        '{{TOOL_FEATURES}}': generate_features_html(config['features']),
        '{{VIDEO_CONTENT}}': generate_video_content(config['video_url'])
    }

    # Aplicar reemplazos
    page_content = template_content
    for placeholder, value in replacements.items():
        page_content = page_content.replace(placeholder, value)

    # Guardar página en el directorio actual
    output_path = os.path.join(current_dir, f"{tool_id}.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(page_content)

    print(f"✅ Generada página para {config['name']}: {tool_id}.html")

def generate_all_pages():
    """Genera todas las páginas de herramientas"""
    print("🚀 Generando páginas de herramientas...")
    print("=" * 50)

    for tool_id, config in TOOLS_CONFIG.items():
        try:
            generate_tool_page(tool_id, config)
        except Exception as e:
            print(f"❌ Error generando {tool_id}: {e}")

    print("=" * 50)
    print("✅ Generación completada!")

    # Generar archivo de configuración para futuras actualizaciones
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "tools_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(TOOLS_CONFIG, f, indent=2, ensure_ascii=False)
    print(f"📁 Configuración guardada en: tools_config.json")

if __name__ == "__main__":
    generate_all_pages()