"""
Test Suite para Diagnóstico de Problemas de Carga de Bases de Datos

Este conjunto de tests está diseñado para identificar y diagnosticar los problemas
esporádicos de carga de bases de datos que experimentan algunos usuarios.

Problemas identificados para testear:
1. Variables globales sin sincronización (duckdb_conn, df_original)
2. Manejo inconsistente de conexiones DuckDB
3. Condiciones de carrera en ThreadPoolExecutor
4. Falta de validación robusta de estado antes de consultas
5. Manejo de excepciones incompleto en operaciones críticas
"""

import asyncio
import concurrent.futures
import os
import pandas as pd
import pytest
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock

# Agregar el directorio backend al path para importar módulos locales
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

# Importar módulos a testear
from main_logic import (
    _setup_duckdb_connection,
    _clear_global_state,
    load_blob_data,
    apply_filters_to_data,
    df_original,
    duckdb_conn
)

class TestDatabaseLoadingStability:
    """Suite de tests para estabilidad de carga de bases de datos."""

    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self):
        """Setup y cleanup para cada test."""
        # Cleanup antes del test
        _clear_global_state()
        yield
        # Cleanup después del test
        _clear_global_state()

    def create_test_dataframe(self, rows: int = 1000) -> pd.DataFrame:
        """Crea un DataFrame de prueba con datos sintéticos."""
        return pd.DataFrame({
            'id': range(rows),
            'categoria': [f'cat_{i % 10}' for i in range(rows)],
            'valor': [i * 1.5 for i in range(rows)],
            'descripcion': [f'item_{i}' for i in range(rows)]
        })

class TestDuckDBConnectionStability(TestDatabaseLoadingStability):
    """Tests específicos para estabilidad de conexiones DuckDB."""

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB no disponible")
    def test_duckdb_connection_creation_and_cleanup(self):
        """Test: Verificar que las conexiones DuckDB se crean y cierran correctamente."""
        df_test = self.create_test_dataframe()

        # Verificar estado inicial limpio
        assert duckdb_conn is None, "La conexión DuckDB debería estar limpia inicialmente"

        # Configurar conexión
        _setup_duckdb_connection(df_test)

        # Verificar que la conexión se creó correctamente
        assert duckdb_conn is not None, "La conexión DuckDB debería haberse creado"

        # Verificar que los datos están disponibles
        result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
        assert result[0] == len(df_test), f"Esperado {len(df_test)} filas, obtenido {result[0]}"

        # Limpiar estado
        _clear_global_state()

        # Verificar limpieza
        assert duckdb_conn is None, "La conexión DuckDB debería haberse cerrado"

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB no disponible")
    def test_duckdb_connection_race_condition(self):
        """Test: Detectar condiciones de carrera en configuración de DuckDB."""
        df_test = self.create_test_dataframe(500)
        results = []
        errors = []

        def setup_connection_worker(worker_id: int):
            """Worker function para test concurrente."""
            try:
                time.sleep(0.01 * worker_id)  # Escalar el delay
                _setup_duckdb_connection(df_test)

                # Verificar que la conexión funciona
                if duckdb_conn:
                    result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                    results.append((worker_id, result[0] if result else 0))
                else:
                    results.append((worker_id, None))

            except Exception as e:
                errors.append((worker_id, str(e)))

        # Ejecutar múltiples workers concurrentemente
        threads = []
        for i in range(5):
            thread = threading.Thread(target=setup_connection_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Esperar a que terminen todos los threads
        for thread in threads:
            thread.join()

        # Evaluar resultados
        print(f"Resultados: {results}")
        print(f"Errores: {errors}")

        # Al menos uno debería haber tenido éxito
        successful_results = [r for r in results if r[1] == len(df_test)]
        assert len(successful_results) > 0, "Al menos una configuración debería haber sido exitosa"

        # No deberían haber errores críticos
        critical_errors = [e for e in errors if 'database is locked' in e[1].lower() or 'connection' in e[1].lower()]
        assert len(critical_errors) == 0, f"Errores críticos detectados: {critical_errors}"

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB no disponible")
    def test_duckdb_connection_memory_leaks(self):
        """Test: Detectar posibles memory leaks en conexiones DuckDB."""
        import gc

        initial_objects = len(gc.get_objects())
        df_test = self.create_test_dataframe(100)

        # Crear y destruir conexiones múltiples veces
        for i in range(10):
            _setup_duckdb_connection(df_test)

            # Verificar que funciona
            if duckdb_conn:
                result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                assert result[0] == len(df_test)

            _clear_global_state()

        # Forzar garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())

        # Verificar que no hay un crecimiento excesivo de objetos
        object_growth = final_objects - initial_objects
        assert object_growth < 100, f"Posible memory leak detectado: {object_growth} objetos adicionales"

class TestGlobalStateManagement(TestDatabaseLoadingStability):
    """Tests para manejo del estado global."""

    def test_global_state_thread_safety(self):
        """Test: Verificar thread-safety del estado global."""
        df_test = self.create_test_dataframe(100)
        results = []
        errors = []

        def state_manipulation_worker(worker_id: int):
            """Worker que manipula el estado global."""
            try:
                # Simular carga de datos
                global df_original
                time.sleep(0.01 * worker_id)

                # Limpiar estado
                _clear_global_state()

                # Configurar nuevo estado
                if DUCKDB_AVAILABLE:
                    _setup_duckdb_connection(df_test)

                # Verificar estado
                if df_original is not None and len(df_original) > 0:
                    results.append((worker_id, "success", len(df_original)))
                else:
                    results.append((worker_id, "empty_dataframe", 0))

            except Exception as e:
                errors.append((worker_id, str(e)))

        # Ejecutar workers concurrentemente
        threads = []
        for i in range(3):
            thread = threading.Thread(target=state_manipulation_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        print(f"Resultados de estado global: {results}")
        print(f"Errores de estado global: {errors}")

        # Verificar que no hay errores críticos
        assert len(errors) == 0, f"Errores en manejo de estado global: {errors}"

    def test_state_consistency_after_operations(self):
        """Test: Verificar consistencia del estado después de operaciones."""
        df_test = self.create_test_dataframe(50)

        # Estado inicial limpio
        _clear_global_state()
        assert df_original.empty, "DataFrame original debería estar vacío inicialmente"

        # Configurar estado
        if DUCKDB_AVAILABLE:
            _setup_duckdb_connection(df_test)

        # Simular operación que podría corromper el estado
        try:
            # Operación que podría fallar
            if DUCKDB_AVAILABLE and duckdb_conn:
                result = duckdb_conn.execute("SELECT * FROM data LIMIT 10").fetchdf()
                assert len(result) <= 10, "Query limitada debería retornar máximo 10 filas"
        except Exception as e:
            print(f"Error esperado en operación: {e}")

        # Verificar que el estado sigue siendo consistente
        if DUCKDB_AVAILABLE and duckdb_conn:
            count_result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
            assert count_result[0] == len(df_test), "El estado debería mantenerse consistente"

class TestLoadBlobDataResilience(TestDatabaseLoadingStability):
    """Tests para resistencia de la función load_blob_data."""

    @patch('main_logic.config_data')
    @patch('main_logic.persistent_cache')
    def test_load_blob_data_with_invalid_config(self, mock_cache, mock_config):
        """Test: Comportamiento de load_blob_data con configuración inválida."""
        # Configurar mocks para simular configuración inválida
        mock_config.get.return_value = None
        mock_cache.has_cached_data.return_value = False

        # Intentar cargar datos con configuración inválida
        with pytest.raises((KeyError, AttributeError, ValueError)) as exc_info:
            load_blob_data("test_blob_invalid")

        print(f"Error esperado capturado: {exc_info.value}")

        # Verificar que el estado global sigue limpio después del error
        assert df_original.empty, "DataFrame debería estar vacío después de error"
        assert duckdb_conn is None, "Conexión DuckDB debería ser None después de error"

    @patch('main_logic.persistent_cache')
    def test_load_blob_data_cache_corruption(self, mock_cache):
        """Test: Manejo de corrupción de caché."""
        # Simular caché corrupto
        mock_cache.has_cached_data.return_value = True
        mock_cache.load_cached_data.return_value = None  # Datos corruptos

        # Intentar cargar desde caché corrupto
        result = load_blob_data("test_blob_corrupted")

        # Debería manejar gracefully la corrupción de caché
        assert result is None or isinstance(result, dict), "Debería manejar caché corrupto sin crashear"

class TestErrorRecoveryMechanisms(TestDatabaseLoadingStability):
    """Tests para mecanismos de recuperación de errores."""

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB no disponible")
    def test_recovery_after_duckdb_connection_failure(self):
        """Test: Recuperación después de falla de conexión DuckDB."""
        df_test = self.create_test_dataframe(100)

        # Crear conexión inicial exitosa
        _setup_duckdb_connection(df_test)
        initial_count = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]
        assert initial_count == len(df_test)

        # Simular falla de conexión
        if duckdb_conn:
            duckdb_conn.close()

        # Intentar recuperar
        _clear_global_state()
        _setup_duckdb_connection(df_test)

        # Verificar recuperación exitosa
        if duckdb_conn:
            recovered_count = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]
            assert recovered_count == len(df_test), "Debería recuperarse exitosamente después de falla"

    def test_concurrent_operations_resilience(self):
        """Test: Resistencia a operaciones concurrentes."""
        df_test = self.create_test_dataframe(200)
        success_count = 0
        error_count = 0

        def concurrent_operation(worker_id: int):
            nonlocal success_count, error_count
            try:
                time.sleep(0.01 * worker_id)

                # Operación de limpieza y configuración
                _clear_global_state()

                if DUCKDB_AVAILABLE:
                    _setup_duckdb_connection(df_test)

                    if duckdb_conn:
                        result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                        if result and result[0] == len(df_test):
                            success_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1
                else:
                    success_count += 1  # Skip si DuckDB no está disponible

            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
                error_count += 1

        # Ejecutar operaciones concurrentes
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(concurrent_operation, i) for i in range(5)]
            concurrent.futures.wait(futures)

        print(f"Operaciones exitosas: {success_count}, Errores: {error_count}")

        # Al menos alguna operación debería ser exitosa
        assert success_count > 0, "Al menos una operación concurrente debería ser exitosa"

        # La mayoría de operaciones deberían ser exitosas
        success_rate = success_count / (success_count + error_count)
        assert success_rate >= 0.6, f"Tasa de éxito muy baja: {success_rate:.2%}"

class TestPerformanceAndStability(TestDatabaseLoadingStability):
    """Tests de rendimiento y estabilidad bajo carga."""

    @pytest.mark.skipif(not DUCKDB_AVAILABLE, reason="DuckDB no disponible")
    def test_large_dataset_stability(self):
        """Test: Estabilidad con datasets grandes."""
        # Crear dataset más grande para simular carga real
        large_df = self.create_test_dataframe(10000)

        start_time = time.time()
        _setup_duckdb_connection(large_df)
        setup_time = time.time() - start_time

        print(f"Tiempo de configuración para 10K filas: {setup_time:.3f}s")

        # Verificar que la configuración fue exitosa
        if duckdb_conn:
            count_result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
            assert count_result[0] == len(large_df), "Dataset grande debería cargarse completamente"

            # Test de consulta
            query_start = time.time()
            sample_result = duckdb_conn.execute("SELECT * FROM data LIMIT 100").fetchdf()
            query_time = time.time() - query_start

            print(f"Tiempo de consulta para muestra: {query_time:.3f}s")
            assert len(sample_result) == 100, "Query de muestra debería retornar 100 filas"

        # Verificar que el sistema sigue estable después de la carga
        assert setup_time < 5.0, "Configuración no debería tomar más de 5 segundos"

    def test_repeated_operations_stability(self):
        """Test: Estabilidad en operaciones repetidas."""
        df_test = self.create_test_dataframe(500)
        operation_times = []

        # Realizar múltiples operaciones
        for i in range(10):
            start_time = time.time()

            _clear_global_state()
            if DUCKDB_AVAILABLE:
                _setup_duckdb_connection(df_test)

                if duckdb_conn:
                    result = duckdb_conn.execute("SELECT COUNT(*) FROM data").fetchone()
                    assert result[0] == len(df_test)

            operation_time = time.time() - start_time
            operation_times.append(operation_time)

        # Analizar estabilidad de rendimiento
        avg_time = sum(operation_times) / len(operation_times)
        max_time = max(operation_times)
        min_time = min(operation_times)

        print(f"Tiempos de operación - Promedio: {avg_time:.3f}s, Min: {min_time:.3f}s, Max: {max_time:.3f}s")

        # Verificar que no hay degradación significativa
        assert max_time < avg_time * 3, "Tiempo máximo no debería ser más del triple del promedio"
        assert avg_time < 1.0, "Tiempo promedio debería ser menor a 1 segundo"

# Función de utilidad para ejecutar todos los tests
def run_database_loading_tests():
    """Ejecutar todos los tests de carga de base de datos."""
    import subprocess
    import sys

    # Ejecutar pytest con este archivo
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--tb=short",
        "--capture=no"
    ], capture_output=True, text=True)

    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
    print(f"Return code: {result.returncode}")

    return result.returncode == 0

if __name__ == "__main__":
    print("🧪 Ejecutando Tests de Diagnóstico de Carga de Base de Datos")
    print("=" * 60)

    # Verificar dependencias
    print(f"DuckDB disponible: {DUCKDB_AVAILABLE}")

    # Ejecutar tests
    success = run_database_loading_tests()

    if success:
        print("✅ Todos los tests pasaron exitosamente")
    else:
        print("❌ Algunos tests fallaron - revisar output para detalles")