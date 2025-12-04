#!/usr/bin/env python3
"""
Script para actualizar videos de YouTube en páginas de herramientas
Uso: python3 update_video.py <tool_id> <youtube_url>
"""

import sys
import json
import os
from generate_tool_pages import TOOLS_CONFIG, generate_tool_page

def update_tool_video(tool_id, youtube_url):
    """Actualiza el video de una herramienta específica"""
    
    if tool_id not in TOOLS_CONFIG:
        print(f"❌ Herramienta '{tool_id}' no encontrada.")
        print(f"Herramientas disponibles: {', '.join(TOOLS_CONFIG.keys())}")
        return
    
    # Actualizar la configuración
    TOOLS_CONFIG[tool_id]['video_url'] = youtube_url
    
    # Regenerar la página
    generate_tool_page(tool_id, TOOLS_CONFIG[tool_id])
    
    # Guardar configuración actualizada
    config_path = "/Users/rjarad/Desktop/tools/App_SUITE/SUITEV1.4.1/FlexStart/herramientas/tools_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(TOOLS_CONFIG, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Video actualizado para {TOOLS_CONFIG[tool_id]['name']}")
    print(f"📹 URL: {youtube_url}")

def main():
    if len(sys.argv) != 3:
        print("Uso: python3 update_video.py <tool_id> <youtube_url>")
        print("\nEjemplo:")
        print("python3 update_video.py buscador_diseno https://youtube.com/watch?v=ABC123")
        print("\nHerramientas disponibles:")
        for tool_id, config in TOOLS_CONFIG.items():
            print(f"  - {tool_id}: {config['name']}")
        return
    
    tool_id = sys.argv[1]
    youtube_url = sys.argv[2]
    
    update_tool_video(tool_id, youtube_url)

if __name__ == "__main__":
    main()