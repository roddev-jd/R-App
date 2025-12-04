#!/usr/bin/env python3

import os
import re
import logging
import threading
import tkinter as tk # Still needed for StringVar
import ttkbootstrap as ttk # ttkbootstrap components
from ttkbootstrap.constants import * # ttkbootstrap constants
from ttkbootstrap.scrolled import ScrolledText # ttkbootstrap ScrolledText
from tkinter import filedialog, messagebox # Standard dialogs
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

# --- Lógica de renombrado (revertida a la funcionalidad original) ---
class SuffixHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            # Ensure path exists, event might fire early
            if os.path.exists(event.src_path):
                self._process(event.src_path)
            else:
                logging.debug(f"SuffixHandler.on_created: src_path {event.src_path} no existe, omitiendo.")


    def on_moved(self, event):
        if not event.is_directory:
            # Ensure path exists, event might fire early
            if os.path.exists(event.dest_path):
                self._process(event.dest_path)
            else:
                logging.debug(f"SuffixHandler.on_moved: dest_path {event.dest_path} no existe, omitiendo.")

    def _process(self, path_str): # path_str is a string from watchdog
        # Original logic starts here
        ext = os.path.splitext(path_str)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
            return

        folder = os.path.dirname(path_str)
        filename = os.path.basename(path_str)
        name, _ = os.path.splitext(filename) # 'name' is stem of the processed file
        
        # 'base' is the name of the parent folder, used to construct new filenames
        base = os.path.basename(folder) 

        # Check 1: Ignore temporary files or files already matching the target pattern
        # The pattern means: base_2.ext or base-NUMBER.ext
        if name.startswith('~$') or re.match(rf"^{re.escape(base)}(_2|-\d+)$", name):
            logging.debug(f"Archivo '{filename}' ignorado (temporal o ya renombrado según patrón).")
            return

        # Original logic proceeds to rename ANY other image file using the 'base' (folder name)
        # to construct the new name. There's no check if 'name == base'.

        has_p2 = False
        negatives = []
        # Iterate over all items in the directory to check for existing suffixes
        for f_in_dir in os.listdir(folder):
            # Get stem of each item in directory, no extension filtering for this check
            b_stem_in_dir, _ = os.path.splitext(f_in_dir) 
            
            if b_stem_in_dir == f"{base}_2": # Checks if 'base_2' (any ext) exists
                has_p2 = True
            
            # Checks if 'base-NUMBER' (any ext) exists
            m = re.match(rf"^{re.escape(base)}-(\d+)$", b_stem_in_dir) 
            if m:
                negatives.append(int(m.group(1)))
        
        # Determine the new suffix based on existing files
        if not has_p2 and not negatives: # If neither base_2 nor base-N exist
            suffix = '_2'
        elif not negatives: # If base_2 exists (or doesn't) but no base-N exist
            suffix = '-1'
        else: # If base-N files exist
            suffix = f"-{max(negatives) + 1}"
        
        new_name_stem = f"{base}{suffix}"
        new_name_with_ext = f"{new_name_stem}{ext}" # Use original file's extension
        new_full_path = os.path.join(folder, new_name_with_ext)
        
        try:
            # Original code directly calls os.rename.
            # It doesn't pre-check for new_full_path existence.
            # os.rename behavior (overwrite or error on existing file) is platform-dependent.
            # Windows: raises FileExistsError if new_full_path exists.
            # Unix-like: often overwrites if new_full_path is a file.
            # Sticking to original's direct os.rename call.
            if path_str == new_full_path:
                 logging.debug(f"Intento de renombrar '{filename}' a sí mismo. Omitiendo.")
                 return

            os.rename(path_str, new_full_path)
            # Original logging format:
            logging.info(f"Renombrado: {filename} → {new_name_with_ext}")
        except Exception as e:
            # Original logging format:
            logging.error(f"Error renombrando {path_str}: {e}")


# --- Logging hacia widget de texto (ttkbootstrap compatible) ---
class TextHandler(logging.Handler):
    def __init__(self, text_widget_internal): # Expects the actual tk.Text component
        super().__init__()
        self.text_widget = text_widget_internal

    def emit(self, record):
        msg = self.format(record)
        def append():
            if not self.text_widget.winfo_exists(): # Check if widget still exists
                return
            current_state = self.text_widget.cget("state")
            self.text_widget.config(state=NORMAL) # Use ttkbootstrap.constants.NORMAL
            self.text_widget.insert(END, msg + '\n') # Use ttkbootstrap.constants.END
            self.text_widget.config(state=current_state) # Restore original state
            self.text_widget.see(END)
        self.text_widget.after(0, append) # Schedule GUI update

# --- Interfaz gráfica (ttkbootstrap) ---
class MonitorApp(ttk.Window):
    def __init__(self):
        super().__init__()
        setup_theme(self)
        self.title('Monitor Sufijos de Imágenes (ttkbootstrap)')
        self.geometry('750x500')
        
        self.observer = None
        self.watchdog_handler = SuffixHandler()
        self.current_monitored_dir = os.getcwd() # Store only the path
        self.dir_display_var = tk.StringVar(value=f'Directorio: {self.current_monitored_dir}')

        self._build_ui()
        self._setup_logging()
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle graceful shutdown

    def _build_ui(self):
        frm_top = ttk.Frame(self, padding=(10, 10))
        frm_top.pack(fill=X)

        self.lbl_dir_display = ttk.Label(frm_top, textvariable=self.dir_display_var, anchor=W)
        self.lbl_dir_display.pack(side=LEFT, fill=X, expand=True, padx=(0,10))
        
        btn_sel_dir = ttk.Button(frm_top, text='Seleccionar Carpeta', command=self._choose_dir, bootstyle="outline-secondary")
        btn_sel_dir.pack(side=LEFT)

        frm_buttons = ttk.Frame(self, padding=(10, 5))
        frm_buttons.pack(fill=X)

        self.btn_start = ttk.Button(frm_buttons, text='Iniciar Monitoreo', command=self._start_monitoring, bootstyle="success")
        self.btn_start.pack(side=LEFT, padx=(0,5))
        
        self.btn_stop = ttk.Button(frm_buttons, text='Detener Monitoreo', state=DISABLED, command=self._stop_monitoring, bootstyle="danger")
        self.btn_stop.pack(side=LEFT)

        self.log_scrolled_text = ScrolledText(self, height=20, autohide=True)
        self.log_scrolled_text.text.config(state=DISABLED) # Disable the internal text widget initially
        self.log_scrolled_text.pack(fill=BOTH, expand=True, padx=10, pady=(5,10))

    def _setup_logging(self):
        logger = logging.getLogger() # Get root logger
        # Clear any existing handlers from root logger to avoid duplicate messages if script is re-run
        if logger.hasHandlers():
            logger.handlers.clear()
            
        logger.setLevel(logging.INFO)
        
        # GUI logger
        gui_text_handler = TextHandler(self.log_scrolled_text.text) # Pass internal tk.Text
        gui_text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_text_handler)

        # Console logger (optional, for debugging)
        # console_handler = logging.StreamHandler()
        # console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        # logger.addHandler(console_handler)

    def _choose_dir(self):
        if self.observer and self.observer.is_alive():
            messagebox.showwarning("Monitoreo Activo", "Debe detener el monitoreo actual antes de seleccionar un nuevo directorio.")
            return

        new_dir = filedialog.askdirectory(initialdir=self.current_monitored_dir, title="Seleccionar Directorio a Monitorear")
        if new_dir: # If a directory was selected
            self.current_monitored_dir = new_dir
            self.dir_display_var.set(f'Directorio: {self.current_monitored_dir}')
            logging.info(f"Directorio para monitorear cambiado a: {self.current_monitored_dir}")

    def _start_monitoring(self):
        if self.observer and self.observer.is_alive():
            logging.warning("El monitoreo ya está activo.")
            return
        
        if not os.path.isdir(self.current_monitored_dir):
            logging.error(f"El directorio seleccionado no es válido: {self.current_monitored_dir}")
            messagebox.showerror("Error de Directorio", f"El directorio '{self.current_monitored_dir}' no existe o no es accesible.")
            return

        self.observer = Observer()
        self.observer.schedule(self.watchdog_handler, path=self.current_monitored_dir, recursive=True)
        
        try:
            self.observer.start()
            logging.info(f'Monitoreo iniciado en: {self.current_monitored_dir}')
            self.btn_start.config(state=DISABLED)
            self.btn_stop.config(state=NORMAL)
        except Exception as e:
            logging.error(f"No se pudo iniciar el monitoreo: {e}")
            messagebox.showerror("Error al Iniciar", f"No se pudo iniciar el monitoreo en '{self.current_monitored_dir}'.\nError: {e}")
            self.observer = None

    def _stop_monitoring(self):
        if not self.observer or not self.observer.is_alive():
            logging.info("El monitoreo no está activo o ya fue detenido.")
            self.btn_start.config(state=NORMAL)
            self.btn_stop.config(state=DISABLED)
            self.observer = None
            return
        
        try:
            self.observer.stop()
            self.observer.join()
            logging.info('Monitoreo detenido exitosamente.')
        except Exception as e:
            logging.error(f"Error al detener el monitoreo: {e}")
        finally:
            self.observer = None
            self.btn_start.config(state=NORMAL)
            self.btn_stop.config(state=DISABLED)
            
    def on_closing(self):
        if self.observer and self.observer.is_alive():
            if messagebox.askyesno("Monitoreo Activo", "El monitoreo está activo. ¿Desea detenerlo y salir?", parent=self):
                self._stop_monitoring()
                self.destroy()
            # else: user chose not to close, do nothing
        else:
            self.destroy()

if __name__ == '__main__':
    app = MonitorApp()
    app.mainloop()