import os
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import * # For ttkbootstrap constants
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

# --- Worker function for image rotation (runs in a separate thread) ---
def rotation_worker(directory_path: str, angle_to_rotate: int, update_queue: queue.Queue):
    """
    Scans for images and rotates them, sending updates via the queue.
    """
    image_paths = []
    errors_list = []

    update_queue.put(("status", "Buscando imágenes..."))
    for root_dir, _, files in os.walk(directory_path):
        for file_name in files:
            if file_name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                full_path = os.path.join(root_dir, file_name)
                image_paths.append(full_path)

    total_images = len(image_paths)
    if total_images == 0:
        update_queue.put(("log", "No se encontraron imágenes en el directorio seleccionado."))
        update_queue.put(("finished", {'total': 0, 'processed': 0, 'errors': []}))
        return

    update_queue.put(("progress_max", total_images))
    update_queue.put(("log", f"Se encontraron {total_images} imágenes para rotar."))
    
    processed_count = 0
    for idx, img_path in enumerate(image_paths, start=1):
        update_queue.put(("status", f"Procesando: {os.path.basename(img_path)} ({idx}/{total_images})"))
        try:
            with Image.open(img_path) as img:
                # Ensure image is loaded before closing file, especially for formats that load lazily
                img.load() 
                # Rotate the image. expand=True ensures the entire rotated image is visible.
                rotated_img = img.rotate(angle_to_rotate, expand=True)
                # Overwrite the original file with the rotated image
                # Make sure to save with original format if possible, or handle format-specific options
                # For simplicity, Pillow's save usually infers format from extension or uses original if not specified.
                rotated_img.save(img_path) # This will try to save in the original format
            processed_count += 1
        except Exception as e:
            error_msg = f"Error procesando '{img_path}': {e}"
            errors_list.append(error_msg)
            update_queue.put(("log", error_msg)) # Log individual errors
        
        update_queue.put(("progress_value", idx))

    update_queue.put(("finished", {
        'total': total_images, 
        'processed': processed_count, 
        'errors': errors_list
    }))


# --- GUI Application (ttkbootstrap) ---
class ImageRotatorBatchApp(ttk.Window):
    def __init__(self):
        super().__init__()
        setup_theme(self)
        self.title("Rotador de Imágenes por Lotes (ttkbootstrap)")
        self.geometry("600x320") # Adjusted size
        self.resizable(False, False)

        # --- Variables ---
        self.selected_directory_path = None # Stores the actual path
        self.directory_display_var = tk.StringVar(value="Directorio: Ninguno")
        
        self.rotation_angle_var = tk.IntVar() # Holds the selected angle value (e.g., 90, -90)
        self.angle_display_var = tk.StringVar(value="Ángulo seleccionado: Ninguno")
        
        self.status_var = tk.StringVar(value="Listo.")
        
        self.update_queue = queue.Queue()
        self.worker_thread = None

        self._build_ui()
        self._process_queue_updates() # Start listening to the queue

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # --- Selección de Directorio ---
        dir_frame = ttk.Frame(main_frame)
        dir_frame.pack(fill=X, pady=(0,10))
        dir_frame.columnconfigure(1, weight=1) # Allow label to expand

        self.btn_select_dir = ttk.Button(dir_frame, text="Seleccionar Directorio", 
                                         command=self.select_directory_action, bootstyle="outline-secondary")
        self.btn_select_dir.grid(row=0, column=0, padx=(0,10), sticky=W)
        
        lbl_selected_dir = ttk.Label(dir_frame, textvariable=self.directory_display_var, anchor=W)
        lbl_selected_dir.grid(row=0, column=1, sticky=EW)

        # --- Selección de Ángulo de Rotación (usando Radiobuttons) ---
        angle_group_frame = ttk.LabelFrame(main_frame, text="Ángulo de Rotación", bootstyle="info", padding=10)
        angle_group_frame.pack(fill=X, pady=10)

        angles = [
            ("Rotar -90° (Izquierda)", -90), 
            ("Rotar 90° (Derecha)", 90), 
            ("Rotar 180°", 180) 
            # ("Rotar -180°", -180) # -180 is same as 180, so usually one is enough
        ]
        # Ensure radiobuttons share the same variable but have unique values
        for i, (text, angle_val) in enumerate(angles):
            rb = ttk.Radiobutton(angle_group_frame, text=text, variable=self.rotation_angle_var, 
                                 value=angle_val, command=self._update_selected_angle_display, 
                                 bootstyle="toolbutton") # "toolbutton" gives a nice toggle look
            # Pack them horizontally
            rb.pack(side=LEFT, padx=5, pady=5, fill=X, expand=True)
            # Default selection (optional, e.g. 90 degrees)
            # if angle_val == 90:
            #    self.rotation_angle_var.set(90)
            #    self._update_selected_angle_display() # Update label if default is set


        # Etiqueta para mostrar el ángulo seleccionado
        lbl_selected_angle = ttk.Label(main_frame, textvariable=self.angle_display_var)
        lbl_selected_angle.pack(pady=5)

        # --- Botón de Procesar ---
        self.btn_process_images = ttk.Button(main_frame, text="Comenzar Rotación", 
                                           command=self.start_image_processing, bootstyle="success", width=20)
        self.btn_process_images.pack(pady=10)

        # --- Barra de Progreso y Estado ---
        self.progress_bar = ttk.Progressbar(main_frame, orient=HORIZONTAL, length=100, mode=DETERMINATE, bootstyle="info-striped")
        self.progress_bar.pack(fill=X, pady=5, padx=5)
        
        lbl_current_status = ttk.Label(main_frame, textvariable=self.status_var, anchor=W)
        lbl_current_status.pack(fill=X, pady=(5,0), padx=5)

        self.protocol("WM_DELETE_WINDOW", self._on_closing)


    def select_directory_action(self):
        directory = filedialog.askdirectory(title="Selecciona el directorio con imágenes")
        if directory:
            self.selected_directory_path = directory # Store the raw path
            # Display a shorter version or the full path as needed
            display_path = directory if len(directory) < 60 else "..." + directory[-57:]
            self.directory_display_var.set(f"Directorio: {display_path}")
            self.status_var.set(f"Directorio seleccionado. Elija ángulo y comience.")

    def _update_selected_angle_display(self):
        angle = self.rotation_angle_var.get()
        # Check if an angle is actually selected (value might be 0 if not set, or default Intvar value)
        # However, Radiobutton selection ensures rotation_angle_var gets one of the defined values.
        self.angle_display_var.set(f"Ángulo seleccionado: {angle}°")


    def start_image_processing(self):
        if not self.selected_directory_path:
            messagebox.showerror("Error", "Primero seleccione un directorio.", parent=self)
            return
        
        # rotation_angle_var will have a value if a radiobutton is selected.
        # If no radiobutton was ever selected, it might be 0 (default for IntVar).
        # We should ensure an angle is chosen.
        try:
            angle_to_rotate = self.rotation_angle_var.get()
            if angle_to_rotate == 0 and not any(rb.cget("value") == 0 for rb_group in self.winfo_children() if isinstance(rb_group, ttk.LabelFrame) for rb in rb_group.winfo_children() if isinstance(rb, ttk.Radiobutton) ): # Check if 0 is a valid choice if any rb had value 0
                 # This check is a bit complex if 0 is never a valid angle choice from radio buttons.
                 # Simpler: check if an angle has been set by a selection beyond IntVar's default.
                 # The easiest is to initialize rotation_angle_var with a non-selectable value or check if its value is one of the valid choices.
                 # For now, assume get() gives a valid selected angle if any radiobutton was clicked.
                 # If no radiobutton is selected by default and none clicked, get() might be 0.
                pass # If 0 is a valid selectable angle, allow. Otherwise, need better check.
        except tk.TclError: # Happens if rotation_angle_var has no selection yet
            messagebox.showerror("Error", "Primero seleccione un ángulo de rotación.", parent=self)
            return
        
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Proceso en Curso", "El proceso de rotación ya está en ejecución.", parent=self)
            return

        self.btn_process_images.config(state=DISABLED)
        self.btn_select_dir.config(state=DISABLED)
        # Disable angle radiobuttons during processing
        for child in self.winfo_children():
            if isinstance(child, ttk.LabelFrame) and "Ángulo" in child.cget("text"):
                for rb in child.winfo_children():
                    if isinstance(rb, ttk.Radiobutton):
                        rb.config(state=DISABLED)

        self.progress_bar["value"] = 0
        self.status_var.set("Iniciando rotación...")

        self.worker_thread = threading.Thread(
            target=rotation_worker,
            args=(self.selected_directory_path, self.rotation_angle_var.get(), self.update_queue),
            daemon=True
        )
        self.worker_thread.start()

    def _process_queue_updates(self):
        try:
            while True: # Process all available messages
                msg_type, data = self.update_queue.get_nowait()

                if msg_type == "progress_max":
                    self.progress_bar["maximum"] = data if data > 0 else 100
                elif msg_type == "progress_value":
                    self.progress_bar["value"] = data
                elif msg_type == "status":
                    self.status_var.set(data)
                elif msg_type == "log": 
                    print(f"WORKER LOG: {data}") # For now, print. Could go to a ScrolledText.
                elif msg_type == "finished":
                    self._handle_rotation_finished(data)
        
        except queue.Empty: # No more messages
            pass
        finally:
            if self.winfo_exists():
                self.after(100, self._process_queue_updates)

    def _handle_rotation_finished(self, results_data):
        self.btn_process_images.config(state=NORMAL)
        self.btn_select_dir.config(state=NORMAL)
        # Re-enable angle radiobuttons
        for child in self.winfo_children():
            if isinstance(child, ttk.LabelFrame) and "Ángulo" in child.cget("text"):
                for rb in child.winfo_children():
                    if isinstance(rb, ttk.Radiobutton):
                        rb.config(state=NORMAL)

        self.progress_bar["value"] = self.progress_bar["maximum"]
        self.worker_thread = None

        total = results_data.get('total', 0)
        processed = results_data.get('processed', 0)
        errors_list = results_data.get('errors', [])
        errors_count = len(errors_list)

        final_status_msg = f"Rotación finalizada. Imágenes procesadas: {processed}/{total}."
        if errors_count > 0:
            final_status_msg += f" Errores: {errors_count} (ver consola)."
        
        self.status_var.set(final_status_msg)

        if errors_count > 0:
            # Consider showing first few errors in messagebox or point to console
            error_details_preview = "\n".join(errors_list[:3])
            if len(errors_list) > 3:
                error_details_preview += "\n..."
            messagebox.showwarning("Proceso Completado con Errores", 
                                   f"{processed} de {total} imágenes procesadas.\n{errors_count} errores ocurrieron.\n\nPrimeros errores:\n{error_details_preview}\n\n(Revise la consola para todos los detalles)", 
                                   parent=self)
        else:
            if total > 0:
                messagebox.showinfo("Proceso Completado", f"Todas las {processed} imágenes fueron procesadas exitosamente.", parent=self)
            else:
                 messagebox.showinfo("Información", "No se encontraron imágenes o no se procesó ninguna.", parent=self)


    def _on_closing(self):
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Proceso en Curso", 
                                   "La rotación de imágenes está en curso. ¿Está seguro de que desea salir?",
                                   parent=self):
                self.destroy()
        else:
            self.destroy()


if __name__ == "__main__":
    app = ImageRotatorBatchApp()
    app.mainloop()