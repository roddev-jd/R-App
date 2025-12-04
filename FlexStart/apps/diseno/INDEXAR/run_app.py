#!/usr/bin/env python3
"""
Script de inicio rápido para el Listador de Carpetas
"""

import sys
import os

def check_dependencies():
    """Verificar que todas las dependencias estén instaladas"""
    try:
        import customtkinter
        import pandas
        import openpyxl
        return True
    except ImportError as e:
        print(f"❌ Error: Falta la dependencia: {e}")
        print("Ejecuta: python3 install.py")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando Listador de Carpetas...")
    
    # Verificar dependencias
    if not check_dependencies():
        sys.exit(1)
    
    # Importar y ejecutar la aplicación
    try:
        from folder_listing_app import FolderListingApp
        
        print("✅ Dependencias verificadas")
        print("🖥️  Abriendo interfaz gráfica...")
        
        app = FolderListingApp()
        app.run()
        
    except Exception as e:
        print(f"❌ Error al iniciar la aplicación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 