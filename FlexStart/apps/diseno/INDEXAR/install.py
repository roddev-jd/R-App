#!/usr/bin/env python3
"""
Script de instalación automática para el Listador de Carpetas
"""

import subprocess
import sys
import os

def install_requirements():
    """Instalar dependencias desde requirements.txt"""
    print("🔧 Instalando dependencias...")
    
    try:
        # Verificar si pip está disponible
        subprocess.check_call([sys.executable, "-m", "pip", "--version"])
        
        # Instalar dependencias
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        
        print("✅ Dependencias instaladas correctamente!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al instalar dependencias: {e}")
        return False
    except FileNotFoundError:
        print("❌ Error: pip no está disponible")
        return False

def check_python_version():
    """Verificar versión de Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Error: Se requiere Python 3.7 o superior. Versión actual: {version.major}.{version.minor}")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def main():
    """Función principal"""
    print("🚀 Instalador del Listador de Carpetas")
    print("=" * 50)
    
    # Verificar versión de Python
    if not check_python_version():
        sys.exit(1)
    
    # Verificar que requirements.txt existe
    if not os.path.exists("requirements.txt"):
        print("❌ Error: No se encontró el archivo requirements.txt")
        sys.exit(1)
    
    # Instalar dependencias
    if install_requirements():
        print("\n🎉 Instalación completada!")
        print("\nPara ejecutar la aplicación:")
        print("python folder_listing_app.py")
    else:
        print("\n❌ La instalación falló. Revisa los errores anteriores.")
        sys.exit(1)

if __name__ == "__main__":
    main() 