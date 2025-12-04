#!/usr/bin/env python3
"""
Test simple para diagnosticar el problema específico de DuckDB
"""

import sys
import os
import pandas as pd

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_basic_duckdb_flow():
    """Test del flujo básico sin usar las funciones del sistema."""
    print("🧪 Test básico de DuckDB...")

    try:
        import duckdb
        print("✅ DuckDB importado correctamente")

        # Test 1: Conexión básica
        conn = duckdb.connect(':memory:')
        print("✅ Conexión DuckDB creada")

        # Test 2: DataFrame básico
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['a', 'b', 'c']
        })
        print("✅ DataFrame creado")

        # Test 3: Registrar DataFrame
        conn.register('test_df', df)
        print("✅ DataFrame registrado")

        # Test 4: Crear tabla
        conn.execute("CREATE TABLE test_table AS SELECT * FROM test_df")
        print("✅ Tabla creada")

        # Test 5: Query básica
        result = conn.execute("SELECT COUNT(*) FROM test_table").fetchone()
        print(f"✅ Query ejecutada: {result[0]} filas")

        # Test 6: Cerrar conexión
        conn.close()
        print("✅ Conexión cerrada")

        return True

    except Exception as e:
        print(f"❌ Error en test básico: {e}")
        return False

def test_main_logic_functions():
    """Test de las funciones específicas de main_logic."""
    print("\n🧪 Test de funciones main_logic...")

    try:
        from main_logic import _clear_global_state, _setup_duckdb_connection, df_original, duckdb_conn

        print("✅ Funciones importadas correctamente")

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

        # Test 4: Configurar DuckDB
        _setup_duckdb_connection(test_df)
        print("✅ DuckDB configurado")

        # Test 5: Verificar conexión
        if duckdb_conn is not None:
            try:
                result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                print(f"✅ Query exitosa: {result[0]} filas")
                return True
            except Exception as e:
                print(f"❌ Error en query: {e}")
                return False
        else:
            print("❌ duckdb_conn es None después de configuración")
            return False

    except Exception as e:
        print(f"❌ Error en test de main_logic: {e}")
        return False

def test_with_stability_patches():
    """Test con los parches de estabilidad aplicados."""
    print("\n🧪 Test con parches de estabilidad...")

    try:
        from database_stability_fixes import apply_stability_patches, improved_setup_duckdb_connection, improved_clear_global_state

        print("✅ Parches importados correctamente")

        # Aplicar parches
        apply_stability_patches()
        print("✅ Parches aplicados")

        # Test 1: Limpiar con versión mejorada
        improved_clear_global_state()
        print("✅ Estado limpiado con versión mejorada")

        # Test 2: DataFrame de prueba
        test_df = pd.DataFrame({
            'id': range(10),
            'data': [f'item_{i}' for i in range(10)]
        })
        print("✅ DataFrame de prueba creado")

        # Test 3: Configurar con versión mejorada
        success = improved_setup_duckdb_connection(test_df)
        print(f"✅ Configuración mejorada: {success}")

        if success:
            # Verificar que funciona
            from main_logic import duckdb_conn
            if duckdb_conn:
                try:
                    result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                    print(f"✅ Verificación exitosa: {result[0]} filas")
                    return True
                except Exception as e:
                    print(f"❌ Error en verificación: {e}")
                    return False
            else:
                print("❌ duckdb_conn sigue siendo None")
                return False
        else:
            print("❌ Configuración mejorada falló")
            return False

    except Exception as e:
        print(f"❌ Error con parches: {e}")
        return False

def main():
    """Función principal."""
    print("🚀 Diagnóstico Simple de DuckDB")
    print("=" * 50)

    results = []

    # Test 1: DuckDB básico
    basic_result = test_basic_duckdb_flow()
    results.append(("DuckDB Básico", basic_result))

    # Test 2: Funciones main_logic
    main_logic_result = test_main_logic_functions()
    results.append(("Main Logic", main_logic_result))

    # Test 3: Con parches
    patches_result = test_with_stability_patches()
    results.append(("Con Parches", patches_result))

    # Resumen
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE TESTS SIMPLES")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"   {status} - {test_name}")
        if result:
            passed += 1

    print(f"\n📈 Resultado: {passed}/{len(results)} tests pasados")

    if passed == len(results):
        print("🎉 ¡Todos los tests pasaron!")
        return 0
    else:
        print("⚠️ Algunos tests fallaron - revisar logs arriba")
        return 1

if __name__ == "__main__":
    sys.exit(main())