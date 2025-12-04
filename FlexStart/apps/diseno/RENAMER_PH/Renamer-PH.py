import sys
import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
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

class RenameFoldersApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Renombrador de Carpetas desde Excel")
        self._build_ui()

    def _build_ui(self):
        main_content_frame = ttk.Frame(self.master, padding="20 20 20 20")
        main_content_frame.pack(fill=BOTH, expand=True)
        main_content_frame.columnconfigure(0, weight=1)
        main_content_frame.rowconfigure(6, weight=1)

        # --- Sección Excel ---
        box_excel = ttk.LabelFrame(main_content_frame, text="Archivo Excel", padding=(10, 5))
        box_excel.grid(row=0, column=0, sticky=EW, pady=(0, 10))
        box_excel.columnconfigure(1, weight=1)
        ttk.Label(box_excel, text="Planilla:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.excel_path_var = tk.StringVar()
        self.txt_excel = ttk.Entry(box_excel, textvariable=self.excel_path_var)
        self.txt_excel.grid(row=0, column=1, sticky=EW, padx=5, pady=5)
        btn_browse_excel = ttk.Button(box_excel, text="Examinar...", command=self.browse_excel, bootstyle="outline-secondary")
        btn_browse_excel.grid(row=0, column=2, sticky=E, padx=5, pady=5)

        # --- Sección Carpeta base ---
        box_folder = ttk.LabelFrame(main_content_frame, text="Carpeta a Analizar", padding=(10, 5))
        box_folder.grid(row=1, column=0, sticky=EW, pady=(0, 10))
        box_folder.columnconfigure(1, weight=1)
        ttk.Label(box_folder, text="Ubicación:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.folder_path_var = tk.StringVar()
        self.txt_folder = ttk.Entry(box_folder, textvariable=self.folder_path_var)
        self.txt_folder.grid(row=0, column=1, sticky=EW, padx=5, pady=5)
        btn_browse_folder = ttk.Button(box_folder, text="Examinar...", command=self.browse_folder, bootstyle="outline-secondary")
        btn_browse_folder.grid(row=0, column=2, sticky=E, padx=5, pady=5)

        # --- Sección Columnas ---
        box_cols = ttk.LabelFrame(main_content_frame, text="Columnas a Usar", padding=(10, 5))
        box_cols.grid(row=2, column=0, sticky=EW, pady=(0, 10))
        box_cols.columnconfigure(1, weight=1)
        ttk.Label(box_cols, text="Col. Carpeta (antigua):").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.old_col_var = tk.StringVar(value="codskupadrelargo")
        self.txt_old = ttk.Entry(box_cols, textvariable=self.old_col_var)
        self.txt_old.grid(row=0, column=1, sticky=EW, padx=(0,5), pady=5)
        ttk.Label(box_cols, text="Col. Nuevo Nombre:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.new_col_var = tk.StringVar(value="upc_ripley")
        self.txt_new = ttk.Entry(box_cols, textvariable=self.new_col_var)
        self.txt_new.grid(row=1, column=1, sticky=EW, padx=(0,5), pady=5)
        
        # --- Botones de acción ---
        action_button_frame = ttk.Frame(main_content_frame)
        action_button_frame.grid(row=3, column=0, sticky=EW, pady=(5, 10))
        action_button_frame.columnconfigure(0, weight=1)
        btn_run = ttk.Button(action_button_frame, text="Renombrar Carpetas", command=self.run_rename, bootstyle="success")
        btn_run.pack(side=RIGHT, padx=5)

        # --- Barra de progreso y etiqueta de estado ---
        self.progress_value = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(main_content_frame, variable=self.progress_value, maximum=100, mode='determinate', bootstyle="info")
        self.progress_bar.grid(row=4, column=0, sticky=EW, pady=(0,5))
        self.status_text_var = tk.StringVar(value="Esperando...")
        self.status_label = ttk.Label(main_content_frame, textvariable=self.status_text_var)
        self.status_label.grid(row=5, column=0, sticky=W, pady=(0,10))

        # --- Log ---
        box_log = ttk.LabelFrame(main_content_frame, text="Log de Operaciones", padding=(10, 5), bootstyle="info")
        box_log.grid(row=6, column=0, sticky=NSEW)
        box_log.rowconfigure(0, weight=1)
        box_log.columnconfigure(0, weight=1)
        self.log_text = ScrolledText(box_log, state=DISABLED, wrap='word', height=10, autohide=True)
        self.log_text.grid(row=0, column=0, sticky=NSEW, padx=5, pady=5)

    def browse_excel(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Excel", filetypes=[("Archivos Excel", "*.xlsx *.xls")]
        )
        if path:
            self.excel_path_var.set(path)
            if not self.folder_path_var.get():
                self.folder_path_var.set(os.path.dirname(path))

    def browse_folder(self):
        path = filedialog.askdirectory(title="Seleccionar Carpeta")
        if path:
            self.folder_path_var.set(path)

    def _log_message(self, message):
        # ✅ CORRECCIÓN: Se accede al widget .text para cambiar el estado
        self.log_text.text.config(state=NORMAL)
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)
        # ✅ CORRECCIÓN: Se accede al widget .text para cambiar el estado
        self.log_text.text.config(state=DISABLED)
        self.master.update_idletasks()

    def run_rename(self):
        excel_file = self.excel_path_var.get().strip()
        base_folder = self.folder_path_var.get().strip()
        old_col_name = self.old_col_var.get().strip()
        new_col_name = self.new_col_var.get().strip()

        if not excel_file or not os.path.isfile(excel_file):
            messagebox.showerror("Error", "Seleccione un archivo Excel válido.")
            return
        if not base_folder or not os.path.isdir(base_folder):
            messagebox.showerror("Error", "Seleccione una carpeta válida para analizar.")
            return
        
        try:
            df = pd.read_excel(excel_file, dtype=str) 
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el archivo Excel:\n{e}")
            return

        if old_col_name not in df.columns or new_col_name not in df.columns:
            messagebox.showerror(
                "Error",
                f"El archivo Excel debe contener las columnas especificadas:\n'{old_col_name}' y '{new_col_name}'.\nColumnas encontradas: {', '.join(df.columns)}"
            )
            return

        # ✅ CORRECCIÓN: Se accede al widget .text para cambiar el estado
        self.log_text.text.config(state=NORMAL)
        self.log_text.delete('1.0', END)
        # ✅ CORRECCIÓN: Se accede al widget .text para cambiar el estado
        self.log_text.text.config(state=DISABLED)

        mapping_list = []
        for index, row in df.iterrows():
            old_name_val = row.get(old_col_name, '')
            new_name_val = row.get(new_col_name, '')
            if pd.isna(old_name_val) or str(old_name_val).lower() == 'nan' or not str(old_name_val).strip():
                continue
            if pd.isna(new_name_val) or str(new_name_val).lower() == 'nan' or not str(new_name_val).strip():
                self._log_message(f"ADVERTENCIA: Nombre nuevo inválido/vacío para carpeta antigua '{old_name_val}' en fila {index+2}. Se omite.")
                continue
            
            mapping_list.append((str(old_name_val).strip(), str(new_name_val).strip()))

        if not mapping_list:
            messagebox.showinfo("Información", "No se encontraron mapeos válidos de nombres en el Excel (verifique valores vacíos o 'NaN').")
            self.status_text_var.set("No hay datos para procesar.")
            return

        total_to_process = len(mapping_list)
        self.progress_bar.config(maximum=total_to_process)
        self.progress_value.set(0)
        self.status_text_var.set(f"Procesando 0/{total_to_process}...")
        self.master.update_idletasks()

        renamed_count = 0
        processed_count = 0
        for old_folder_name, new_folder_name in mapping_list:
            source_path = os.path.join(base_folder, old_folder_name)
            destination_path = os.path.join(base_folder, new_folder_name)
            
            processed_count += 1
            self.status_text_var.set(f"Procesando {processed_count}/{total_to_process}: {old_folder_name}...")

            if os.path.isdir(source_path):
                if source_path == destination_path:
                    self._log_message(f"INFO: Nombre antiguo y nuevo son idénticos para '{old_folder_name}'. No se requiere renombrar.")
                elif os.path.exists(destination_path):
                    self._log_message(f"ADVERTENCIA: Ya existe un archivo/carpeta con el nuevo nombre '{new_folder_name}'. No se renombró '{old_folder_name}'.")
                else:
                    try:
                        os.rename(source_path, destination_path)
                        renamed_count += 1
                        self._log_message(f"ÉXITO: '{old_folder_name}' renombrado a '{new_folder_name}'")
                    except Exception as e:
                        self._log_message(f"ERROR al renombrar '{old_folder_name}' a '{new_folder_name}': {e}")
            else:
                self._log_message(f"INFO: No se encontró la carpeta de origen '{old_folder_name}' en '{base_folder}'.")
            
            self.progress_value.set(processed_count)
            self.master.update_idletasks()

        self.status_text_var.set(f"Completado. Carpetas renombradas: {renamed_count} de {processed_count} evaluadas.")
        messagebox.showinfo(
            "Proceso Completado",
            f"Se intentaron renombrar {processed_count} carpetas.\n"
            f"Carpetas renombradas exitosamente: {renamed_count}."
        )

if __name__ == "__main__":
    root = ttk.Window()
    setup_theme(root)
    app = RenameFoldersApp(root)
    root.geometry("700x650")
    root.mainloop()