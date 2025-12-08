#!/usr/bin/env python3
"""
Script para ejecutar diagnóstico completo de problemas de base de datos

Este script ejecuta todos los tests y diagnósticos para identificar
y solucionar los problemas esporádicos de carga de bases de datos.

Uso:
    python run_diagnosis.py              # Diagnóstico básico
    python run_diagnosis.py --full       # Diagnóstico completo con tests intensivos
    python run_diagnosis.py --fix        # Aplicar parches de estabilidad
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

# Agregar directorios al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def run_basic_diagnosis():
    """Ejecutar diagnóstico básico."""
    logging.info("🩺 Ejecutando diagnóstico básico...")

    try:
        from test_runner import DatabaseLoadingDiagnostic

        diagnostic = DatabaseLoadingDiagnostic()
        results = diagnostic.run_all_tests()

        return results

    except ImportError as e:
        logging.error(f"Error importando módulos de diagnóstico: {e}")
        return None
    except Exception as e:
        logging.error(f"Error en diagnóstico básico: {e}")
        return None

def run_full_diagnosis():
    """Ejecutar diagnóstico completo con tests intensivos."""
    logging.info("🩺 Ejecutando diagnóstico completo...")

    try:
        import subprocess

        # Ejecutar tests de pytest si está disponible
        try:
            result = subprocess.run([
                sys.executable, "-m", "pytest",
                str(backend_dir / "tests" / "test_database_loading.py"),
                "-v",
                "--tb=short"
            ], capture_output=True, text=True, timeout=300)

            logging.info("📊 Resultado de tests de pytest:")
            if result.stdout:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        logging.info(f"   {line}")

            if result.stderr:
                logging.warning("⚠️ Errores en tests:")
                for line in result.stderr.split('\n'):
                    if line.strip():
                        logging.warning(f"   {line}")

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            logging.error("⏰ Tests de pytest excedieron el tiempo límite")
            return False
        except FileNotFoundError:
            logging.warning("⚠️ pytest no disponible, ejecutando diagnóstico básico")
            return run_basic_diagnosis()

    except Exception as e:
        logging.error(f"Error en diagnóstico completo: {e}")
        return False

def apply_stability_fixes():
    """Aplicar parches de estabilidad."""
    logging.info("🔧 Aplicando parches de estabilidad...")

    try:
        from database_stability_fixes import apply_stability_patches, get_system_health_status

        # Aplicar parches
        success = apply_stability_patches()

        if success:
            logging.info("✅ Parches aplicados exitosamente")

            # Verificar estado del sistema
            health_status = get_system_health_status()
            logging.info("📊 Estado del sistema después de parches:")

            for key, value in health_status.items():
                if key != "timestamp":
                    logging.info(f"   {key}: {value}")

            return True
        else:
            logging.error("❌ Falló la aplicación de parches")
            return False

    except ImportError as e:
        logging.error(f"Error importando módulos de estabilidad: {e}")
        return False
    except Exception as e:
        logging.error(f"Error aplicando parches: {e}")
        return False

def check_system_dependencies():
    """Verificar dependencias del sistema."""
    logging.info("🔍 Verificando dependencias del sistema...")

    dependencies = {}

    # Verificar pandas
    try:
        import pandas as pd
        dependencies['pandas'] = pd.__version__
    except ImportError:
        dependencies['pandas'] = 'NOT_AVAILABLE'

    # Verificar DuckDB
    try:
        import duckdb
        dependencies['duckdb'] = duckdb.__version__
    except ImportError:
        dependencies['duckdb'] = 'NOT_AVAILABLE'

    # Verificar threading
    import threading
    dependencies['threading'] = 'AVAILABLE'

    # Verificar main_logic
    try:
        from main_logic import df_original, duckdb_conn
        dependencies['main_logic'] = 'AVAILABLE'
    except ImportError as e:
        dependencies['main_logic'] = f'ERROR: {e}'

    logging.info("📦 Estado de dependencias:")
    for dep, status in dependencies.items():
        status_icon = "✅" if status not in ['NOT_AVAILABLE'] and not status.startswith('ERROR') else "❌"
        logging.info(f"   {status_icon} {dep}: {status}")

    # Verificar que las dependencias críticas estén disponibles
    critical_deps = ['pandas', 'main_logic']
    missing_critical = [dep for dep in critical_deps if dependencies.get(dep, '').startswith(('NOT_AVAILABLE', 'ERROR'))]

    if missing_critical:
        logging.error(f"❌ Dependencias críticas faltantes: {missing_critical}")
        return False

    if dependencies.get('duckdb') == 'NOT_AVAILABLE':
        logging.warning("⚠️ DuckDB no disponible - funcionalidad limitada")

    return True

def generate_report(diagnosis_results, fix_applied=False):
    """Generar reporte de diagnóstico."""
    logging.info("\n" + "=" * 60)
    logging.info("📋 REPORTE DE DIAGNÓSTICO DE BASE DE DATOS")
    logging.info("=" * 60)

    # Información general
    logging.info(f"⏰ Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"🔧 Parches aplicados: {'Sí' if fix_applied else 'No'}")

    if diagnosis_results:
        if isinstance(diagnosis_results, dict):
            # Resultados del diagnóstico básico
            passed = sum(1 for result in diagnosis_results.values() if result)
            total = len(diagnosis_results)

            logging.info(f"📊 Tests ejecutados: {total}")
            logging.info(f"✅ Tests pasados: {passed}")
            logging.info(f"❌ Tests fallidos: {total - passed}")

            if total > 0:
                success_rate = (passed / total) * 100
                logging.info(f"📈 Tasa de éxito: {success_rate:.1f}%")

            # Detalles por test
            logging.info("\n📋 Detalle de tests:")
            for test_name, result in diagnosis_results.items():
                status = "✅" if result else "❌"
                logging.info(f"   {status} {test_name}")

            # Recomendaciones
            logging.info("\n💡 RECOMENDACIONES:")
            if passed == total:
                logging.info("   🎉 Sistema estable - no se detectaron problemas")
            else:
                logging.info("   ⚠️ Se detectaron problemas de estabilidad")
                logging.info("   🔧 Ejecutar con --fix para aplicar parches")
                logging.info("   🧪 Ejecutar tests completos con --full")

        else:
            # Resultado booleano simple
            if diagnosis_results:
                logging.info("✅ Diagnóstico pasó exitosamente")
            else:
                logging.info("❌ Diagnóstico falló")

    else:
        logging.info("❌ No se pudieron ejecutar los diagnósticos")

    logging.info("=" * 60)

def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Diagnóstico de problemas de carga de base de datos"
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Ejecutar diagnóstico completo con tests intensivos'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Aplicar parches de estabilidad'
    )
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Solo verificar dependencias'
    )

    args = parser.parse_args()

    logging.info("🚀 Iniciando diagnóstico de base de datos SUITE")
    logging.info(f"📁 Directorio de trabajo: {backend_dir}")

    start_time = time.time()

    # Verificar dependencias
    if not check_system_dependencies():
        logging.error("❌ Dependencias críticas faltantes")
        return 1

    if args.check_deps:
        logging.info("✅ Verificación de dependencias completada")
        return 0

    # Aplicar parches si se solicita
    fix_applied = False
    if args.fix:
        fix_applied = apply_stability_fixes()
        if not fix_applied:
            logging.error("❌ Falló la aplicación de parches")
            return 1

    # Ejecutar diagnóstico
    diagnosis_results = None
    if args.full:
        diagnosis_results = run_full_diagnosis()
    else:
        diagnosis_results = run_basic_diagnosis()

    # Generar reporte
    generate_report(diagnosis_results, fix_applied)

    # Tiempo total
    total_time = time.time() - start_time
    logging.info(f"⏱️ Tiempo total de ejecución: {total_time:.2f}s")

    # Código de salida
    if diagnosis_results:
        if isinstance(diagnosis_results, dict):
            all_passed = all(diagnosis_results.values())
            return 0 if all_passed else 1
        else:
            return 0 if diagnosis_results else 1
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())