import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd

import ttkbootstrap as ttk
from ttkbootstrap.constants import (LEFT, RIGHT, X, Y, BOTH, VERTICAL, HORIZONTAL,
                                    DISABLED, NORMAL, END)
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

class FiltradorApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Identificador de diseñadores / redactores (TTKBootstrap)")
        self.master.geometry("550x250") # Adjusted geometry for the new widget

        # Determine base directory (docs folder next to the script)
        if getattr(sys, 'frozen', False): # If running as a PyInstaller bundle
            self.base_script_dir = Path(sys.executable).parent
        else: # If running as a normal script
            self.base_script_dir = Path(__file__).parent
        
        self.docs_dir = self.base_script_dir / "docs"
        
        self.base_files = {
            "CHILE": self.docs_dir / "CHILE.xlsx",
            "PERU":  self.docs_dir / "PERU.xlsx",
            #"ESTUDIO PERU":  self.docs_dir / "ESTUDIO_PERU.xlsx"
        }
        # Definimos aquí los nombres de columna:
        self.dest_col   = "DEPTOS"

        # Tkinter control variables
        self.filepath_var = tk.StringVar()
        self.source_col_var = tk.StringVar(value="coddepto") # Default value

        self._init_ui()

    def _init_ui(self):
        main_frame = ttk.Frame(self.master, padding=15)
        main_frame.pack(fill=BOTH, expand=True)

        # 1) Seleccionar base
        frame_base_selection = ttk.Frame(main_frame)
        frame_base_selection.pack(fill=X, pady=(0, 10))
        
        ttk.Label(frame_base_selection, text="Elige el país:").pack(side=LEFT, padx=(0, 10))
        
        self.combo_base = ttk.Combobox(frame_base_selection, state="readonly", width=35)
        self.combo_base['values'] = list(self.base_files.keys())
        if self.combo_base['values']: # Set default selection
            self.combo_base.current(0)
        self.combo_base.pack(side=LEFT, expand=True, fill=X)

        # 2) Columna a analizar
        frame_col_selection = ttk.Frame(main_frame)
        frame_col_selection.pack(fill=X, pady=10)

        ttk.Label(frame_col_selection, text="Columna depto. en tu planilla:").pack(side=LEFT, padx=(0, 10))
        self.entry_source_col = ttk.Entry(frame_col_selection, textvariable=self.source_col_var)
        self.entry_source_col.pack(side=LEFT, expand=True, fill=X)

        # 3) Seleccionar planilla a analizar
        frame_file_selection = ttk.Frame(main_frame)
        frame_file_selection.pack(fill=X, pady=10)
        
        ttk.Label(frame_file_selection, text="Adjunta la curva a analizar:").pack(side=LEFT, padx=(0, 10))
        
        self.line_file_entry = ttk.Entry(frame_file_selection, textvariable=self.filepath_var, state="readonly")
        self.line_file_entry.pack(side=LEFT, expand=True, fill=X, padx=(0,10))
        
        btn_browse = ttk.Button(frame_file_selection, text="Examinar…", 
                                command=self._browse_file, bootstyle="outline-secondary")
        btn_browse.pack(side=LEFT)

        # 3) Generar filtrado
        btn_generate = ttk.Button(main_frame, text="Generar reporte", 
                                  command=self._generate, bootstyle="success")
        btn_generate.pack(pady=(15,0), fill=X, ipady=5) # Make button a bit taller

    def _browse_file(self):
        # Use base_script_dir as initial directory for file dialog
        initial_dir = str(self.base_script_dir)
        fname = filedialog.askopenfilename(
            master=self.master, # Explicitly set master for dialog parent
            title="Selecciona la planilla a analizar",
            initialdir=initial_dir,
            filetypes=[("Excel", "*.xlsx *.xls"), ("CSV", "*.csv"), ("Todos los archivos", "*.*")]
        )
        if fname:
            self.filepath_var.set(fname)

    def _read_df(self, path: Path):
        ext = path.suffix.lower()
        try:
            if ext in (".xlsx", ".xls"):
                return pd.read_excel(path)
            elif ext == ".csv":
                return pd.read_csv(path)
            else:
                # This case should ideally not be reached if file dialog filters are used,
                # but good for robustness if path is set otherwise.
                raise ValueError(f"Formato no soportado: {ext}")
        except Exception as e:
            raise ValueError(f"Error al leer el archivo {path.name}: {e}")


    def _generate(self):
        base_name     = self.combo_base.get()
        designer_path_str = self.filepath_var.get()
        source_col_name = self.source_col_var.get().strip() # Get column name from Entry
        
        if not designer_path_str:
            messagebox.showwarning("Atención", "Por favor, selecciona un archivo para analizar.", parent=self.master)
            return

        if not source_col_name:
            messagebox.showwarning("Atención", "Por favor, ingresa el nombre de la columna de departamento.", parent=self.master)
            return
            
        designer_path = Path(designer_path_str)
        base_path     = self.base_files.get(base_name) # Use .get for safety

        # Validaciones
        if not designer_path.exists():
            messagebox.showwarning("Atención", f"El archivo seleccionado '{designer_path.name}' no existe o no es válido.", parent=self.master)
            return
        
        if not base_path: # Should not happen if combo_base is populated correctly
             messagebox.showerror("Error Crítico", f"No se encontró la configuración para la base '{base_name}'.", parent=self.master)
             return

        if not base_path.exists():
            # Create docs directory if it doesn't exist, as a hint to the user
            try:
                self.docs_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass # Ignore if cannot create
            messagebox.showerror(
                "Error de Archivo Base",
                f"No se encontró el archivo base '{base_path.name}' para '{base_name}'.\n"
                f"Debería estar en la carpeta:\n{self.docs_dir}\n"
                "Por favor, asegúrate de que el archivo exista en esa ubicación.",
                parent=self.master
            )
            return

        try:
            df_source = self._read_df(designer_path)
            df_base   = self._read_df(base_path)

            # Comprobamos existencia de columnas
            if source_col_name not in df_source.columns:
                messagebox.showerror(
                    "Error de Columna",
                    f"La columna requerida '{source_col_name}' no existe en tu planilla '{designer_path.name}'.",
                    parent=self.master
                )
                return
            if self.dest_col not in df_base.columns:
                messagebox.showerror(
                    "Error de Columna",
                    f"La columna requerida '{self.dest_col}' no existe en el archivo base '{base_path.name}'.",
                    parent=self.master
                )
                return

            # Filtrado: valores de source_col (coddepto) contra dest_col (DEPTOS)
            # Convert both columns to string before comparison to handle mixed types or numeric codes gracefully
            valores_source = df_source[source_col_name].astype(str).dropna().unique()
            df_base[self.dest_col] = df_base[self.dest_col].astype(str)
            
            out_df = df_base[df_base[self.dest_col].isin(valores_source)]

            if out_df.empty:
                messagebox.showinfo("Resultado", "No se encontraron coincidencias para generar el reporte.", parent=self.master)
                return

            # Guardar resultado
            # Use base_script_dir as initial directory for save dialog
            initial_save_dir = str(self.base_script_dir)
            default_save_name = f"filtrado_{base_name}_{designer_path.stem}.xlsx" # More descriptive default name

            save_fname = filedialog.asksaveasfilename(
                master=self.master,
                title="Guardar resultado del filtrado",
                initialdir=initial_save_dir,
                initialfile=default_save_name,
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx"), ("Todos los archivos", "*.*")]
            )
            
            if save_fname:
                out_df.to_excel(save_fname, index=False)
                messagebox.showinfo(
                    "Listo",
                    f"Filtrado guardado exitosamente en:\n{save_fname}",
                    parent=self.master
                )
        except ValueError as ve: # Catch specific errors from _read_df or data issues
            messagebox.showerror("Error de Datos", str(ve), parent=self.master)
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Ocurrió un problema durante la generación:\n{e}", parent=self.master)

if __name__ == "__main__":
    # Determine if running as a script or frozen executable for base_files path
    # This initial path setup is now handled inside the class constructor for clarity
    
    root = ttk.Window()
    setup_theme(root)
    app = FiltradorApp(root)
    root.mainloop()