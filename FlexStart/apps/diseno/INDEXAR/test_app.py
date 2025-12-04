#!/usr/bin/env python3
"""
Script de prueba para el Listador de Carpetas
"""

import os
import tempfile
import pandas as pd
from folder_listing_app import FolderListingApp

def create_test_directories():
    """Crear directorios de prueba"""
    test_dir = tempfile.mkdtemp(prefix="test_folders_")
    
    # Crear carpetas de prueba
    test_folders = [
        "Producto001",
        "Producto002", 
        "ProductoABC",
        "Producto123",
        "Carpeta_Sin_Numeros",
        "Producto456"
    ]
    
    for folder in test_folders:
        folder_path = os.path.join(test_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
    
    return test_dir, test_folders

def test_folder_listing():
    """Probar la funcionalidad de listado de carpetas"""
    print("🧪 Iniciando pruebas...")
    
    # Crear directorios de prueba
    test_dir, expected_folders = create_test_directories()
    print(f"📁 Directorio de prueba creado: {test_dir}")
    
    try:
        # Crear instancia de la aplicación
        app = FolderListingApp()
        
        # Probar obtención de carpetas
        folders = app.get_folders_from_directory(test_dir)
        print(f"📋 Carpetas encontradas: {folders}")
        
        # Verificar que se encontraron todas las carpetas esperadas
        if set(folders) == set(expected_folders):
            print("✅ Listado de carpetas correcto")
        else:
            print("❌ Error en listado de carpetas")
            print(f"Esperado: {expected_folders}")
            print(f"Encontrado: {folders}")
            return False
        
        # Probar creación de DataFrame
        df = app.create_dataframe(folders)
        print(f"📊 DataFrame creado con {len(df)} filas")
        print(f"Columnas: {list(df.columns)}")
        
        # Verificar estructura del DataFrame
        if 'SKU' in df.columns and len(df.columns) == 1:
            print("✅ Estructura del DataFrame correcta")
        else:
            print("❌ Error en estructura del DataFrame")
            print(f"Columnas encontradas: {list(df.columns)}")
            return False
        
        # Probar guardado de Excel
        output_path = app.save_excel_file(test_dir, df)
        print(f"💾 Archivo Excel guardado: {output_path}")
        
        # Verificar que el archivo existe
        if os.path.exists(output_path):
            print("✅ Archivo Excel creado correctamente")
            
            # Verificar contenido del Excel
            df_read = pd.read_excel(output_path)
            if len(df_read) == len(df):
                print("✅ Contenido del Excel correcto")
            else:
                print("❌ Error en contenido del Excel")
                return False
        else:
            print("❌ Error al crear archivo Excel")
            return False
        
        print("🎉 Todas las pruebas pasaron exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
        return False
        
    finally:
        # Limpiar archivos de prueba
        try:
            import shutil
            shutil.rmtree(test_dir)
            print("🧹 Archivos de prueba eliminados")
        except:
            pass

def test_dependencies():
    """Probar que todas las dependencias están disponibles"""
    print("🔍 Verificando dependencias...")
    
    try:
        import customtkinter as ctk
        print("✅ CustomTkinter disponible")
    except ImportError:
        print("❌ CustomTkinter no disponible")
        return False
    
    try:
        import pandas as pd
        print("✅ Pandas disponible")
    except ImportError:
        print("❌ Pandas no disponible")
        return False
    
    try:
        import openpyxl
        print("✅ OpenPyXL disponible")
    except ImportError:
        print("❌ OpenPyXL no disponible")
        return False
    
    return True

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas del Listador de Carpetas")
    print("=" * 50)
    
    # Probar dependencias
    if not test_dependencies():
        print("\n❌ Faltan dependencias. Ejecuta: pip install -r requirements.txt")
        return
    
    # Probar funcionalidad
    if test_folder_listing():
        print("\n🎉 Todas las pruebas completadas exitosamente!")
        print("La aplicación está lista para usar.")
    else:
        print("\n❌ Algunas pruebas fallaron.")
        print("Revisa los errores anteriores.")

if __name__ == "__main__":
    main() 