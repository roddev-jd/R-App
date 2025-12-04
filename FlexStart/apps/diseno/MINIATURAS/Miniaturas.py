import os
import re
import time # Kept for watchdog, though the GUI won't use time.sleep in main thread
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText # For the log area
from PIL import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
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

# --- Constantes de la aplicación ---
TARGET_WIDTH = 125
TARGET_HEIGHT = 93
IDLE_TIMEOUT = 5  # Segundos para considerar que no hay más miniaturas por crear

# Configuración del filtro de remuestreo para Pillow
try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.LANCZOS

# --- Lógica de Transformación de Imágenes (sin cambios funcionales) ---
def transform_by_width(im: Image.Image) -> Image.Image:
    if im.mode not in ("RGB", "RGBA"): # Convert to RGBA to handle transparency, then to RGB for white bg
        im = im.convert("RGBA")
    
    background = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), (255, 255, 255))
    
    new_width = TARGET_WIDTH
    new_height = int(im.height * TARGET_WIDTH / im.width)
    im_resized = im.resize((new_width, new_height), RESAMPLE_FILTER)
    
    if new_height >= TARGET_HEIGHT:
        top = (new_height - TARGET_HEIGHT) // 2
        im_cropped_or_fitted = im_resized.crop((0, top, TARGET_WIDTH, top + TARGET_HEIGHT))
        background.paste(im_cropped_or_fitted, (0,0))
    else: # new_height < TARGET_HEIGHT (imagen más baja, añadir padding vertical)
        top_pad = (TARGET_HEIGHT - new_height) // 2
        # Paste im_resized (which is RGBA if original had alpha) onto RGB background
        # If im_resized has alpha, paste will use it as a mask.
        background.paste(im_resized, (0, top_pad), mask=im_resized if im_resized.mode == 'RGBA' else None)
        
    return background


def transform_by_height(im: Image.Image) -> Image.Image:
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")

    background = Image.new("RGB", (TARGET_WIDTH, TARGET_HEIGHT), (255, 255, 255))

    new_height = TARGET_HEIGHT
    new_width = int(im.width * TARGET_HEIGHT / im.height)
    im_resized = im.resize((new_width, new_height), RESAMPLE_FILTER)
    
    if new_width >= TARGET_WIDTH:
        left = (new_width - TARGET_WIDTH) // 2
        im_cropped_or_fitted = im_resized.crop((left, 0, left + TARGET_WIDTH, TARGET_HEIGHT))
        background.paste(im_cropped_or_fitted, (0,0))
    else: # new_width < TARGET_WIDTH (imagen más estrecha, añadir padding horizontal)
        left_pad = (TARGET_WIDTH - new_width) // 2
        background.paste(im_resized, (left_pad, 0), mask=im_resized if im_resized.mode == 'RGBA' else None)
        
    return background


# --- Manejador de Eventos de Watchdog ---
class ImageFileEventHandler(FileSystemEventHandler):
    def __init__(self, transformation_option_getter, gui_queue):
        super().__init__()
        self.transformation_option_getter = transformation_option_getter # Func to get current option
        self.gui_queue = gui_queue
        self.filename_pattern = re.compile(r"^(.*)_2(\.(jpg|png|webp))$", re.IGNORECASE)
        self.idle_timer = None
        self.last_processed_time = 0

    def _log_to_gui(self, message):
        self.gui_queue.put(("log", message))

    def _reset_idle_timer(self):
        """Reinicia el temporizador de inactividad"""
        if self.idle_timer:
            self.idle_timer.cancel()
        
        self.idle_timer = threading.Timer(IDLE_TIMEOUT, self._on_idle_timeout)
        self.idle_timer.daemon = True
        self.idle_timer.start()

    def _on_idle_timeout(self):
        """Se ejecuta cuando no hay más imágenes por procesar"""
        current_time = time.time()
        if current_time - self.last_processed_time >= IDLE_TIMEOUT:
            self._log_to_gui("no hay mas miniaturas por crear")

    def _process_image_file(self, file_path_str):
        if not os.path.isfile(file_path_str): # Ensure it's a file and still exists
            return

        base_name = os.path.basename(file_path_str)
        match = self.filename_pattern.match(base_name)

        if not match:
            # self._log_to_gui(f"Ignorado (no coincide patrón _2): {base_name}")
            return 

        output_filename_stem = match.group(1)
        output_extension = match.group(2) # Includes the dot, e.g., ".jpg"
        output_filename = f"{output_filename_stem}{output_extension}"
        output_path = os.path.join(os.path.dirname(file_path_str), output_filename)

        if os.path.exists(output_path):
            # self._log_to_gui(f"Ignorado (ya existe miniatura): {output_filename} para {base_name}")
            return

        current_transformation_option = self.transformation_option_getter()
        if not current_transformation_option: # Should not happen if UI validates
            self._log_to_gui("Error: Opción de transformación no establecida.")
            return

        try:
            with Image.open(file_path_str) as img:
                img.load() # Cargar datos de la imagen antes de que el archivo se cierre
                
                if current_transformation_option == "width":
                    transformed_img = transform_by_width(img)
                elif current_transformation_option == "height":
                    transformed_img = transform_by_height(img)
                else: # Fallback or error
                    self._log_to_gui(f"Error: Opción de transformación desconocida '{current_transformation_option}'.")
                    return

            transformed_img.save(output_path) # Pillow infers format from extension
            self._log_to_gui(f"Miniatura creada: {output_filename} (de {base_name})")
            
            # Actualizar tiempo de último procesamiento y reiniciar temporizador
            self.last_processed_time = time.time()
            self._reset_idle_timer()

        except FileNotFoundError: # Original _2 file might be gone if it's a temp file from save
            self._log_to_gui(f"Archivo '{base_name}' no encontrado durante el procesamiento (¿temporal?).")
        except Exception as e:
            self._log_to_gui(f"Error procesando '{base_name}': {e}")

    def on_created(self, event):
        if not event.is_directory:
            # Delay slightly to ensure file is fully written
            time.sleep(0) 
            self._process_image_file(event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory:
            # Delay slightly
            time.sleep(0.1) 
            self._process_image_file(event.src_path)

    def cleanup(self):
        """Limpia el temporizador al detener la monitorización"""
        if self.idle_timer:
            self.idle_timer.cancel()
            self.idle_timer = None


# --- Aplicación GUI (ttkbootstrap) ---
class ThumbnailerApp(ttk.Window):
    def __init__(self):
        super().__init__()
        setup_theme(self)
        self.title("Miniaturizador Mágico (ttkbootstrap)")
        self.geometry("750x500") # Adjusted size

        # --- Variables ---
        self.folder_path_var = tk.StringVar()
        self.transformation_option_var = tk.StringVar(value="width") # Opción por defecto
        self.status_var = tk.StringVar(value="Listo. Seleccione carpeta e inicie monitoreo.")
        
        self.update_queue = queue.Queue()
        self.watchdog_observer = None
        self.watchdog_event_handler = None # Será una instancia de ImageFileEventHandler
        self.filename_pattern = re.compile(r"^(.*)_2(\.(jpg|png|webp))$", re.IGNORECASE)

        self._build_ui()
        self._process_gui_updates_from_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)


    def _get_current_transformation_option(self):
        return self.transformation_option_var.get()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1) # Para que el Entry se expanda

        # --- Selección de Carpeta ---
        ttk.Label(main_frame, text="Carpeta a Monitorizar:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.folder_entry = ttk.Entry(main_frame, textvariable=self.folder_path_var, width=60, state=READONLY)
        self.folder_entry.grid(row=0, column=1, sticky=EW, padx=5, pady=5)
        self.browse_button = ttk.Button(main_frame, text="Seleccionar Carpeta", command=self._select_folder_action, bootstyle="outline-secondary")
        self.browse_button.grid(row=0, column=2, sticky=E, padx=5, pady=5)

        # --- Opciones de Transformación ---
        options_frame = ttk.LabelFrame(main_frame, text="Tipo de Transformación", bootstyle="info", padding=10)
        options_frame.grid(row=1, column=0, columnspan=3, sticky=EW, padx=5, pady=10)
        
        ttk.Radiobutton(options_frame, text="Escalar a lo Ancho (recorte vertical centrado)", 
                        variable=self.transformation_option_var, value="width", bootstyle="toolbutton").pack(side=LEFT, padx=5, expand=True, fill=X)
        ttk.Radiobutton(options_frame, text="Escalar a lo Alto (recorte horizontal centrado)", 
                        variable=self.transformation_option_var, value="height", bootstyle="toolbutton").pack(side=LEFT, padx=5, expand=True, fill=X)

        # --- Botones de Control ---
        control_buttons_frame = ttk.Frame(main_frame)
        control_buttons_frame.grid(row=2, column=0, columnspan=3, pady=10)
        
        self.start_button = ttk.Button(control_buttons_frame, text="Comenzar Monitorización", command=self._start_monitoring_action, bootstyle="success")
        self.start_button.pack(side=LEFT, padx=5)
        self.stop_button = ttk.Button(control_buttons_frame, text="Detener Monitorización", command=self._stop_monitoring_action, bootstyle="danger", state=DISABLED)
        self.stop_button.pack(side=LEFT, padx=5)

        # --- Área de Registro (Log) ---
        log_display_frame = ttk.LabelFrame(main_frame, text="Registro de Actividad", bootstyle="info", padding=10)
        log_display_frame.grid(row=3, column=0, columnspan=3, sticky=NSEW, padx=5, pady=5)
        main_frame.rowconfigure(3, weight=1) # Permitir que el log se expanda verticalmente
        
        self.log_area_scrolledtext = ScrolledText(log_display_frame, height=10, autohide=True, bd=0)
        self.log_area_scrolledtext.text.config(state=DISABLED, wrap=WORD)
        self.log_area_scrolledtext.pack(fill=BOTH, expand=True)

        # --- Etiqueta de Estado ---
        status_label = ttk.Label(main_frame, textvariable=self.status_var, anchor=W)
        status_label.grid(row=4, column=0, columnspan=3, sticky=EW, padx=5, pady=(10,0))

    def _select_folder_action(self):
        folder = filedialog.askdirectory(title="Seleccionar Carpeta a Monitorizar")
        if folder:
            self.folder_path_var.set(folder)
            self.status_var.set(f"Carpeta seleccionada. Listo para iniciar monitoreo.")
            self._add_log_message(f"Carpeta a monitorizar establecida en: {folder}")


    def _process_existing_files(self, folder):
        """Procesa archivos existentes en la carpeta antes de iniciar la monitorización"""
        self._add_log_message("Buscando archivos existentes en la carpeta...")
        processed_count = 0

        # Buscar recursivamente todos los archivos que coincidan con el patrón
        for root, _, files in os.walk(folder):
            for filename in files:
                if self.filename_pattern.match(filename):
                    file_path = os.path.join(root, filename)

                    # Verificar si ya existe la miniatura
                    match = self.filename_pattern.match(filename)
                    if match:
                        output_filename_stem = match.group(1)
                        output_extension = match.group(2)
                        output_filename = f"{output_filename_stem}{output_extension}"
                        output_path = os.path.join(root, output_filename)

                        if not os.path.exists(output_path):
                            # Procesar el archivo
                            if self.watchdog_event_handler:
                                self.watchdog_event_handler._process_image_file(file_path)
                                processed_count += 1

        if processed_count > 0:
            self._add_log_message(f"✓ Se procesaron {processed_count} archivo(s) existente(s)")
        else:
            self._add_log_message("No se encontraron archivos pendientes de procesar")

    def _start_monitoring_action(self):
        folder = self.folder_path_var.get()
        selected_option = self.transformation_option_var.get()

        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Error", "Por favor, seleccione una carpeta válida para monitorizar.", parent=self)
            return
        if not selected_option: # Aunque hay un valor por defecto, es una buena práctica verificar
            messagebox.showerror("Error", "Por favor, seleccione una opción de transformación.", parent=self)
            return

        if self.watchdog_observer and self.watchdog_observer.is_alive():
            messagebox.showwarning("Advertencia", "La monitorización ya está activa.", parent=self)
            return

        self.watchdog_event_handler = ImageFileEventHandler(self._get_current_transformation_option, self.update_queue)
        self.watchdog_observer = Observer()
        self.watchdog_observer.schedule(self.watchdog_event_handler, folder, recursive=True)

        try:
            self.watchdog_observer.start() # El observer corre en su propio hilo
            self.start_button.config(state=DISABLED)
            self.stop_button.config(state=NORMAL)
            self.browse_button.config(state=DISABLED) # Deshabilitar cambio de carpeta mientras monitorea
            # Deshabilitar radio buttons
            for child_frame in self.winfo_children():
                if isinstance(child_frame, ttk.Frame): # main_frame
                    for LFrame in child_frame.winfo_children():
                         if isinstance(LFrame, ttk.LabelFrame) and "Transformación" in LFrame.cget("text"):
                            for rb in LFrame.winfo_children():
                                if isinstance(rb, ttk.Radiobutton): rb.config(state=DISABLED)

            msg = f"Monitorización iniciada en: '{folder}' con opción: '{selected_option}'."
            self._add_log_message(msg)
            self.status_var.set("Monitorización activa...")

            # Procesar archivos existentes en un hilo separado para no bloquear la GUI
            threading.Thread(target=self._process_existing_files, args=(folder,), daemon=True).start()

        except Exception as e:
            self._add_log_message(f"Error al iniciar monitorización: {e}")
            messagebox.showerror("Error", f"No se pudo iniciar la monitorización: {e}", parent=self)
            self.watchdog_observer = None # Limpiar en caso de fallo


    def _stop_monitoring_action(self):
        if self.watchdog_observer and self.watchdog_observer.is_alive():
            try:
                # Limpiar el temporizador del event handler
                if self.watchdog_event_handler:
                    self.watchdog_event_handler.cleanup()
                
                self.watchdog_observer.stop()
                self.watchdog_observer.join() # Esperar a que el hilo del observer termine
                msg = "Monitorización detenida."
                self._add_log_message(msg)
                self.status_var.set(msg)
            except Exception as e:
                msg = f"Error al detener monitorización: {e}"
                self._add_log_message(msg)
                self.status_var.set(msg)
            finally:
                self.watchdog_observer = None
                self.watchdog_event_handler = None
                self.start_button.config(state=NORMAL)
                self.stop_button.config(state=DISABLED)
                self.browse_button.config(state=NORMAL)
                # Habilitar radio buttons
                for child_frame in self.winfo_children():
                    if isinstance(child_frame, ttk.Frame):
                        for LFrame in child_frame.winfo_children():
                            if isinstance(LFrame, ttk.LabelFrame) and "Transformación" in LFrame.cget("text"):
                                for rb in LFrame.winfo_children():
                                    if isinstance(rb, ttk.Radiobutton): rb.config(state=NORMAL)
        else:
            self.status_var.set("Monitorización no estaba activa.")
            # Asegurar estado correcto de botones si se llama erróneamente
            self.start_button.config(state=NORMAL)
            self.stop_button.config(state=DISABLED)
            self.browse_button.config(state=NORMAL)


    def _add_log_message(self, message: str):
        if self.log_area_scrolledtext.winfo_exists():
            self.log_area_scrolledtext.text.config(state=NORMAL)
            self.log_area_scrolledtext.text.insert(END, message + "\n")
            self.log_area_scrolledtext.text.see(END) # Auto-scroll
            self.log_area_scrolledtext.text.config(state=DISABLED)

    def _process_gui_updates_from_queue(self):
        try:
            while True: # Procesar todos los mensajes en la cola sin bloquear
                msg_type, data = self.update_queue.get_nowait()
                if msg_type == "log":
                    self._add_log_message(data)
                # Podrían añadirse otros tipos de mensajes si es necesario
        except queue.Empty:
            pass # Cola vacía
        finally:
            if self.winfo_exists(): # Re-programar solo si la ventana existe
                self.after(100, self._process_gui_updates_from_queue)

    def _on_window_close(self):
        if self.watchdog_observer and self.watchdog_observer.is_alive():
            if messagebox.askyesno("Confirmar Salida", 
                                   "La monitorización está activa. ¿Desea detenerla y salir?", 
                                   parent=self):
                self._stop_monitoring_action() # Intentar detener limpiamente
                self.destroy()
            # else: No cerrar si el usuario cancela
        else:
            self.destroy()


if __name__ == "__main__":
    app = ThumbnailerApp()
    app.mainloop()