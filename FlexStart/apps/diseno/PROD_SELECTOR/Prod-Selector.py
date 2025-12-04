import os
import shutil
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText # Para un área de log mejorada
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

class FolderProcessorApp:
    def __init__(self, master):
        self.master = master
        master.title("SELECTOR DE PRODUCCIÓN A PARTIR DE REQUERIMIENTOS")
        master.geometry("750x550") # Ajustada la altura para el ScrolledText

        # Variables para los campos de entrada
        self.planilla_path_var = tk.StringVar()
        self.base_folder_path_var = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        # Frame principal con padding
        main_container = ttk.Frame(self.master, padding="15 15 15 15")
        main_container.pack(fill=BOTH, expand=True)

        # --- Sección de Entradas ---
        input_frame = ttk.Frame(main_container)
        input_frame.pack(fill=X, pady=(0, 10))
        input_frame.columnconfigure(1, weight=1) # Para que los Entry se expandan

        # Selección de la planilla
        label_planilla = ttk.Label(input_frame, text="Planilla (Excel/CSV):")
        label_planilla.grid(row=0, column=0, sticky=W, padx=(0,5), pady=5)
        entry_planilla = ttk.Entry(input_frame, textvariable=self.planilla_path_var, width=60)
        entry_planilla.grid(row=0, column=1, sticky=EW, padx=5, pady=5)
        button_planilla = ttk.Button(input_frame, text="Seleccionar Planilla",
                                     command=self.seleccionar_planilla, bootstyle="outline-secondary")
        button_planilla.grid(row=0, column=2, padx=(5,0), pady=5)

        # Selección de la carpeta base
        label_carpeta = ttk.Label(input_frame, text="Carpeta Base:")
        label_carpeta.grid(row=1, column=0, sticky=W, padx=(0,5), pady=5)
        entry_carpeta = ttk.Entry(input_frame, textvariable=self.base_folder_path_var, width=60)
        entry_carpeta.grid(row=1, column=1, sticky=EW, padx=5, pady=5)
        button_carpeta = ttk.Button(input_frame, text="Seleccionar Carpeta",
                                    command=self.seleccionar_carpeta, bootstyle="outline-secondary")
        button_carpeta.grid(row=1, column=2, padx=(5,0), pady=5)

        # --- Botón para iniciar el proceso ---
        button_procesar = ttk.Button(main_container, text="Procesar Carpetas",
                                     command=self.procesar, bootstyle="success")
        button_procesar.pack(pady=15, ipadx=10, ipady=5) # Botón más prominente

        # --- Área para mostrar mensajes de log (ScrolledText) ---
        log_frame = ttk.LabelFrame(main_container, text="Registro de Procesamiento", padding=(10,5), bootstyle="info")
        log_frame.pack(fill=BOTH, expand=True, padx=0, pady=(5,0))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_widget = ScrolledText(log_frame, wrap=WORD, state=DISABLED, height=10, autohide=True)
        self.log_widget.grid(row=0, column=0, sticky=NSEW)
        # Al inicializar ScrolledText con state=DISABLED, se aplica al Text interno.

    def _add_to_log(self, message):
        """Añade un mensaje al widget de log (ScrolledText)."""
        self.log_widget.text.config(state=NORMAL) # MODIFICADO
        self.log_widget.insert(END, message + "\n")
        self.log_widget.see(END) # Auto-scroll hasta el final
        self.log_widget.text.config(state=DISABLED) # MODIFICADO
        self.master.update_idletasks() # Refrescar UI para mostrar el mensaje

    def seleccionar_planilla(self):
        """Permite seleccionar la planilla (Excel o CSV) y actualiza el campo correspondiente."""
        file_path = filedialog.askopenfilename(
            title="Seleccione la planilla",
            filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Archivos CSV", "*.csv")]
        )
        if file_path:
            self.planilla_path_var.set(file_path)

    def seleccionar_carpeta(self):
        """Permite seleccionar la carpeta base para buscar las subcarpetas."""
        folder_path = filedialog.askdirectory(title="Seleccione la carpeta base")
        if folder_path:
            self.base_folder_path_var.set(folder_path)

    def procesar(self):
        """Lee la planilla, busca coincidencias en nombres de carpetas y mueve las que coincidan a PRODUCCION."""
        planilla_path = self.planilla_path_var.get()
        base_folder = self.base_folder_path_var.get()

        if not planilla_path or not base_folder:
            messagebox.showerror("Error de Entrada", "Por favor, seleccione la planilla y la carpeta base.")
            return
        
        if not os.path.isfile(planilla_path):
            messagebox.showerror("Error de Archivo", f"La ruta de la planilla no es un archivo válido:\n{planilla_path}")
            return
        if not os.path.isdir(base_folder):
            messagebox.showerror("Error de Carpeta", f"La ruta de la carpeta base no es un directorio válido:\n{base_folder}")
            return

        # Limpiar log anterior
        self.log_widget.text.config(state=NORMAL) # MODIFICADO (esta era la línea 104 original)
        self.log_widget.delete('1.0', END)
        self.log_widget.text.config(state=DISABLED) # MODIFICADO
        
        self._add_to_log("Iniciando procesamiento...")

        # Cargar la planilla con pandas
        try:
            if planilla_path.lower().endswith(".csv"):
                df = pd.read_csv(planilla_path, dtype=str) # Leer todo como string para EAN_HIJO
            else:
                df = pd.read_excel(planilla_path, dtype=str) # Leer todo como string
        except Exception as e:
            self._add_to_log(f"ERROR al leer la planilla: {e}")
            messagebox.showerror("Error de Lectura", f"Error al leer la planilla: {e}")
            return

        # Verificar que exista la columna 'EAN_HIJO'
        if "EAN_HIJO" not in df.columns:
            self._add_to_log("ERROR: La columna 'EAN_HIJO' no se encuentra en la planilla.")
            messagebox.showerror("Error de Columna", "La columna 'EAN_HIJO' no se encuentra en la planilla.")
            return

        # Obtener los nombres únicos permitidos (se convierte a cadena y se quitan espacios extra)
        # Filtrar valores nulos o vacíos antes de crear el set
        allowed_folders = set(df["EAN_HIJO"].dropna().astype(str).str.strip().tolist())
        allowed_folders = {name for name in allowed_folders if name} # Eliminar strings vacíos
        
        if not allowed_folders:
            self._add_to_log("ADVERTENCIA: No se encontraron nombres de carpetas válidos ('EAN_HIJO') en la planilla.")
            messagebox.showwarning("Sin Datos", "No se encontraron nombres de carpetas válidos ('EAN_HIJO') en la planilla para procesar.")
            return

        # Crear la carpeta PRODUCCION dentro de la carpeta base
        produccion_path = os.path.join(base_folder, "PRODUCCION")
        try:
            if not os.path.exists(produccion_path):
                os.makedirs(produccion_path)
                self._add_to_log(f"Carpeta creada: {produccion_path}")
        except Exception as e:
            self._add_to_log(f"ERROR al crear la carpeta PRODUCCION: {e}")
            messagebox.showerror("Error de Creación", f"No se pudo crear la carpeta PRODUCCION en '{base_folder}':\n{e}")
            return
        
        moved_count = 0
        skipped_count = 0
        processed_folders = 0

        # Recorrer la carpeta base (topdown=False para procesar subcarpetas más profundas primero)
        for current_root, dirs, files in os.walk(base_folder, topdown=False):
            # Convertir a rutas absolutas para comparación fiable
            abs_current_root = os.path.abspath(current_root)
            abs_produccion_path = os.path.abspath(produccion_path)

            # Evitar procesar la carpeta PRODUCCION o sus contenidos
            if abs_current_root.startswith(abs_produccion_path):
                dirs[:] = [] 
                continue

            for d in list(dirs): 
                folder_name = d 
                folder_full_path = os.path.join(current_root, folder_name)
                abs_folder_full_path = os.path.abspath(folder_full_path)

                if abs_folder_full_path == abs_produccion_path:
                    if d in dirs: dirs.remove(d) 
                    continue
                
                processed_folders += 1

                if folder_name in allowed_folders:
                    try:
                        target_path = os.path.join(produccion_path, folder_name)
                        if os.path.exists(target_path):
                            self._add_to_log(f"OMITIDO: La carpeta '{folder_name}' ya existe en PRODUCCION.")
                            skipped_count +=1
                        else:
                            self._add_to_log(f"Moviendo: '{folder_full_path}' -> '{target_path}'")
                            shutil.move(folder_full_path, target_path)
                            self._add_to_log(f"MOVIDA: '{folder_name}' a PRODUCCION.")
                            moved_count += 1
                            if d in dirs: dirs.remove(d) 
                    except Exception as e:
                        self._add_to_log(f"ERROR moviendo '{folder_full_path}': {e}")

        final_message = (f"Procesamiento finalizado.\n"
                         f"Carpetas movidas exitosamente: {moved_count}\n"
                         f"Carpetas omitidas (ya en PRODUCCION): {skipped_count}\n"
                         f"Total de carpetas encontradas en planilla: {len(allowed_folders)}")
        self._add_to_log(final_message)
        messagebox.showinfo("Proceso Completado", final_message)

if __name__ == "__main__":
    root = ttk.Window()
    setup_theme(root)
    app = FolderProcessorApp(root)
    root.mainloop()