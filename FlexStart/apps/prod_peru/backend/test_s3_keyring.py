#!/usr/bin/env python3
"""
Script de Testing para Credenciales S3 en Keyring

Verifica que:
1. Las credenciales están en keyring
2. El cliente S3 se inicializa correctamente
3. Se puede listar el bucket (prueba de conectividad)
4. La integración con app.py funciona

Uso:
    python3 test_s3_keyring.py
"""

import sys
from pathlib import Path

# Agregar directorio backend al path
sys.path.insert(0, str(Path(__file__).parent))

import logging
import keyring
import boto3

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

S3_KEYRING_SERVICE = "ProdPeruS3"

def test_keyring_credentials():
    """Test 1: Verificar que las credenciales están en keyring."""
    print("\n" + "=" * 70)
    print("TEST 1: Verificar credenciales en macOS Keychain")
    print("=" * 70)

    try:
        access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
        secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

        if not access_key:
            print("❌ FALLIDO: AWS_ACCESS_KEY_ID no encontrado en keyring")
            return False

        if not secret_key:
            print("❌ FALLIDO: AWS_SECRET_ACCESS_KEY no encontrado en keyring")
            return False

        print(f"✅ PASADO: Credenciales encontradas en keyring")
        print(f"   AWS_ACCESS_KEY_ID: {access_key[:10]}...{access_key[-4:]}")
        print(f"   AWS_SECRET_ACCESS_KEY: {'*' * 36}{secret_key[-4:]}")

        return True

    except Exception as e:
        print(f"❌ FALLIDO: Error accediendo keyring: {e}")
        return False

def test_s3_client_initialization():
    """Test 2: Verificar que el cliente S3 se inicializa."""
    print("\n" + "=" * 70)
    print("TEST 2: Inicializar cliente boto3 S3")
    print("=" * 70)

    try:
        access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
        secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

        client = boto3.client(
            's3',
            aws_access_key_id=access_key.strip(),
            aws_secret_access_key=secret_key.strip(),
            region_name='us-east-1'
        )

        print("✅ PASADO: Cliente S3 inicializado correctamente")
        return True

    except Exception as e:
        print(f"❌ FALLIDO: Error inicializando cliente S3: {e}")
        return False

def test_s3_connectivity(bucket_name="s3-vi1-wop-prd"):
    """Test 3: Verificar conectividad S3 (listando bucket)."""
    print("\n" + "=" * 70)
    print(f"TEST 3: Verificar conectividad S3 (bucket: {bucket_name})")
    print("=" * 70)

    try:
        access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
        secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

        client = boto3.client(
            's3',
            aws_access_key_id=access_key.strip(),
            aws_secret_access_key=secret_key.strip(),
            region_name='us-east-1'
        )

        # Intentar listar primeros 5 objetos
        response = client.list_objects_v2(
            Bucket=bucket_name,
            MaxKeys=5,
            Prefix="prod_peru/"
        )

        if 'Contents' in response:
            count = len(response['Contents'])
            print(f"✅ PASADO: Conectividad S3 verificada")
            print(f"   Bucket: {bucket_name}")
            print(f"   Objetos encontrados (primeros 5): {count}")
            for obj in response['Contents'][:3]:
                print(f"   - {obj['Key']}")
        else:
            print(f"✅ PASADO: Bucket accesible pero sin objetos en 'prod_peru/'")

        return True

    except Exception as e:
        print(f"⚠️  ADVERTENCIA: No se pudo conectar a S3: {e}")
        print("   Esto puede deberse a:")
        print("   - Credenciales incorrectas")
        print("   - Bucket incorrecto")
        print("   - Sin conexión a internet")
        print("   - Permisos IAM insuficientes")
        return False

def test_app_integration():
    """Test 4: Verificar integración con app.py."""
    print("\n" + "=" * 70)
    print("TEST 4: Integración con app.py")
    print("=" * 70)

    try:
        # Importar la función de app.py
        from app import get_s3_client

        # Llamar a la función
        client = get_s3_client()

        if client is None:
            print("❌ FALLIDO: get_s3_client() retornó None")
            return False

        print("✅ PASADO: get_s3_client() funciona correctamente")
        print("   Cliente S3 inicializado desde app.py")

        return True

    except Exception as e:
        print(f"❌ FALLIDO: Error en integración con app.py: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todos los tests."""
    print("\n" + "=" * 70)
    print("Suite de Testing: Credenciales S3 en macOS Keychain")
    print("=" * 70)

    results = []

    # Test 1
    results.append(("Credenciales en Keychain", test_keyring_credentials()))

    # Test 2
    results.append(("Inicialización Cliente S3", test_s3_client_initialization()))

    # Test 3 (puede fallar si no hay internet o permisos)
    results.append(("Conectividad S3", test_s3_connectivity()))

    # Test 4
    results.append(("Integración app.py", test_app_integration()))

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN DE TESTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✅ PASADO" if result else "❌ FALLADO"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("-" * 70)
    print(f"Total: {len(results)} tests | Pasados: {passed} | Fallados: {failed}")
    print("=" * 70)

    if failed == 0:
        print("\n🎉 ¡Todos los tests pasaron! La migración fue exitosa.")
        return 0
    else:
        print(f"\n⚠️  {failed} test(s) fallaron. Revise los mensajes de error arriba.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
