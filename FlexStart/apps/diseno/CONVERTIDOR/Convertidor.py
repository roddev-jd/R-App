import os
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import * # ttkbootstrap constants
# ScrolledText is not explicitly requested for error logging, will stick to original error file.
# from ttkbootstrap.scrolled import ScrolledText
from PIL import Image
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

# --- Helper function for single file conversion (extracted and made standalone) ---
def convert_single_image_file(filepath, target_format_str):
    """
    Converts a single image file to the target format.
    Deletes the original if the new filename is different.
    Raises an exception on failure.
    """
    with Image.open(filepath) as img:
        original_mode = img.mode
        img_to_save = img

        # Handle transparency for JPG conversion
        if target_format_str.lower() == "jpg":
            if img.mode in ("RGBA", "LA", "P"): # P (palette) mode can also have transparency
                # Check for actual transparency in P mode before converting
                has_transparency_in_palette = False
                if img.mode == "P" and 'transparency' in img.info:
                    # Check if any transparent pixels are actually used (can be slow for many images)
                    # For simplicity, we assume if 'transparency' key exists, we should handle it.
                    has_transparency_in_palette = True

                if img.mode in ("RGBA", "LA") or has_transparency_in_palette:
                    try:
                        # Create a white background and paste the image with its alpha mask
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        # Ensure img has an alpha channel to use as a mask
                        if img.mode != 'RGBA':
                           img_with_alpha = img.convert('RGBA')
                        else:
                           img_with_alpha = img
                        background.paste(img_with_alpha, mask=img_with_alpha.split()[-1])
                        img_to_save = background
                    except Exception as e_alpha: # Fallback if alpha handling fails
                        # print(f"Alpha handling fallback for {filepath}: {e_alpha}")
                        img_to_save = img.convert("RGB")

                elif img.mode != "RGB": # If not RGBA/LA/P with transp, but also not RGB
                    img_to_save = img.convert("RGB")
        
        # WEBP specific: Pillow saves P mode WEBP as lossless by default.
        # If lossy is desired (usually for smaller files), convert from P to RGB/RGBA.
        # However, the original code didn't have WEBP specific quality settings, so keeping it simple.
        # if target_format_str.lower() == "webp" and img_to_save.mode == 'P':
        #    img_to_save = img_to_save.convert('RGB')


        directory, filename = os.path.split(filepath)
        base, _ = os.path.splitext(filename) # Original extension is discarded
        new_filename = f"{base}.{target_format_str.lower()}"
        new_filepath = os.path.join(directory, new_filename)

        # Save parameters can be added here if needed (e.g., quality for jpg/webp)
        save_params = {}
        if target_format_str.lower() == 'jpg':
            save_params['quality'] = 90 # Example quality
            save_params['optimize'] = True
        elif target_format_str.lower() == 'webp':
            save_params['quality'] = 85 # Example quality
            # save_params['lossless'] = False

        img_to_save.save(new_filepath, target_format_str.upper(), **save_params)

    # Delete original if conversion resulted in a new file name (different extension)
    # and the new file was successfully created.
    if os.path.abspath(filepath).lower() != os.path.abspath(new_filepath).lower():
        if os.path.exists(new_filepath): # Ensure new file was actually created
            os.remove(filepath)
        else:
            # This case should ideally not happen if img.save didn't raise error
            raise Exception(f"Nuevo archivo '{new_filename}' no fue creado después de guardar.")

# --- Helper function to add extensions to files without extensions ---
def add_extension_to_file(filepath, target_format_str):
    """
    Adds extension to a file that doesn't have one.
    Verifies the file is a valid image first.
    Returns the new filepath if successful, raises exception on failure.
    """
    # First, verify it's a valid image
    try:
        with Image.open(filepath) as img:
            # Just opening is enough to verify it's a valid image
            pass
    except Exception as e:
        raise Exception(f"No es una imagen válida: {e}")
    
    # Add the extension
    directory, filename = os.path.split(filepath)
    new_filename = f"{filename}.{target_format_str.lower()}"
    new_filepath = os.path.join(directory, new_filename)
    
    # Check if a file with that name already exists
    if os.path.exists(new_filepath):
        raise Exception(f"Ya existe un archivo llamado '{new_filename}'")
    
    # Rename the file
    os.rename(filepath, new_filepath)
    return new_filepath

# --- Worker function for threading ---
def conversion_worker_thread(folder_path_str, target_format_str, update_queue):
    image_extensions = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff")
    files_to_convert = []
    files_to_add_extension = []
    errors_this_run = []
    files_converted_count = 0
    files_extension_added_count = 0

    update_queue.put(("status", "Buscando imágenes para convertir..."))
    for root, _, files in os.walk(folder_path_str):
        for file in files:
            filepath = os.path.join(root, file)
            base, ext = os.path.splitext(file)
            
            # Check if file has an extension
            if ext:
                # File has an extension
                if file.lower().endswith(image_extensions):
                    # Si la extensión del archivo ya es igual al formato de destino,
                    # se usa 'continue' para saltar este archivo y pasar al siguiente en el bucle.
                    if ext.lower() == f".{target_format_str.lower()}":
                        continue
                    
                    # Esta línea solo se ejecutará para archivos que SÍ necesitan conversión.
                    files_to_convert.append(filepath)
            else:
                # File has no extension - candidate for adding extension
                files_to_add_extension.append(filepath)

    total_files_to_add_ext = len(files_to_add_extension)
    total_files_to_convert = len(files_to_convert)
    total_files = total_files_to_add_ext + total_files_to_convert
    
    if total_files == 0:
        # Mensaje actualizado para mayor claridad.
        update_queue.put(("log", "No se encontraron imágenes que necesiten conversión al formato deseado."))
        update_queue.put(("finished", {'has_errors': False, 'report_path': None, 'total_files': 0, 'converted_count':0, 'errors_count': 0}))
        return

    update_queue.put(('progress_max', total_files))
    update_queue.put(('log', f"Se encontraron {total_files_to_add_ext} archivos sin extensión y {total_files_to_convert} imágenes para convertir."))

    current_progress = 0
    
    # First, process files that need extensions added
    for filepath in files_to_add_extension:
        current_progress += 1
        original_filename = os.path.basename(filepath)
        update_queue.put(('status', f"Agregando extensión: {original_filename} ({current_progress}/{total_files})"))
        try:
            new_filepath = add_extension_to_file(filepath, target_format_str)
            files_extension_added_count += 1
            update_queue.put(('log', f"✓ Extensión agregada: {original_filename} → {os.path.basename(new_filepath)}"))
        except Exception as e:
            err_msg = f"Error al agregar extensión a {original_filename}: {e}"
            errors_this_run.append(err_msg)
            update_queue.put(('log', err_msg))
        update_queue.put(('progress_update', current_progress))

    # Then, process regular conversions
    for filepath in files_to_convert:
        current_progress += 1
        original_filename = os.path.basename(filepath)
        update_queue.put(('status', f"Convirtiendo: {original_filename} ({current_progress}/{total_files})"))
        try:
            convert_single_image_file(filepath, target_format_str)
            files_converted_count += 1
        except Exception as e:
            err_msg = f"Error al convertir {original_filename}: {e}"
            errors_this_run.append(err_msg)
            update_queue.put(('log', err_msg))
        update_queue.put(('progress_update', current_progress))

    report_file_path = None
    if errors_this_run:
        try:
            report_file_path = os.path.join(folder_path_str, "conversion_errors.txt")
            with open(report_file_path, "w", encoding="utf-8") as f_report:
                f_report.write("Errores durante el procesamiento de imágenes:\n\n")
                for error in errors_this_run:
                    f_report.write(error + "\n")
            update_queue.put(('log', f"Reporte de errores guardado en: {report_file_path}"))
        except Exception as e_report:
            update_queue.put(('log', f"CRÍTICO: No se pudo escribir el reporte de errores: {e_report}"))
            report_file_path = f"FALLÓ ESCRITURA DE REPORTE ({e_report})"

    update_queue.put(('finished', {
        'has_errors': bool(errors_this_run), 
        'report_path': report_file_path,
        'total_files': total_files,
        'converted_count': files_converted_count,
        'extension_added_count': files_extension_added_count,
        'errors_count': len(errors_this_run)
    }))


# --- GUI Application (ttkbootstrap) ---
class ImageFormatConverterApp(ttk.Window):
    def __init__(self):
        super().__init__()
        setup_theme(self)
        self.title("Convertidor de Formatos de Imágenes (ttkbootstrap)")
        self.geometry("650x300") # Adjusted size

        # Variables
        self.folder_path_var = tk.StringVar()
        self.target_format_var = tk.StringVar(value="jpg")  # Formato por defecto
        self.status_var = tk.StringVar(value="Listo para convertir.")
        
        self.update_queue = queue.Queue()
        self.worker_thread = None

        self._build_ui()
        self._process_queue_updates() # Start queue listener

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1) # Allow entry to expand

        # Selección de carpeta
        ttk.Label(main_frame, text="Carpeta de Imágenes:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.entry_folder = ttk.Entry(main_frame, textvariable=self.folder_path_var, width=50, state=READONLY)
        self.entry_folder.grid(row=0, column=1, padx=5, pady=5, sticky=EW)
        self.btn_browse_folder = ttk.Button(main_frame, text="Seleccionar...", command=self.browse_folder, bootstyle="outline-secondary")
        self.btn_browse_folder.grid(row=0, column=2, padx=5, pady=5, sticky=E)

        # Selección del formato destino
        ttk.Label(main_frame, text="Formato Destino:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        frame_formats = ttk.Frame(main_frame)
        frame_formats.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=W)
        
        formats = ["jpg", "png", "webp"]
        for fmt in formats:
            # Using "outline-toolbutton" for a toggle group appearance
            rb = ttk.Radiobutton(frame_formats, text=fmt.upper(), variable=self.target_format_var, value=fmt, bootstyle="outline-toolbutton")
            rb.pack(side=LEFT, padx=(0, 5))
        # self.target_format_var.set("jpg") # Ensure default is selected visually if needed, though StringVar has value

        # Botón para comenzar la conversión
        self.button_convert = ttk.Button(main_frame, text="Iniciar Conversión", command=self.start_conversion_process, bootstyle="success", width=20)
        self.button_convert.grid(row=2, column=0, columnspan=3, padx=5, pady=15)

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(main_frame, orient=HORIZONTAL, length=100, mode=DETERMINATE, bootstyle="info-striped")
        self.progress_bar.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky=EW)

        # Etiqueta de estado
        self.label_status = ttk.Label(main_frame, textvariable=self.status_var, anchor=W)
        self.label_status.grid(row=4, column=0, columnspan=3, padx=5, pady=(10,0), sticky=EW)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)


    def browse_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar Carpeta con Imágenes")
        if folder:
            self.folder_path_var.set(folder)
            self.status_var.set(f"Carpeta: {os.path.basename(folder)}")

    def start_conversion_process(self):
        folder = self.folder_path_var.get()
        if not folder:
            messagebox.showwarning("Advertencia", "Por favor, seleccione una carpeta.", parent=self)
            return
        
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Proceso en Curso", "La conversión ya está en ejecución.", parent=self)
            return

        target_format = self.target_format_var.get()

        self.button_convert.config(state=DISABLED)
        self.btn_browse_folder.config(state=DISABLED) # Disable folder selection too
        self.progress_bar["value"] = 0
        self.status_var.set("Iniciando conversión...")
        # Consider adding a ScrolledText for detailed logs if many errors are expected.
        # For now, sticking to original error file + messagebox.

        self.worker_thread = threading.Thread(
            target=conversion_worker_thread,
            args=(folder, target_format, self.update_queue),
            daemon=True
        )
        self.worker_thread.start()

    def _process_queue_updates(self):
        try:
            while True: # Process all available messages
                msg_type, data = self.update_queue.get_nowait()

                if msg_type == "progress_max":
                    self.progress_bar["maximum"] = data if data > 0 else 100
                elif msg_type == "progress_update":
                    self.progress_bar["value"] = data
                elif msg_type == "status":
                    self.status_var.set(data)
                elif msg_type == "log": # Individual log messages (can be errors or successes)
                    # For now, just print to console or update status briefly
                    # A ScrolledText area would be better for a list of these.
                    print(f"WORKER LOG: {data}") 
                elif msg_type == "finished":
                    self._handle_conversion_finished(data)
        
        except queue.Empty: # No more messages
            pass
        finally:
            if self.winfo_exists(): # Check if window still exists
                self.after(100, self._process_queue_updates) # Poll again

    def _handle_conversion_finished(self, results_data):
        self.button_convert.config(state=NORMAL)
        self.btn_browse_folder.config(state=NORMAL)
        self.progress_bar["value"] = self.progress_bar["maximum"] # Fill bar on completion
        self.worker_thread = None

        has_errors = results_data['has_errors']
        report_path = results_data['report_path']
        total_files = results_data['total_files']
        converted_count = results_data['converted_count']
        extension_added_count = results_data.get('extension_added_count', 0)
        errors_count = results_data['errors_count']
        
        final_status_msg = f"Procesamiento finalizado. Total: {total_files}, Extensiones agregadas: {extension_added_count}, Convertidos: {converted_count}, Errores: {errors_count}."
        self.status_var.set(final_status_msg)

        if has_errors:
            msg = f"Algunas operaciones fallaron ({errors_count} errores).\n"
            if report_path and "FALLÓ ESCRITURA" not in report_path :
                 msg += f"Revise el reporte para más detalles:\n{report_path}"
            elif report_path: # Report writing failed
                msg += f"Además, {report_path}"
            else: # No errors, but no report path implies no errors were written
                msg += "No se generó un archivo de reporte específico (puede que no hubiera errores que escribir o falló la escritura)."
            messagebox.showwarning("Procesamiento Completado con Errores", msg, parent=self)
        else:
            if total_files > 0 : # Only show success if files were actually processed
                success_msg = f"Procesamiento completado exitosamente:\n"
                if extension_added_count > 0:
                    success_msg += f"• {extension_added_count} archivo(s) con extensión agregada\n"
                if converted_count > 0:
                    success_msg += f"• {converted_count} imagen(es) convertida(s)"
                messagebox.showinfo("Procesamiento Completado", success_msg, parent=self)
            else:
                messagebox.showinfo("Información", "No se procesaron imágenes (0 encontradas o elegibles).", parent=self)

                
    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Proceso en Curso", 
                                   "La conversión de imágenes está en curso. ¿Está seguro de que desea salir?",
                                   parent=self):
                # Worker thread is daemon, will exit with app.
                # Consider adding a stop event to the worker for cleaner shutdown if operations are critical.
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = ImageFormatConverterApp()
    app.mainloop()