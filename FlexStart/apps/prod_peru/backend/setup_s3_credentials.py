#!/usr/bin/env python3
"""
Setup Script para Credenciales AWS S3 en macOS Keychain

Este script configura las credenciales AWS S3 para la aplicación Prod Peru
en macOS Keychain, eliminando la necesidad de archivos .env o variables de entorno.

Uso:
    python3 setup_s3_credentials.py

Requisitos:
    - macOS (usa Keychain nativo)
    - keyring>=24.0.0 instalado
    - Credenciales AWS válidas (Access Key ID y Secret Access Key)

Autor: Ripley P&C Team
Fecha: Diciembre 2025
"""

import sys
import getpass
import keyring
from pathlib import Path

# Nombre del servicio en Keychain (debe coincidir con app.py)
S3_KEYRING_SERVICE = "ProdPeruS3"

def validate_credentials(access_key: str, secret_key: str) -> bool:
    """
    Validar que las credenciales tengan el formato correcto.

    Args:
        access_key: AWS Access Key ID
        secret_key: AWS Secret Access Key

    Returns:
        True si las credenciales tienen formato válido
    """
    # AWS Access Key IDs tienen 20 caracteres
    if len(access_key) != 20:
        print("⚠️  ADVERTENCIA: AWS Access Key ID normalmente tiene 20 caracteres")
        print(f"   La clave ingresada tiene {len(access_key)} caracteres")

    # AWS Secret Access Keys tienen 40 caracteres
    if len(secret_key) != 40:
        print("⚠️  ADVERTENCIA: AWS Secret Access Key normalmente tiene 40 caracteres")
        print(f"   La clave ingresada tiene {len(secret_key)} caracteres")

    # Validar que no estén vacías
    if not access_key or not secret_key:
        print("❌ ERROR: Las credenciales no pueden estar vacías")
        return False

    return True

def check_existing_credentials():
    """Verificar si ya existen credenciales en Keychain."""
    try:
        access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
        secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

        if access_key or secret_key:
            print(f"\n⚠️  Ya existen credenciales para '{S3_KEYRING_SERVICE}' en macOS Keychain")
            if access_key:
                print(f"   AWS_ACCESS_KEY_ID: {access_key[:10]}...{access_key[-4:]}")
            if secret_key:
                print(f"   AWS_SECRET_ACCESS_KEY: {'*' * 36}{secret_key[-4:]}")
            return True
        return False
    except Exception as e:
        print(f"⚠️  Error verificando credenciales existentes: {e}")
        return False

def save_credentials(access_key: str, secret_key: str) -> bool:
    """
    Guardar credenciales en macOS Keychain.

    Args:
        access_key: AWS Access Key ID
        secret_key: AWS Secret Access Key

    Returns:
        True si se guardaron exitosamente
    """
    try:
        # Guardar en Keychain
        keyring.set_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID", access_key)
        keyring.set_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY", secret_key)

        print("\n✅ Credenciales guardadas exitosamente en macOS Keychain")
        print(f"   Servicio: {S3_KEYRING_SERVICE}")
        print(f"   Keys: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")

        return True

    except Exception as e:
        print(f"\n❌ Error guardando credenciales: {e}")
        return False

def delete_credentials():
    """Eliminar credenciales existentes de Keychain."""
    try:
        keyring.delete_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
        keyring.delete_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")
        print("✅ Credenciales eliminadas de macOS Keychain")
        return True
    except keyring.errors.PasswordDeleteError:
        print("ℹ️  No había credenciales que eliminar")
        return True
    except Exception as e:
        print(f"❌ Error eliminando credenciales: {e}")
        return False

def test_credentials():
    """Probar que las credenciales se pueden leer de Keychain."""
    try:
        access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
        secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

        if access_key and secret_key:
            print("\n🧪 TEST: Credenciales leídas correctamente desde Keychain")
            print(f"   AWS_ACCESS_KEY_ID: {access_key[:10]}...{access_key[-4:]}")
            print(f"   AWS_SECRET_ACCESS_KEY: {'*' * 36}{secret_key[-4:]}")
            return True
        else:
            print("\n❌ TEST FALLIDO: No se pudieron leer las credenciales")
            return False

    except Exception as e:
        print(f"\n❌ TEST FALLIDO: {e}")
        return False

def main():
    """Función principal del script."""
    print("=" * 70)
    print("Setup de Credenciales AWS S3 para Prod Peru")
    print("macOS Keychain Configuration Tool")
    print("=" * 70)

    # Verificar que estamos en macOS
    if sys.platform != "darwin":
        print(f"\n⚠️  ADVERTENCIA: Este sistema operativo es '{sys.platform}', no macOS")
        print("   El script funciona mejor en macOS con Keychain nativo")
        print("   En otros sistemas, keyring usará un backend alternativo")
        response = input("\n¿Desea continuar de todas formas? (s/N): ").strip().lower()
        if response != 's':
            print("❌ Operación cancelada")
            return

    # Verificar credenciales existentes
    has_existing = check_existing_credentials()

    if has_existing:
        print("\nOpciones:")
        print("  1. Sobrescribir con nuevas credenciales")
        print("  2. Eliminar credenciales existentes")
        print("  3. Probar credenciales existentes")
        print("  4. Cancelar (no hacer nada)")

        choice = input("\nSeleccione una opción (1-4): ").strip()

        if choice == "2":
            if delete_credentials():
                print("\n✅ Operación completada")
            else:
                print("\n❌ Operación fallida")
            return

        elif choice == "3":
            test_credentials()
            return

        elif choice == "4":
            print("❌ Operación cancelada")
            return

        elif choice != "1":
            print("❌ Opción inválida. Operación cancelada")
            return

    # Solicitar credenciales
    print("\n" + "-" * 70)
    print("Ingrese sus credenciales AWS S3")
    print("-" * 70)
    print("\nNOTA: Las credenciales NO se mostrarán en pantalla mientras las escribe")
    print("      (la Secret Key será invisible por seguridad)")

    # Solicitar Access Key ID
    print("\nAWS Access Key ID (20 caracteres):")
    access_key = input("> ").strip()

    # Solicitar Secret Access Key (oculto)
    print("\nAWS Secret Access Key (40 caracteres, oculto):")
    secret_key = getpass.getpass("> ")

    # Validar formato
    if not validate_credentials(access_key, secret_key):
        response = input("\n¿Desea guardar las credenciales de todas formas? (s/N): ").strip().lower()
        if response != 's':
            print("❌ Operación cancelada")
            return

    # Confirmar antes de guardar
    print("\n" + "-" * 70)
    print("Resumen:")
    print(f"  AWS_ACCESS_KEY_ID: {access_key[:10]}...{access_key[-4:] if len(access_key) > 14 else ''}")
    print(f"  AWS_SECRET_ACCESS_KEY: {'*' * 36}****")
    print(f"  Servicio Keychain: {S3_KEYRING_SERVICE}")
    print("-" * 70)

    response = input("\n¿Confirma guardar estas credenciales en macOS Keychain? (s/N): ").strip().lower()

    if response != 's':
        print("❌ Operación cancelada")
        return

    # Guardar credenciales
    if save_credentials(access_key, secret_key):
        # Probar inmediatamente
        test_credentials()

        print("\n" + "=" * 70)
        print("✅ CONFIGURACIÓN COMPLETADA")
        print("=" * 70)
        print("\nPróximos pasos:")
        print("  1. Las credenciales ya están disponibles para la aplicación")
        print("  2. El archivo .env ya NO es necesario (puede eliminarse)")
        print("  3. Reinicie la aplicación Prod Peru para aplicar los cambios")
        print("\nPara eliminar las credenciales en el futuro:")
        print(f"  python3 {Path(__file__).name}")
        print("=" * 70)
    else:
        print("\n❌ Error en la configuración. Por favor, intente nuevamente")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operación cancelada por el usuario (Ctrl+C)")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
