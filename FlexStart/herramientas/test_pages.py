#!/usr/bin/env python3
"""
Script de prueba para verificar que las páginas se sirven correctamente
"""

import requests
import time

def test_page(page_name, base_url="http://localhost:8000"):
    """Prueba si una página se carga correctamente"""
    url = f"{base_url}/herramientas/{page_name}"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {page_name} - OK (Status: {response.status_code})")
            return True
        else:
            print(f"❌ {page_name} - Error (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {page_name} - Error de conexión: {e}")
        return False

def main():
    print("🧪 Probando páginas de herramientas...")
    print("=" * 50)
    
    # Lista de páginas a probar
    pages = [
        "buscador_diseno.html",
        "RipleyDownloader.html", 
        "Dept.html",
        "Encarpetar.html",
        "Indexar.html",
        "Scrapper.html",
        "miniaturas_diseno.html",
        "Compresor.html"
    ]
    
    success_count = 0
    total_pages = len(pages)
    
    print("📋 Probando páginas:")
    for page in pages:
        if test_page(page):
            success_count += 1
        time.sleep(0.5)  # Pequeña pausa entre requests
    
    print("=" * 50)
    print(f"📊 Resultados: {success_count}/{total_pages} páginas funcionando")
    
    if success_count == total_pages:
        print("🎉 ¡Todas las páginas están funcionando correctamente!")
    else:
        print("⚠️  Algunas páginas tienen problemas. Verifica que el servidor esté ejecutándose.")
        print("💡 Ejecuta: python3 lanzador.py")

if __name__ == "__main__":
    main()