import os
import threading
import queue # For thread-safe GUI updates
import tkinter as tk
from tkinter import filedialog, messagebox # Standard Tkinter dialogs
import sys

# Verificar dependencias antes de importar
try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    TTKBOOTSTRAP_AVAILABLE = True
except ImportError:
    import tkinter.ttk as ttk
    TTKBOOTSTRAP_AVAILABLE = False
    print("Warning: ttkbootstrap not available, using standard ttk")

# Importar tema solo si está disponible
# Función de tema compatible multiplataforma
def setup_theme(window=None):
    import ttkbootstrap as ttk
    style = ttk.Style()
    
    # Lista de temas ordenados por compatibilidad multiplataforma
    preferred_themes = ["flatly", "litera", "cosmo", "journal", "sandstone"]
    available = list(style.theme_names())
    
    for theme in preferred_themes:
        if theme in available:
            try:
                style.theme_use(theme)
                return style
            except:
                continue
    
    # Fallback a tema por defecto
    try:
        style.theme_use("default")
    except:
        pass
    
    return style

THEME_AVAILABLE = True

# --- Lógica de renombrado (adaptada para correr en hilo y reportar vía queue) ---
def renombrar_imagenes_en_hilo(directorio_raiz: str, update_queue: queue.Queue):
    """
    Recorre subdirectorios y renombra imágenes. Envía actualizaciones a la GUI vía cola.
    La lógica de renombrado se mantiene idéntica a la original.
    """
    archivos_procesados = 0
    archivos_renombrados = 0
    errores_count = 0

    try:
        update_queue.put(("status", "Iniciando renombrado..."))
        formatos_imagen = ['.jpg', '.png', '.webp', '.jpeg'] # Agregado .jpeg por si acaso

        # Verificar que el directorio existe
        if not os.path.exists(directorio_raiz):
            update_queue.put(("show_message", "error", "Error", f"El directorio no existe: {directorio_raiz}"))
            return

        try:
            subdirectorios = os.listdir(directorio_raiz)
        except PermissionError:
            update_queue.put(("show_message", "error", "Error de Permisos", f"Sin permisos para acceder a: {directorio_raiz}"))
            return
        except OSError as e:
            update_queue.put(("show_message", "error", "Error de Sistema", f"Error accediendo al directorio: {e}"))
            return

        for nombre_subcarpeta in subdirectorios:
            ruta_subcarpeta = os.path.join(directorio_raiz, nombre_subcarpeta)
            if os.path.isdir(ruta_subcarpeta):
                nuevo_nombre_base_para_archivos = nombre_subcarpeta # Nombre de la subcarpeta

                try:
                    archivos_en_subcarpeta = os.listdir(ruta_subcarpeta)
                except (PermissionError, OSError) as e:
                    update_queue.put(("log", f"Error listando archivos en '{nombre_subcarpeta}': {e}"))
                    errores_count += 1
                    continue

                for nombre_archivo_original in archivos_en_subcarpeta:
                    ruta_archivo_original = os.path.join(ruta_subcarpeta, nombre_archivo_original)
                    archivos_procesados += 1
                    update_queue.put(("status", f"Procesando: {nombre_archivo_original} en {nombre_subcarpeta}"))

                    if os.path.isfile(ruta_archivo_original) and \
                       any(nombre_archivo_original.lower().endswith(ext) for ext in formatos_imagen):
                        
                        nombre_final_construido = None
                        extension_original = os.path.splitext(nombre_archivo_original)[1]

                        # Lógica original para determinar el nuevo nombre:
                        if "_" in nombre_archivo_original:
                            # Captura todo después del primer guion bajo
                            parte_sufijo = nombre_archivo_original.split('_', 1)[1]
                            nombre_final_construido = f"{nuevo_nombre_base_para_archivos}_{parte_sufijo}"
                        elif "-" in nombre_archivo_original: # Se ejecuta solo si no hay guion bajo
                            # Captura todo después del primer guion
                            parte_sufijo = nombre_archivo_original.split('-', 1)[1]
                            nombre_final_construido = f"{nuevo_nombre_base_para_archivos}-{parte_sufijo}"
                        else:
                            # No tiene sufijos _ ni -
                            nombre_final_construido = f"{nuevo_nombre_base_para_archivos}{extension_original}"
                        
                        ruta_archivo_nuevo = os.path.join(ruta_subcarpeta, nombre_final_construido)

                        if ruta_archivo_original != ruta_archivo_nuevo:
                            if os.path.exists(ruta_archivo_nuevo):
                                update_queue.put(("log", f"Conflicto: '{ruta_archivo_nuevo}' ya existe. Se omitió '{nombre_archivo_original}'."))
                                errores_count += 1 # Contando como un tipo de error/conflicto
                            else:
                                try:
                                    os.rename(ruta_archivo_original, ruta_archivo_nuevo)
                                    archivos_renombrados += 1
                                except PermissionError:
                                    update_queue.put(("log", f"Sin permisos para renombrar '{nombre_archivo_original}'"))
                                    errores_count += 1
                                except OSError as e_rename:
                                    update_queue.put(("log", f"Error del sistema renombrando '{nombre_archivo_original}': {e_rename}"))
                                    errores_count += 1
                                except Exception as e_rename:
                                    update_queue.put(("log", f"Error inesperado renombrando '{nombre_archivo_original}': {e_rename}"))
                                    errores_count += 1
                        # else: El nombre ya es correcto, no se hace nada.
        
        summary = f"Imágenes renombradas: {archivos_renombrados}.\nArchivos procesados: {archivos_procesados}.\nConflictos/Errores: {errores_count}."
        update_queue.put(("show_message", "info", "Proceso completado", summary))

    except Exception as e_global:
        update_queue.put(("show_message", "error", "Error Crítico", f"Ocurrió un error inesperado: {e_global}"))
    finally:
        update_queue.put(("finished", None)) # Señal para re-habilitar UI

# --- Interfaz Gráfica ---
# Clase base para compatibilidad
if TTKBOOTSTRAP_AVAILABLE:
    BaseWindow = ttk.Window
else:
    class BaseWindow(tk.Tk):
        def __init__(self):
            super().__init__()

class AppRenombradorSimple(BaseWindow):
    def __init__(self):
        super().__init__()
        
        # Aplicar tema solo si está disponible
        if THEME_AVAILABLE:
            try:
                setup_theme(self)
            except Exception as e:
                print(f"Warning: Could not apply theme: {e}")
        self.title("Renombrar Imágenes por Carpeta")
        self.geometry("500x220") # Ajustado para los widgets
        self.resizable(False, False)

        self.update_queue = queue.Queue()
        self.worker_thread = None

        # Variables de Tkinter
        self.status_var = tk.StringVar(value="Seleccione una carpeta para iniciar.")

        self._build_ui()
        self._process_gui_updates() # Iniciar el listener de la cola

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Seleccione la carpeta raíz que contiene las subcarpetas con imágenes:").pack(pady=(0,10), anchor=tk.W)
        
        # Configurar estilo del botón basado en disponibilidad de ttkbootstrap
        button_style = {}
        if TTKBOOTSTRAP_AVAILABLE:
            button_style = {"bootstyle": "success"}
            
        self.btn_seleccionar = ttk.Button(
            main_frame, 
            text="Seleccionar Carpeta y Renombrar", 
            command=self.seleccionar_y_procesar_carpeta,
            width=30,
            **button_style
        )
        self.btn_seleccionar.pack(pady=20)

        self.lbl_status = ttk.Label(main_frame, textvariable=self.status_var, anchor=tk.W)
        self.lbl_status.pack(pady=(10,0), fill=tk.X, expand=True)
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def seleccionar_y_procesar_carpeta(self):
        carpeta_seleccionada = filedialog.askdirectory(title="Seleccionar la carpeta raíz con subcarpetas de imágenes")
        if not carpeta_seleccionada:
            self.status_var.set("Operación cancelada por el usuario.")
            return

        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Proceso en curso", "Un proceso de renombrado ya está en ejecución.", parent=self)
            return

        # Deshabilitar botón usando el método correcto
        if TTKBOOTSTRAP_AVAILABLE:
            self.btn_seleccionar.config(state="disabled")
        else:
            self.btn_seleccionar.config(state=tk.DISABLED)
        self.status_var.set(f"Procesando carpeta: {os.path.basename(carpeta_seleccionada)}...")

        self.worker_thread = threading.Thread(
            target=renombrar_imagenes_en_hilo, 
            args=(carpeta_seleccionada, self.update_queue), 
            daemon=True
        )
        self.worker_thread.start()

    def _process_gui_updates(self):
        try:
            while True: # Procesar todos los mensajes disponibles
                msg_type, *data = self.update_queue.get_nowait()

                if msg_type == "status":
                    self.status_var.set(data[0])
                elif msg_type == "log": # Para mensajes de log más detallados (actualmente solo conflictos/errores)
                    print(f"LOG Interno: {data[0]}") # Se podría dirigir a un ScrolledText si fuera necesario
                    self.status_var.set(data[0]) # También actualiza el status principal
                elif msg_type == "show_message":
                    severity, title, message = data
                    if severity == "info":
                        messagebox.showinfo(title, message, parent=self)
                    elif severity == "error":
                        messagebox.showerror(title, message, parent=self)
                elif msg_type == "finished":
                    # Rehabilitar botón usando el método correcto
                    if TTKBOOTSTRAP_AVAILABLE:
                        self.btn_seleccionar.config(state="normal")
                    else:
                        self.btn_seleccionar.config(state=tk.NORMAL)
                    self.status_var.set("Listo. Puede seleccionar otra carpeta.")
                    self.worker_thread = None
        
        except queue.Empty: # No hay más mensajes
            pass
        finally:
            # Verificar si la ventana aún existe antes de programar el siguiente update
            try:
                if self.winfo_exists():
                    self.after(100, self._process_gui_updates) # Re-programar
            except tk.TclError:
                # La ventana ya fue destruida
                pass

    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Proceso en Curso", 
                                   "El proceso de renombrado está en curso. ¿Está seguro de que desea salir?",
                                   parent=self):
                # El hilo es daemon, terminará cuando la app principal se cierre.
                # No hay un mecanismo explícito de 'stop' para el hilo.
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    try:
        app = AppRenombradorSimple()
        app.mainloop()
    except Exception as e:
        print(f"Error iniciando la aplicación: {e}")
        # Mostrar un mensaje de error básico si tkinter funciona
        try:
            root = tk.Tk()
            root.withdraw()  # Ocultar ventana principal
            messagebox.showerror("Error", f"No se pudo iniciar la aplicación:\n{e}")
        except:
            print("Error crítico: No se puede mostrar interfaz gráfica")
        sys.exit(1)