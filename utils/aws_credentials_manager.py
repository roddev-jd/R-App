#!/usr/bin/env python3
"""
AWS Credentials Manager - GUI para macOS Keychain

Interfaz gráfica para gestionar credenciales AWS S3 almacenadas
de forma segura en macOS Keychain.

Uso:
    python3 aws_credentials_manager.py

Requisitos:
    - macOS (Keychain nativo)
    - keyring>=24.0.0
    - customtkinter>=5.2.0

Autor: Ripley P&C Team
Fecha: Diciembre 2025
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import threading

# Intentar importar customtkinter, con fallback a tkinter estándar
try:
    import customtkinter as ctk
    USE_CUSTOM_TK = True
except ImportError:
    import tkinter as ctk
    USE_CUSTOM_TK = False
    print("⚠️  customtkinter no disponible, usando tkinter estándar")

try:
    import keyring
except ImportError:
    messagebox.showerror(
        "Error",
        "La librería 'keyring' no está instalada.\n\n"
        "Instale con: pip install keyring"
    )
    sys.exit(1)

# Constantes
S3_KEYRING_SERVICE = "ProdPeruS3"
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 700

# Configurar tema si usamos customtkinter
if USE_CUSTOM_TK:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")


class AWSCredentialsManager:
    """Gestor de credenciales AWS con interfaz gráfica."""

    def __init__(self, root):
        """
        Inicializar la aplicación.

        Args:
            root: Ventana principal de tkinter
        """
        self.root = root
        self.root.title("AWS Credentials Manager - Prod Peru")

        # Configurar tamaño y centrar ventana
        self.center_window(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Variables de entrada
        self.access_key_var = tk.StringVar()
        self.secret_key_var = tk.StringVar()

        # Construir interfaz
        self.build_ui()

        # Cargar estado inicial
        self.check_existing_credentials()

    def center_window(self, width, height):
        """Centrar la ventana en la pantalla."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # Hacer que la ventana no sea redimensionable
        self.root.resizable(False, False)

    def build_ui(self):
        """Construir la interfaz de usuario."""

        # Frame principal con padding
        if USE_CUSTOM_TK:
            main_frame = ctk.CTkFrame(self.root)
        else:
            main_frame = tk.Frame(self.root, bg="#2b2b2b")

        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # ========== HEADER ==========
        if USE_CUSTOM_TK:
            header_label = ctk.CTkLabel(
                main_frame,
                text="🔐 AWS Credentials Manager",
                font=("Helvetica", 24, "bold")
            )
        else:
            header_label = tk.Label(
                main_frame,
                text="🔐 AWS Credentials Manager",
                font=("Helvetica", 24, "bold"),
                bg="#2b2b2b",
                fg="white"
            )
        header_label.pack(pady=(0, 10))

        if USE_CUSTOM_TK:
            subtitle_label = ctk.CTkLabel(
                main_frame,
                text="Gestión segura de credenciales en macOS Keychain",
                font=("Helvetica", 12)
            )
        else:
            subtitle_label = tk.Label(
                main_frame,
                text="Gestión segura de credenciales en macOS Keychain",
                font=("Helvetica", 12),
                bg="#2b2b2b",
                fg="#aaaaaa"
            )
        subtitle_label.pack(pady=(0, 20))

        # ========== STATUS FRAME ==========
        if USE_CUSTOM_TK:
            status_frame = ctk.CTkFrame(main_frame)
        else:
            status_frame = tk.Frame(main_frame, bg="#1e1e1e", relief="ridge", bd=2)

        status_frame.pack(fill="x", pady=(0, 20))

        if USE_CUSTOM_TK:
            status_title = ctk.CTkLabel(
                status_frame,
                text="Estado Actual",
                font=("Helvetica", 14, "bold")
            )
        else:
            status_title = tk.Label(
                status_frame,
                text="Estado Actual",
                font=("Helvetica", 14, "bold"),
                bg="#1e1e1e",
                fg="white"
            )
        status_title.pack(pady=(10, 5))

        if USE_CUSTOM_TK:
            self.status_label = ctk.CTkLabel(
                status_frame,
                text="Verificando...",
                font=("Helvetica", 11)
            )
        else:
            self.status_label = tk.Label(
                status_frame,
                text="Verificando...",
                font=("Helvetica", 11),
                bg="#1e1e1e",
                fg="#aaaaaa"
            )
        self.status_label.pack(pady=(0, 10))

        # ========== INPUT FRAME ==========
        if USE_CUSTOM_TK:
            input_frame = ctk.CTkFrame(main_frame)
        else:
            input_frame = tk.Frame(main_frame, bg="#1e1e1e", relief="ridge", bd=2)

        input_frame.pack(fill="x", pady=(0, 20))

        # Título de sección
        if USE_CUSTOM_TK:
            input_title = ctk.CTkLabel(
                input_frame,
                text="Credenciales AWS",
                font=("Helvetica", 14, "bold")
            )
        else:
            input_title = tk.Label(
                input_frame,
                text="Credenciales AWS",
                font=("Helvetica", 14, "bold"),
                bg="#1e1e1e",
                fg="white"
            )
        input_title.pack(pady=(10, 15))

        # Access Key ID
        if USE_CUSTOM_TK:
            access_label = ctk.CTkLabel(
                input_frame,
                text="AWS Access Key ID (20 caracteres):",
                font=("Helvetica", 11)
            )
        else:
            access_label = tk.Label(
                input_frame,
                text="AWS Access Key ID (20 caracteres):",
                font=("Helvetica", 11),
                bg="#1e1e1e",
                fg="white"
            )
        access_label.pack(pady=(0, 5))

        if USE_CUSTOM_TK:
            self.access_key_entry = ctk.CTkEntry(
                input_frame,
                textvariable=self.access_key_var,
                width=400,
                height=35,
                font=("Courier", 12)
            )
        else:
            self.access_key_entry = tk.Entry(
                input_frame,
                textvariable=self.access_key_var,
                width=40,
                font=("Courier", 12)
            )
        self.access_key_entry.pack(pady=(0, 15))

        # Secret Access Key
        if USE_CUSTOM_TK:
            secret_label = ctk.CTkLabel(
                input_frame,
                text="AWS Secret Access Key (40 caracteres):",
                font=("Helvetica", 11)
            )
        else:
            secret_label = tk.Label(
                input_frame,
                text="AWS Secret Access Key (40 caracteres):",
                font=("Helvetica", 11),
                bg="#1e1e1e",
                fg="white"
            )
        secret_label.pack(pady=(0, 5))

        if USE_CUSTOM_TK:
            self.secret_key_entry = ctk.CTkEntry(
                input_frame,
                textvariable=self.secret_key_var,
                width=400,
                height=35,
                font=("Courier", 12),
                show="*"
            )
        else:
            self.secret_key_entry = tk.Entry(
                input_frame,
                textvariable=self.secret_key_var,
                width=40,
                font=("Courier", 12),
                show="*"
            )
        self.secret_key_entry.pack(pady=(0, 10))

        # Checkbox para mostrar/ocultar Secret Key
        self.show_secret_var = tk.BooleanVar()
        if USE_CUSTOM_TK:
            show_secret_check = ctk.CTkCheckBox(
                input_frame,
                text="Mostrar Secret Key",
                variable=self.show_secret_var,
                command=self.toggle_secret_visibility
            )
        else:
            show_secret_check = tk.Checkbutton(
                input_frame,
                text="Mostrar Secret Key",
                variable=self.show_secret_var,
                command=self.toggle_secret_visibility,
                bg="#1e1e1e",
                fg="white",
                selectcolor="#1e1e1e"
            )
        show_secret_check.pack(pady=(0, 15))

        # ========== BUTTONS FRAME ==========
        if USE_CUSTOM_TK:
            buttons_frame = ctk.CTkFrame(main_frame)
        else:
            buttons_frame = tk.Frame(main_frame, bg="#2b2b2b")

        buttons_frame.pack(fill="x", pady=(0, 20))

        # Frame para botones principales (centrado)
        if USE_CUSTOM_TK:
            main_buttons = ctk.CTkFrame(buttons_frame)
        else:
            main_buttons = tk.Frame(buttons_frame, bg="#2b2b2b")
        main_buttons.pack()

        # Botón Guardar
        if USE_CUSTOM_TK:
            save_button = ctk.CTkButton(
                main_buttons,
                text="💾 Guardar Credenciales",
                command=self.save_credentials,
                width=180,
                height=40,
                font=("Helvetica", 12, "bold"),
                fg_color="#28a745",
                hover_color="#218838"
            )
        else:
            save_button = tk.Button(
                main_buttons,
                text="💾 Guardar Credenciales",
                command=self.save_credentials,
                width=20,
                height=2,
                font=("Helvetica", 11, "bold"),
                bg="#28a745",
                fg="white",
                relief="raised"
            )
        save_button.pack(side="left", padx=5)

        # Botón Eliminar
        if USE_CUSTOM_TK:
            delete_button = ctk.CTkButton(
                main_buttons,
                text="🗑️  Eliminar Credenciales",
                command=self.delete_credentials,
                width=180,
                height=40,
                font=("Helvetica", 12, "bold"),
                fg_color="#dc3545",
                hover_color="#c82333"
            )
        else:
            delete_button = tk.Button(
                main_buttons,
                text="🗑️  Eliminar Credenciales",
                command=self.delete_credentials,
                width=20,
                height=2,
                font=("Helvetica", 11, "bold"),
                bg="#dc3545",
                fg="white",
                relief="raised"
            )
        delete_button.pack(side="left", padx=5)

        # Frame para botones secundarios
        if USE_CUSTOM_TK:
            secondary_buttons = ctk.CTkFrame(buttons_frame)
        else:
            secondary_buttons = tk.Frame(buttons_frame, bg="#2b2b2b")
        secondary_buttons.pack(pady=(10, 0))

        # Botón Probar
        if USE_CUSTOM_TK:
            test_button = ctk.CTkButton(
                secondary_buttons,
                text="🧪 Probar Conexión S3",
                command=self.test_credentials,
                width=180,
                height=40,
                font=("Helvetica", 12, "bold"),
                fg_color="#007bff",
                hover_color="#0056b3"
            )
        else:
            test_button = tk.Button(
                secondary_buttons,
                text="🧪 Probar Conexión S3",
                command=self.test_credentials,
                width=20,
                height=2,
                font=("Helvetica", 11, "bold"),
                bg="#007bff",
                fg="white",
                relief="raised"
            )
        test_button.pack(side="left", padx=5)

        # Botón Recargar
        if USE_CUSTOM_TK:
            reload_button = ctk.CTkButton(
                secondary_buttons,
                text="🔄 Recargar Estado",
                command=self.check_existing_credentials,
                width=180,
                height=40,
                font=("Helvetica", 12, "bold")
            )
        else:
            reload_button = tk.Button(
                secondary_buttons,
                text="🔄 Recargar Estado",
                command=self.check_existing_credentials,
                width=20,
                height=2,
                font=("Helvetica", 11, "bold"),
                bg="#6c757d",
                fg="white",
                relief="raised"
            )
        reload_button.pack(side="left", padx=5)

        # ========== INFO FRAME ==========
        if USE_CUSTOM_TK:
            info_frame = ctk.CTkFrame(main_frame)
        else:
            info_frame = tk.Frame(main_frame, bg="#1e1e1e", relief="ridge", bd=2)

        info_frame.pack(fill="both", expand=True)

        info_text = (
            "ℹ️  Información:\n\n"
            "• Las credenciales se guardan encriptadas en macOS Keychain\n"
            "• Servicio: ProdPeruS3\n"
            "• Access Key: 20 caracteres\n"
            "• Secret Key: 40 caracteres\n\n"
            "Para más información:\n"
            "FlexStart/apps/prod_peru/backend/S3_CREDENTIALS_README.md"
        )

        if USE_CUSTOM_TK:
            info_label = ctk.CTkLabel(
                info_frame,
                text=info_text,
                font=("Helvetica", 10),
                justify="left"
            )
        else:
            info_label = tk.Label(
                info_frame,
                text=info_text,
                font=("Helvetica", 10),
                justify="left",
                bg="#1e1e1e",
                fg="#aaaaaa"
            )
        info_label.pack(padx=15, pady=15)

    def toggle_secret_visibility(self):
        """Alternar visibilidad del Secret Key."""
        if self.show_secret_var.get():
            self.secret_key_entry.configure(show="")
        else:
            self.secret_key_entry.configure(show="*")

    def check_existing_credentials(self):
        """Verificar si existen credenciales en Keychain."""
        try:
            access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
            secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

            if access_key and secret_key:
                # Mostrar parcialmente
                masked_access = f"{access_key[:10]}...{access_key[-4:]}"
                masked_secret = f"{'*' * 36}{secret_key[-4:]}"

                status_text = (
                    f"✅ Credenciales encontradas\n\n"
                    f"Access Key: {masked_access}\n"
                    f"Secret Key: {masked_secret}"
                )
                self.status_label.configure(text=status_text)
            else:
                self.status_label.configure(
                    text="❌ No hay credenciales configuradas\n\nIngrese las credenciales abajo y presione 'Guardar'"
                )
        except Exception as e:
            self.status_label.configure(
                text=f"⚠️  Error verificando credenciales:\n{str(e)}"
            )

    def validate_credentials(self, access_key: str, secret_key: str) -> bool:
        """
        Validar formato de credenciales.

        Args:
            access_key: AWS Access Key ID
            secret_key: AWS Secret Access Key

        Returns:
            True si son válidas
        """
        if not access_key or not secret_key:
            messagebox.showerror(
                "Error de Validación",
                "Las credenciales no pueden estar vacías"
            )
            return False

        # Validar longitud de Access Key
        if len(access_key) != 20:
            result = messagebox.askyesno(
                "Advertencia",
                f"AWS Access Key ID normalmente tiene 20 caracteres.\n"
                f"La clave ingresada tiene {len(access_key)} caracteres.\n\n"
                f"¿Desea continuar de todas formas?"
            )
            if not result:
                return False

        # Validar longitud de Secret Key
        if len(secret_key) != 40:
            result = messagebox.askyesno(
                "Advertencia",
                f"AWS Secret Access Key normalmente tiene 40 caracteres.\n"
                f"La clave ingresada tiene {len(secret_key)} caracteres.\n\n"
                f"¿Desea continuar de todas formas?"
            )
            if not result:
                return False

        return True

    def save_credentials(self):
        """Guardar credenciales en Keychain."""
        access_key = self.access_key_var.get().strip()
        secret_key = self.secret_key_var.get().strip()

        # Validar
        if not self.validate_credentials(access_key, secret_key):
            return

        # Confirmar
        masked_access = f"{access_key[:10]}...{access_key[-4:]}" if len(access_key) > 14 else access_key

        result = messagebox.askyesno(
            "Confirmar",
            f"¿Confirma guardar estas credenciales en macOS Keychain?\n\n"
            f"Access Key: {masked_access}\n"
            f"Secret Key: ****************************************\n\n"
            f"Servicio: {S3_KEYRING_SERVICE}"
        )

        if not result:
            return

        try:
            # Guardar en Keychain
            keyring.set_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID", access_key)
            keyring.set_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY", secret_key)

            messagebox.showinfo(
                "Éxito",
                "✅ Credenciales guardadas exitosamente en macOS Keychain\n\n"
                f"Servicio: {S3_KEYRING_SERVICE}\n"
                "Keys: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
            )

            # Limpiar campos
            self.access_key_var.set("")
            self.secret_key_var.set("")

            # Recargar estado
            self.check_existing_credentials()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"❌ Error guardando credenciales:\n\n{str(e)}"
            )

    def delete_credentials(self):
        """Eliminar credenciales de Keychain."""
        # Confirmar
        result = messagebox.askyesno(
            "Confirmar Eliminación",
            "⚠️  ¿Está seguro que desea eliminar las credenciales de macOS Keychain?\n\n"
            "Esta acción no se puede deshacer."
        )

        if not result:
            return

        try:
            keyring.delete_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
            keyring.delete_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

            messagebox.showinfo(
                "Éxito",
                "✅ Credenciales eliminadas de macOS Keychain"
            )

            # Recargar estado
            self.check_existing_credentials()

        except Exception as e:
            messagebox.showwarning(
                "Advertencia",
                f"No se pudieron eliminar las credenciales:\n\n{str(e)}\n\n"
                "Es posible que no existieran credenciales guardadas."
            )

    def test_credentials_thread(self):
        """Probar credenciales en un hilo separado."""
        try:
            # Leer credenciales desde Keychain
            access_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_ACCESS_KEY_ID")
            secret_key = keyring.get_password(S3_KEYRING_SERVICE, "AWS_SECRET_ACCESS_KEY")

            if not all([access_key, secret_key]):
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    "❌ No hay credenciales en macOS Keychain\n\n"
                    "Guarde las credenciales primero."
                ))
                return

            # Importar boto3
            try:
                import boto3
                from botocore.exceptions import ClientError, NoCredentialsError
            except ImportError:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error",
                    "❌ La librería 'boto3' no está instalada\n\n"
                    "Instale con: pip install boto3"
                ))
                return

            # Crear cliente S3
            client = boto3.client(
                's3',
                aws_access_key_id=access_key.strip(),
                aws_secret_access_key=secret_key.strip(),
                region_name='us-east-1'
            )

            # Intentar listar bucket
            bucket_name = "s3-vi1-wop-prd"
            response = client.list_objects_v2(
                Bucket=bucket_name,
                MaxKeys=1,
                Prefix="prod_peru/"
            )

            # Éxito
            self.root.after(0, lambda: messagebox.showinfo(
                "Test Exitoso",
                f"✅ Conexión S3 verificada exitosamente\n\n"
                f"Bucket: {bucket_name}\n"
                f"Región: us-east-1\n"
                f"Credenciales: Válidas"
            ))

        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: messagebox.showerror(
                "Test Fallido",
                f"❌ No se pudo conectar a S3\n\n"
                f"Error: {error_msg}\n\n"
                f"Posibles causas:\n"
                f"• Credenciales incorrectas\n"
                f"• Sin conexión a internet\n"
                f"• Permisos IAM insuficientes\n"
                f"• Bucket incorrecto"
            ))

    def test_credentials(self):
        """Probar credenciales (lanzar hilo)."""
        # Ejecutar en hilo separado para no bloquear UI
        thread = threading.Thread(target=self.test_credentials_thread, daemon=True)
        thread.start()


def main():
    """Función principal."""
    # Verificar que estamos en macOS
    if sys.platform != "darwin":
        result = messagebox.askyesno(
            "Advertencia",
            f"⚠️  Este sistema operativo es '{sys.platform}', no macOS\n\n"
            f"El script funciona mejor en macOS con Keychain nativo.\n"
            f"En otros sistemas, keyring usará un backend alternativo.\n\n"
            f"¿Desea continuar de todas formas?"
        )
        if not result:
            sys.exit(0)

    # Crear ventana principal
    if USE_CUSTOM_TK:
        root = ctk.CTk()
    else:
        root = tk.Tk()
        root.configure(bg="#2b2b2b")

    # Crear aplicación
    app = AWSCredentialsManager(root)

    # Ejecutar loop
    root.mainloop()


if __name__ == "__main__":
    main()
