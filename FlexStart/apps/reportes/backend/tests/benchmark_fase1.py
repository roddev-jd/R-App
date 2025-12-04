#!/usr/bin/env python3
"""
Script de Benchmarking - Fase 1 de Optimización
===============================================

Mide el rendimiento y consumo de memoria de las optimizaciones implementadas:
- Hito 1.1: Conversión selectiva a string
- Hito 1.2: Caché de fuentes de enriquecimiento
- Hito 1.3: Generación paralela de opciones de filtro
- Hito 1.4: Bases cacheables expandidas + detección Azure

Uso:
    python benchmark_fase1.py

Requisitos:
    - Backend de reportes debe estar accesible
    - Configuración de Azure/SharePoint debe estar configurada
    - psutil debe estar instalado

Autor: Claude Code (Fase 1 Optimización)
Fecha: 2025-11-14
"""

import time
import sys
import os
from pathlib import Path
import pandas as pd
import json

# Agregar path del backend al sys.path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    import psutil
except ImportError:
    print("ERROR: psutil no está instalado. Instalar con: pip install psutil")
    sys.exit(1)

# Importar módulos del backend
try:
    from main_logic import load_blob_data
    from services.cache_service import persistent_cache
except ImportError as e:
    print(f"ERROR: No se pudo importar módulos del backend: {e}")
    print(f"Asegúrate de ejecutar desde: {backend_dir}/tests/")
    sys.exit(1)


class BenchmarkRunner:
    """Ejecuta benchmarks y reporta métricas."""

    def __init__(self):
        self.results = []
        self.process = psutil.Process()

    def benchmark_load(self, base_name: str, iterations: int = 3, clear_cache: bool = True) -> pd.DataFrame:
        """
        Ejecuta benchmark de carga y reporta métricas.

        Args:
            base_name: Nombre de la base a cargar (ej: "UNIVERSO PERU", "UNIVERSO CHILE")
            iterations: Número de iteraciones para promediar
            clear_cache: Si True, limpia caché antes de cada iteración (mide carga fresca)

        Returns:
            DataFrame con resultados del benchmark
        """
        print(f"\n{'='*70}")
        print(f"BENCHMARK: {base_name}")
        print(f"Iteraciones: {iterations} | Limpiar caché: {'Sí' if clear_cache else 'No'}")
        print(f"{'='*70}\n")

        iteration_results = []

        for i in range(iterations):
            # Limpiar caché si se solicita
            if clear_cache:
                persistent_cache.clear_cache(base_name)
                print(f"[Iteración {i+1}] Caché limpiado")

            # Medir memoria inicial
            mem_before = self.process.memory_info().rss / 1024 / 1024  # MB

            # Medir tiempo de carga
            start = time.time()
            try:
                result = load_blob_data(base_name)
                elapsed = time.time() - start

                # Medir memoria final
                mem_after = self.process.memory_info().rss / 1024 / 1024  # MB
                mem_peak = mem_after - mem_before

                rows = result.get('total_rows', 0)
                cache_decision = result.get('cache_decision', 'unknown')

                iteration_results.append({
                    'iteration': i + 1,
                    'time_seconds': elapsed,
                    'memory_mb': mem_peak,
                    'rows': rows,
                    'cache_decision': cache_decision,
                    'success': True,
                    'error': None
                })

                print(f"[Iteración {i+1}] ✅ {elapsed:.2f}s | {mem_peak:.1f} MB | {rows:,} filas | {cache_decision}")

            except Exception as e:
                elapsed = time.time() - start
                iteration_results.append({
                    'iteration': i + 1,
                    'time_seconds': elapsed,
                    'memory_mb': 0,
                    'rows': 0,
                    'cache_decision': 'error',
                    'success': False,
                    'error': str(e)
                })
                print(f"[Iteración {i+1}] ❌ Error: {e}")

            # Pequeña pausa entre iteraciones
            time.sleep(2)

        # Calcular estadísticas
        df_results = pd.DataFrame(iteration_results)

        # Filtrar solo iteraciones exitosas para estadísticas
        df_success = df_results[df_results['success']]

        if not df_success.empty:
            print(f"\n{'─'*70}")
            print("RESULTADOS PROMEDIO:")
            print(f"{'─'*70}")
            print(f"Tiempo promedio:  {df_success['time_seconds'].mean():.2f}s (±{df_success['time_seconds'].std():.2f}s)")
            print(f"Tiempo mínimo:    {df_success['time_seconds'].min():.2f}s")
            print(f"Tiempo máximo:    {df_success['time_seconds'].max():.2f}s")
            print(f"Memoria promedio: {df_success['memory_mb'].mean():.1f} MB (±{df_success['memory_mb'].std():.1f} MB)")
            print(f"Memoria pico:     {df_success['memory_mb'].max():.1f} MB")
            print(f"Filas cargadas:   {df_success['rows'].iloc[0]:,}" if len(df_success) > 0 else "N/A")
            print(f"Éxito:            {len(df_success)}/{iterations} iteraciones")
            print(f"{'─'*70}\n")
        else:
            print("\n❌ TODAS LAS ITERACIONES FALLARON\n")

        # Agregar metadata
        df_results['base_name'] = base_name
        df_results['clear_cache'] = clear_cache

        return df_results

    def save_results(self, output_file: str = "benchmark_results.json"):
        """Guarda resultados del benchmark en formato JSON."""
        output_path = backend_dir / "tests" / output_file

        results_dict = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'benchmarks': self.results,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'python_version': sys.version
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False)

        print(f"✅ Resultados guardados en: {output_path}")


def main():
    """Función principal del benchmark."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                 BENCHMARK - FASE 1 OPTIMIZACIÓN                   ║
║                    App_SUITE v2.0.5 - Reportes                    ║
╚═══════════════════════════════════════════════════════════════════╝

Este script mide el impacto de las optimizaciones implementadas:
  ⚡ Hito 1.1: Conversión selectiva a string
  ⚡ Hito 1.2: Caché de fuentes de enriquecimiento
  ⚡ Hito 1.3: Generación paralela de opciones de filtro
  ⚡ Hito 1.4: Bases cacheables expandidas + detección Azure

Se realizarán dos tipos de pruebas por cada base:
  1. Carga FRESCA (sin caché) - 3 iteraciones
  2. Carga desde CACHÉ - 3 iteraciones
""")

    # input("Presiona ENTER para comenzar el benchmark...")  # Comentado para ejecución automática
    print("\n🚀 Iniciando benchmark automáticamente...\n")

    runner = BenchmarkRunner()

    # Bases a testear
    bases_to_test = [
        "UNIVERSO PERU",
        "INFO MARCA PROPIA PERU",
        "UNIVERSO CHILE",
        "MEJORAS CHILE",
        "ESTUDIOS CHILE"
    ]

    # Benchmark 1: Cargas frescas (sin caché)
    print("\n" + "="*70)
    print("FASE 1: CARGAS FRESCAS (sin caché)")
    print("="*70)

    for base_name in bases_to_test:
        try:
            results = runner.benchmark_load(base_name, iterations=3, clear_cache=True)
            runner.results.append({
                'base_name': base_name,
                'test_type': 'fresh_load',
                'results': results.to_dict('records')
            })
        except Exception as e:
            print(f"❌ Error en benchmark de {base_name}: {e}")
            continue

    # Benchmark 2: Cargas desde caché
    print("\n" + "="*70)
    print("FASE 2: CARGAS DESDE CACHÉ")
    print("="*70)

    for base_name in bases_to_test:
        try:
            results = runner.benchmark_load(base_name, iterations=3, clear_cache=False)
            runner.results.append({
                'base_name': base_name,
                'test_type': 'cached_load',
                'results': results.to_dict('records')
            })
        except Exception as e:
            print(f"❌ Error en benchmark de {base_name}: {e}")
            continue

    # Guardar resultados
    runner.save_results()

    print("\n" + "="*70)
    print("✅ BENCHMARK COMPLETADO")
    print("="*70)
    print("""
PRÓXIMOS PASOS:
1. Revisar los resultados guardados en benchmark_results.json
2. Comparar con métricas baseline (si existen)
3. Verificar que los objetivos de Fase 1 se cumplieron:
   - Tiempo de carga: -25% (35-50s → 25-35s)
   - Uso de RAM: -17% (~350 MB → ~290 MB)
4. Si los resultados son satisfactorios, proceder con Fase 2

Para análisis más detallado, revisar los logs de la aplicación.
""")


if __name__ == "__main__":
    main()
