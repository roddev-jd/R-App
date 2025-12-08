"""
Script para probar la carga completa de C1 PERU y UNIVERSO PERU
simulando lo que hace la aplicación web.
"""
import sys
import os

# Añadir el directorio backend al path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_full_load():
    """Prueba la carga completa de las bases particionadas."""

    print("=" * 80)
    print("TEST DE CARGA COMPLETA - C1 PERU Y UNIVERSO PERU")
    print("=" * 80)

    try:
        # Importar la función de carga
        from main_logic import load_blob_data

        # Casos de prueba
        test_cases = [
            {
                'name': 'C1 PERU',
                'param': 'C1 PERU'
            },
            {
                'name': 'UNIVERSO PERU',
                'param': 'UNIVERSO PERU'
            }
        ]

        for test_case in test_cases:
            print(f"\n{'='*80}")
            print(f"Probando carga de: {test_case['name']}")
            print(f"{'='*80}\n")

            try:
                # Intentar cargar los datos
                result = load_blob_data(
                    param_from_frontend_url=test_case['param'],
                    selected_columns_from_api=None
                )

                print(f"\n[OK] Carga exitosa de {test_case['name']}")
                print(f"     Filas: {result.get('row_count_original', 0):,}")
                print(f"     Columnas: {len(result.get('columns', []))}")
                print(f"     Tipo fuente: {result.get('source_type', 'N/A')}")

                # Mostrar primeras columnas
                columns = result.get('columns', [])
                if columns:
                    print(f"     Primeras 10 columnas: {columns[:10]}")

            except Exception as e:
                print(f"\n[ERROR] Error cargando {test_case['name']}")
                print(f"        Tipo: {type(e).__name__}")
                print(f"        Mensaje: {str(e)}")

                # Mostrar traceback completo
                import traceback
                print("\n--- Traceback completo ---")
                traceback.print_exc()
                print("--- Fin traceback ---\n")

    except Exception as e:
        print(f"\n[ERROR FATAL] {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 80)
    print("TEST COMPLETADO")
    print("=" * 80)
    return True

if __name__ == "__main__":
    test_full_load()
