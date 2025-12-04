#!/usr/bin/env python3
"""
Test específico para la función corregida sin cache de importaciones
"""

import sys
import os
import pandas as pd
import importlib

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_fixed_function():
    """Test de la función corregida con importación fresca."""
    print("🧪 Test de función corregida (sin cache)...")

    try:
        # Importación fresca forzando reload
        import main_logic
        importlib.reload(main_logic)

        from main_logic import _clear_global_state, _setup_duckdb_connection, df_original, duckdb_conn

        print("✅ Funciones importadas con reload")

        # Test 1: Estado inicial
        print(f"Estado inicial - df_original vacío: {df_original.empty}")
        print(f"Estado inicial - duckdb_conn es None: {duckdb_conn is None}")

        # Test 2: Limpiar estado
        _clear_global_state()
        print("✅ Estado limpiado")

        # Test 3: Crear DataFrame de prueba
        test_df = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'value': ['a', 'b', 'c', 'd', 'e']
        })
        print("✅ DataFrame de prueba creado")

        # Test 4: Configurar DuckDB con función corregida
        _setup_duckdb_connection(test_df)
        print("✅ DuckDB configurado con función corregida")

        # Test 5: Verificar conexión
        # Necesitamos reimportar para obtener el estado actual
        from main_logic import duckdb_conn as current_conn

        if current_conn is not None:
            try:
                result = current_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                print(f"✅ Query exitosa: {result[0]} filas")
                print(f"✅ FUNCIÓN CORREGIDA FUNCIONA CORRECTAMENTE!")
                return True
            except Exception as e:
                print(f"❌ Error en query: {e}")
                return False
        else:
            print("❌ duckdb_conn sigue siendo None - el problema persiste")
            return False

    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal."""
    print("🔧 Test de Función Corregida")
    print("=" * 40)

    result = test_fixed_function()

    print("=" * 40)
    if result:
        print("🎉 ¡FIX EXITOSO!")
        print("La función corregida resuelve el problema.")
        return 0
    else:
        print("❌ El fix no funcionó como esperado")
        return 1

if __name__ == "__main__":
    sys.exit(main())