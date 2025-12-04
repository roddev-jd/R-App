"""
Test Runner para Diagnóstico Rápido de Problemas de Base de Datos

Este script permite ejecutar tests específicos de manera rápida para diagnosticar
los problemas esporádicos de carga de bases de datos.
"""

import os
import sys
import logging
import time
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Agregar directorios al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

class DatabaseLoadingDiagnostic:
    """Clase para ejecutar diagnósticos de carga de base de datos."""

    def __init__(self):
        self.results = {}

    def test_basic_functionality(self):
        """Test básico de funcionalidad."""
        logging.info("🧪 Ejecutando test básico de funcionalidad...")

        try:
            from main_logic import _clear_global_state, df_original, duckdb_conn

            # Test 1: Estado inicial limpio
            _clear_global_state()

            if df_original.empty:
                logging.info("✅ Estado inicial limpio - DataFrame vacío")
                self.results['initial_state_clean'] = True
            else:
                logging.warning("⚠️ Estado inicial no limpio - DataFrame contiene datos")
                self.results['initial_state_clean'] = False

            if duckdb_conn is None:
                logging.info("✅ Estado inicial limpio - Conexión DuckDB es None")
                self.results['initial_connection_clean'] = True
            else:
                logging.warning("⚠️ Estado inicial no limpio - Conexión DuckDB existe")
                self.results['initial_connection_clean'] = False

            return True

        except Exception as e:
            logging.error(f"❌ Error en test básico: {e}")
            self.results['basic_test_error'] = str(e)
            return False

    def test_duckdb_connection_stability(self):
        """Test de estabilidad de conexión DuckDB."""
        logging.info("🧪 Ejecutando test de estabilidad de conexión DuckDB...")

        try:
            import duckdb
            import pandas as pd
            from main_logic import _setup_duckdb_connection, _clear_global_state, duckdb_conn

            # Crear DataFrame de prueba
            test_df = pd.DataFrame({
                'id': range(100),
                'categoria': [f'cat_{i % 5}' for i in range(100)],
                'valor': [i * 1.5 for i in range(100)]
            })

            success_count = 0
            error_count = 0

            # Realizar múltiples configuraciones
            for i in range(5):
                try:
                    _clear_global_state()
                    _setup_duckdb_connection(test_df)

                    if duckdb_conn is not None:
                        result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                        if result and result[0] == len(test_df):
                            success_count += 1
                            logging.info(f"✅ Intento {i+1}: Éxito - {result[0]} filas")
                        else:
                            error_count += 1
                            logging.warning(f"⚠️ Intento {i+1}: Resultado incorrecto - {result}")
                    else:
                        error_count += 1
                        logging.warning(f"⚠️ Intento {i+1}: Conexión es None")

                except Exception as e:
                    error_count += 1
                    logging.error(f"❌ Intento {i+1}: Error - {e}")

                # Pequeña pausa entre intentos
                time.sleep(0.1)

            success_rate = success_count / (success_count + error_count)
            logging.info(f"📊 Tasa de éxito: {success_rate:.1%} ({success_count}/{success_count + error_count})")

            self.results['duckdb_success_rate'] = success_rate
            self.results['duckdb_success_count'] = success_count
            self.results['duckdb_error_count'] = error_count

            return success_rate > 0.8  # 80% de éxito mínimo

        except ImportError:
            logging.warning("⚠️ DuckDB no disponible - saltando test")
            self.results['duckdb_not_available'] = True
            return True
        except Exception as e:
            logging.error(f"❌ Error en test de estabilidad DuckDB: {e}")
            self.results['duckdb_test_error'] = str(e)
            return False

    def test_concurrent_access(self):
        """Test de acceso concurrente."""
        logging.info("🧪 Ejecutando test de acceso concurrente...")

        try:
            import threading
            import pandas as pd
            from main_logic import _setup_duckdb_connection, _clear_global_state, duckdb_conn

            test_df = pd.DataFrame({
                'id': range(50),
                'data': [f'item_{i}' for i in range(50)]
            })

            results = []
            errors = []

            def worker(worker_id):
                try:
                    time.sleep(0.01 * worker_id)  # Pequeño offset

                    _clear_global_state()

                    try:
                        import duckdb
                        _setup_duckdb_connection(test_df)

                        if duckdb_conn:
                            result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                            results.append((worker_id, result[0] if result else 0))
                        else:
                            results.append((worker_id, None))

                    except ImportError:
                        results.append((worker_id, "duckdb_not_available"))

                except Exception as e:
                    errors.append((worker_id, str(e)))

            # Ejecutar workers
            threads = []
            for i in range(3):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            logging.info(f"📊 Resultados concurrentes: {results}")
            if errors:
                logging.warning(f"⚠️ Errores concurrentes: {errors}")

            self.results['concurrent_results'] = results
            self.results['concurrent_errors'] = errors

            # Verificar que al menos algunos workers fueron exitosos
            successful_results = [r for r in results if isinstance(r[1], int) and r[1] > 0]
            return len(successful_results) >= 1

        except Exception as e:
            logging.error(f"❌ Error en test de concurrencia: {e}")
            self.results['concurrent_test_error'] = str(e)
            return False

    def test_error_recovery(self):
        """Test de recuperación de errores."""
        logging.info("🧪 Ejecutando test de recuperación de errores...")

        try:
            import pandas as pd
            from main_logic import _setup_duckdb_connection, _clear_global_state, duckdb_conn

            test_df = pd.DataFrame({'id': range(10), 'value': range(10)})

            # Test 1: Configuración normal
            _clear_global_state()

            try:
                import duckdb
                _setup_duckdb_connection(test_df)

                if duckdb_conn:
                    initial_result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                    logging.info(f"✅ Configuración inicial exitosa: {initial_result[0]} filas")

                    # Test 2: Simular error y recuperación
                    try:
                        # Forzar cierre de conexión (simular error)
                        duckdb_conn.close()

                        # Intentar recuperación
                        _clear_global_state()
                        _setup_duckdb_connection(test_df)

                        if duckdb_conn:
                            recovery_result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                            logging.info(f"✅ Recuperación exitosa: {recovery_result[0]} filas")
                            self.results['error_recovery_success'] = True
                            return True
                        else:
                            logging.warning("⚠️ Falló la recuperación - conexión es None")
                            self.results['error_recovery_success'] = False
                            return False

                    except Exception as recovery_error:
                        logging.error(f"❌ Error en recuperación: {recovery_error}")
                        self.results['recovery_error'] = str(recovery_error)
                        return False

                else:
                    logging.warning("⚠️ Configuración inicial falló - conexión es None")
                    self.results['initial_setup_failed'] = True
                    return False

            except ImportError:
                logging.warning("⚠️ DuckDB no disponible - saltando test de recuperación")
                self.results['duckdb_not_available_recovery'] = True
                return True

        except Exception as e:
            logging.error(f"❌ Error en test de recuperación: {e}")
            self.results['recovery_test_error'] = str(e)
            return False

    def run_all_tests(self):
        """Ejecutar todos los tests de diagnóstico."""
        logging.info("🚀 Iniciando diagnóstico completo de carga de base de datos")
        logging.info("=" * 60)

        start_time = time.time()
        test_results = {}

        # Ejecutar tests
        tests = [
            ("Funcionalidad Básica", self.test_basic_functionality),
            ("Estabilidad DuckDB", self.test_duckdb_connection_stability),
            ("Acceso Concurrente", self.test_concurrent_access),
            ("Recuperación de Errores", self.test_error_recovery),
        ]

        for test_name, test_func in tests:
            logging.info(f"\n🧪 Ejecutando: {test_name}")
            try:
                result = test_func()
                test_results[test_name] = result
                status = "✅ PASÓ" if result else "❌ FALLÓ"
                logging.info(f"   {status}")
            except Exception as e:
                test_results[test_name] = False
                logging.error(f"   ❌ ERROR: {e}")

        # Resumen
        total_time = time.time() - start_time
        passed = sum(1 for result in test_results.values() if result)
        total = len(test_results)

        logging.info("\n" + "=" * 60)
        logging.info("📊 RESUMEN DE DIAGNÓSTICO")
        logging.info(f"   Tiempo total: {total_time:.2f}s")
        logging.info(f"   Tests pasados: {passed}/{total}")

        for test_name, result in test_results.items():
            status = "✅" if result else "❌"
            logging.info(f"   {status} {test_name}")

        if passed == total:
            logging.info("\n🎉 TODOS LOS TESTS PASARON - Sistema estable")
        else:
            logging.warning(f"\n⚠️ {total - passed} TESTS FALLARON - Revisar problemas")

        # Mostrar detalles de resultados si hay problemas
        if self.results and passed < total:
            logging.info("\n📋 DETALLES DE RESULTADOS:")
            for key, value in self.results.items():
                logging.info(f"   {key}: {value}")

        return test_results

def main():
    """Función principal para ejecutar diagnóstico."""
    diagnostic = DatabaseLoadingDiagnostic()
    results = diagnostic.run_all_tests()

    # Retornar código de salida apropiado
    all_passed = all(results.values())
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())