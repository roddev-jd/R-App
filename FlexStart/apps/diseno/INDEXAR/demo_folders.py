#!/usr/bin/env python3
"""
Script de demostración para crear carpetas de ejemplo
"""

import os
import tempfile
import shutil

def create_demo_folders():
    """Crear carpetas de demostración"""
    # Crear directorio temporal para la demostración
    demo_dir = os.path.join(os.getcwd(), "demo_folders")
    
    # Limpiar si ya existe
    if os.path.exists(demo_dir):
        shutil.rmtree(demo_dir)
    
    # Crear directorio
    os.makedirs(demo_dir)
    
    # Lista de carpetas de ejemplo
    demo_folders = [
        "Producto001",
        "Producto002",
        "ProductoABC",
        "Producto123",
        "Carpeta_Sin_Numeros",
        "Producto456",
        "Producto789",
        "ProductoXYZ",
        "Producto100",
        "Producto200"
    ]
    
    print(f"📁 Creando carpetas de demostración en: {demo_dir}")
    
    # Crear las carpetas
    for folder in demo_folders:
        folder_path = os.path.join(demo_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        print(f"  ✅ Creada: {folder}")
    
    print(f"\n🎉 Se crearon {len(demo_folders)} carpetas de demostración")
    print(f"📍 Ubicación: {demo_dir}")
    print("\n💡 Ahora puedes usar la aplicación para listar estas carpetas")
    
    return demo_dir

def main():
    """Función principal"""
    print("🚀 Creando carpetas de demostración...")
    print("=" * 50)
    
    try:
        demo_dir = create_demo_folders()
        
        print("\n📋 Instrucciones:")
        print("1. Ejecuta: python3 folder_listing_app.py")
        print("2. Selecciona el directorio: demo_folders")
        print("3. Haz clic en 'Generar Lista de Carpetas'")
        print("4. Revisa el archivo Excel generado")
        
    except Exception as e:
        print(f"❌ Error al crear carpetas de demostración: {e}")

if __name__ == "__main__":
    main() 