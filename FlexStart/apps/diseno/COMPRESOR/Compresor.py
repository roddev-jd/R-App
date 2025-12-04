import os
import io
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import * # For constants like LEFT, RIGHT, X, Y, NORMAL, DISABLED, INFO, SUCCESS etc.
from ttkbootstrap.scrolled import ScrolledText
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

# --- Lógica de Compresión WEBP ---
def _compress_single_webp(image_obj: Image.Image, size_threshold_bytes: int, min_quality: int = 10, initial_quality: int = 90, compression_method: int = 6) -> bytes | None:
    low = min_quality
    high = initial_quality
    best_image_bytes = None

    img_to_compress = image_obj
    if img_to_compress.mode == 'P' and 'transparency' in img_to_compress.info:
        img_to_compress = image_obj.convert('RGBA')
    elif img_to_compress.mode == 'LA': # LA (Luminance Alpha) a RGBA
        img_to_compress = image_obj.convert('RGBA')

    while low <= high:
        current_quality = (low + high) // 2
        if current_quality == 0: 
            current_quality = 1 
            
        buffer = io.BytesIO()
        try:
            img_to_compress.save(buffer, format="WEBP", quality=current_quality, method=compression_method)
            current_size = buffer.tell()

            if current_size <= size_threshold_bytes:
                best_image_bytes = buffer.getvalue()
                low = current_quality + 1
            else:
                high = current_quality - 1
        except Exception as e:
            high = current_quality - 1
            if low > high and best_image_bytes is None: 
                return None 
    return best_image_bytes

# --- Worker en Hilo ---
def compression_worker(folder_path: str, threshold_kb: int, update_queue: queue.Queue):
    size_threshold_bytes = threshold_kb * 1024
    images_to_scan = []
    files_processed_count = 0
    files_compressed_count = 0
    files_skipped_count = 0
    error_details = [] 

    update_queue.put(("log", f"Iniciando escaneo de imágenes WEBP en: {folder_path}"))
    update_queue.put(("status", "Escaneando archivos..."))

    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(".webp"):
                images_to_scan.append(os.path.join(root, file))
    
    total_images_to_scan = len(images_to_scan)
    if total_images_to_scan == 0:
        update_queue.put(("log", "No se encontraron archivos .webp en la ruta especificada."))
        update_queue.put(("finished", {"total":0, "compressed":0, "skipped":0, "errors":0, "error_details":[]}))
        return

    update_queue.put(("progress_max", total_images_to_scan))
    update_queue.put(("log", f"Se encontraron {total_images_to_scan} imágenes .webp para analizar."))

    for idx, img_path in enumerate(images_to_scan):
        files_processed_count += 1
        base_name = os.path.basename(img_path)
        update_queue.put(("progress_value", idx + 1))
        update_queue.put(("status", f"Procesando: {base_name} ({idx+1}/{total_images_to_scan})"))

        try:
            original_size = os.path.getsize(img_path)
            if original_size <= size_threshold_bytes:
                update_queue.put(("log", f"OMITIDO (ya cumple): {base_name} ({original_size/1024:.2f} KB)"))
                files_skipped_count += 1
                continue

            with Image.open(img_path) as img_obj:
                compressed_bytes = _compress_single_webp(img_obj, size_threshold_bytes)

            if compressed_bytes:
                with open(img_path, "wb") as f_out:
                    f_out.write(compressed_bytes)
                new_size = len(compressed_bytes)
                update_queue.put(("log", f"COMPRIMIDO: {base_name} (de {original_size/1024:.2f} KB a {new_size/1024:.2f} KB)"))
                files_compressed_count += 1
            else:
                error_msg = f"No se pudo comprimir por debajo de {threshold_kb} KB."
                update_queue.put(("log", f"ERROR ({error_msg}): {base_name}"))
                error_details.append({"file": img_path, "error": error_msg})
        except FileNotFoundError:
            error_msg = "Archivo no encontrado."
            update_queue.put(("log", f"ERROR ({error_msg}): {base_name}."))
            error_details.append({"file": img_path, "error": error_msg})
        except Exception as e:
            error_msg = f"Error inesperado: {e}"
            update_queue.put(("log", f"ERROR (procesando {base_name}): {error_msg}"))
            error_details.append({"file": img_path, "error": error_msg})
            
    results = {
        "total": total_images_to_scan,
        "compressed": files_compressed_count,
        "skipped": files_skipped_count,
        "errors": len(error_details),
        "error_details": error_details
    }
    update_queue.put(("finished", results))

# --- Aplicación GUI ---
class WebpCompressorApp(ttk.Window):
    def __init__(self):
        super().__init__()
        setup_theme(self)
        self.title("Compresor WEBP por Umbral")
        self.geometry("750x600")

        self.folder_path_var = tk.StringVar()
        self.threshold_var = tk.IntVar(value=150) 

        self.update_queue = queue.Queue()
        self.worker_thread = None

        self._build_ui()
        self._process_queue()

    def _build_ui(self):
        main_padding = {"padx": 15, "pady": 10}
        widget_padding = {"pady": 5, "padx": 5}

        main_frame = ttk.Frame(self, padding=main_padding["padx"])
        main_frame.pack(fill=BOTH, expand=True)

        settings_frame = ttk.LabelFrame(main_frame, text="Configuración de Compresión", bootstyle="info", padding=15) # CORRECTED
        settings_frame.pack(fill=X, pady=(0, main_padding["pady"]))
        settings_frame.columnconfigure(1, weight=1) 

        ttk.Label(settings_frame, text="Carpeta de Imágenes:").grid(row=0, column=0, sticky=W, **widget_padding)
        self.folder_entry = ttk.Entry(settings_frame, textvariable=self.folder_path_var, state=READONLY, width=60)
        self.folder_entry.grid(row=0, column=1, sticky=EW, **widget_padding)
        self.browse_button = ttk.Button(settings_frame, text="Examinar...", command=self._select_folder, bootstyle="outline-secondary") # CORRECTED
        self.browse_button.grid(row=0, column=2, sticky=E, **widget_padding)

        ttk.Label(settings_frame, text="Umbral Máximo:").grid(row=1, column=0, sticky=W, **widget_padding)
        threshold_options_frame = ttk.Frame(settings_frame)
        threshold_options_frame.grid(row=1, column=1, columnspan=2, sticky=EW, **widget_padding)
        
        threshold_values = [("100 KB", 100), ("150 KB", 150), ("200 KB", 200)]
        for i, (text, val) in enumerate(threshold_values):
            rb = ttk.Radiobutton(threshold_options_frame, text=text, variable=self.threshold_var, value=val, bootstyle="toolbutton")
            rb.pack(side=LEFT, padx=(0, 10))
            if val == 150: 
                 rb.invoke()

        self.start_button = ttk.Button(main_frame, text="Iniciar Compresión", command=self._start_compression, bootstyle="success", width=25) # CORRECTED
        self.start_button.pack(pady=main_padding["pady"])

        ttk.Label(main_frame, text="Progreso General:").pack(fill=X, anchor=W, padx=widget_padding["padx"])
        self.progress_bar = ttk.Progressbar(main_frame, mode=DETERMINATE, bootstyle="info-striped") # CORRECTED
        self.progress_bar.pack(fill=X, pady=widget_padding["pady"], padx=widget_padding["padx"])

        log_frame = ttk.LabelFrame(main_frame, text="Registro de Actividad", bootstyle="info", padding=10) # CORRECTED
        log_frame.pack(fill=BOTH, expand=True, pady=(main_padding["pady"], 0))
        
        self.log_area = ScrolledText(log_frame, height=10, autohide=True, bd=0) 
        self.log_area.text.config(state=DISABLED, wrap=WORD) 
        self.log_area.pack(fill=BOTH, expand=True)

        self.status_var = tk.StringVar(value="Listo. Seleccione una carpeta y umbral.")
        ttk.Label(main_frame, textvariable=self.status_var, anchor=W).pack(fill=X, pady=(main_padding["pady"],0), padx=widget_padding["padx"])
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _select_folder(self):
        path = filedialog.askdirectory(title="Seleccionar Carpeta Raíz con Imágenes WEBP")
        if path:
            self.folder_path_var.set(path)
            self.status_var.set(f"Carpeta seleccionada: {os.path.basename(path)}")

    def _start_compression(self):
        folder = self.folder_path_var.get()
        threshold = self.threshold_var.get()

        if not folder:
            messagebox.showwarning("Entrada Faltante", "Por favor, seleccione una carpeta.", parent=self)
            return
        
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Proceso en Curso", "La compresión ya está en ejecución.", parent=self)
            return

        self.start_button.config(state=DISABLED)
        self.browse_button.config(state=DISABLED) 
        self.progress_bar['value'] = 0 # Ensure progress bar var is also reset if not bound
        self.log_area.text.config(state=NORMAL)
        self.log_area.text.delete("1.0", END)
        self.log_area.text.config(state=DISABLED)
        self._add_to_log_area(f"Iniciando compresión para archivos mayores a {threshold} KB...")
        self.status_var.set("Procesando...")

        self.worker_thread = threading.Thread(
            target=compression_worker,
            args=(folder, threshold, self.update_queue),
            daemon=True
        )
        self.worker_thread.start()

    def _add_to_log_area(self, message: str):
        if self.log_area.winfo_exists():
            self.log_area.text.config(state=NORMAL)
            self.log_area.text.insert(END, message + "\n")
            self.log_area.text.see(END)
            self.log_area.text.config(state=DISABLED)

    def _process_queue(self):
        try:
            while True:
                msg_type, data = self.update_queue.get_nowait()

                if msg_type == "log":
                    self._add_to_log_area(data)
                elif msg_type == "status":
                    self.status_var.set(data)
                elif msg_type == "progress_max":
                    self.progress_bar["maximum"] = data if data > 0 else 100 
                elif msg_type == "progress_value":
                    # For ttk.Progressbar not bound to a tk.DoubleVar, set value directly
                    current_val = data
                    max_val = self.progress_bar["maximum"]
                    self.progress_bar["value"] = current_val 
                    # If you bound it to self.progress_bar_var, you'd set self.progress_bar_var.set(percentage_or_value)
                elif msg_type == "finished":
                    self._on_compression_finished(data)
        except queue.Empty:
            pass 
        finally:
            if self.winfo_exists(): 
                self.after(100, self._process_queue)

    def _on_compression_finished(self, results: dict):
        self.start_button.config(state=NORMAL)
        self.browse_button.config(state=NORMAL) 
        self.progress_bar["value"] = self.progress_bar["maximum"] 
        
        errors_found = results.get('errors', 0)
        error_details = results.get('error_details', [])

        summary = (
            f"--- Compresión Finalizada ---\n"
            f"Imágenes Analizadas: {results.get('total', 0)}\n"
            f"Imágenes Comprimidas: {results.get('compressed', 0)}\n"
            f"Imágenes Omitidas (ya cumplían): {results.get('skipped', 0)}\n"
            f"Errores: {errors_found}"
        )
        self._add_to_log_area(summary)
        self.status_var.set("Proceso completado. Listo.")
        messagebox.showinfo("Proceso Completado", summary, parent=self)

        if errors_found > 0:
            if messagebox.askyesno("Reporte de Errores", 
                                   f"Se encontraron {errors_found} errores. ¿Desea guardar un reporte detallado?",
                                   parent=self):
                self._save_error_report(error_details)

        self.worker_thread = None

    def _save_error_report(self, error_details: list):
        report_path = filedialog.asksaveasfilename(
            title="Guardar Reporte de Errores",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile="reporte_de_compresion.txt"
        )
        if not report_path:
            return

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("--- Reporte de Errores de Compresión ---\n\n")
                for error in error_details:
                    f.write(f"Archivo: {error['file']}\n")
                    f.write(f"  Error: {error['error']}\n\n")
            messagebox.showinfo("Reporte Guardado", f"El reporte ha sido guardado en: {report_path}", parent=self)
        except Exception as e:
            messagebox.showerror("Error al Guardar", f"No se pudo guardar el reporte: {e}", parent=self)

    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Proceso en Curso", 
                                   "La compresión está en curso. ¿Está seguro de que desea salir?",
                                   parent=self):
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = WebpCompressorApp()
    app.mainloop()