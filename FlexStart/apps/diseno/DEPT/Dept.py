import os
import shutil
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import (
    NORMAL, DISABLED, END, NSEW, EW, W, LEFT, E
)
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

class DepartamentalizarApp:
    def __init__(self, master):
        self.master = master
        master.title('Departamentalizador de carpetas') # Incremented version
        # master.geometry("750x700")
        setup_theme(master)

        self.excel_file_var = tk.StringVar()
        self.input_dir_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()
        self.child_col_var = tk.StringVar(value='upc_ripley')
        self.depto_col_var = tk.StringVar(value='coddepto')
        self.include_count_var = tk.BooleanVar(value=True)
        self.progress_var = tk.DoubleVar()

        self._create_widgets()

    def _add_to_log(self, message):
        # CORREGIDO: Usar self.log_text.text.config() para el estado
        self.log_text.text.config(state=NORMAL)
        self.log_text.insert(END, message + '\n') # .insert() debería estar bien delegado
        self.log_text.text.config(state=DISABLED)
        self.log_text.see(END) # .see() debería estar bien delegado
        self.master.update_idletasks()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="15 15 15 15")
        main_frame.grid(row=0, column=0, sticky=NSEW)
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)

        main_frame.rowconfigure(5, weight=1)
        main_frame.columnconfigure(0, weight=1)

        entry_frame = ttk.Frame(main_frame)
        entry_frame.grid(row=0, column=0, sticky=EW, pady=(0,15))
        entry_frame.columnconfigure(1, weight=1)

        ttk.Label(entry_frame, text='Archivo Excel:').grid(row=0, column=0, sticky=W, padx=(0,5), pady=5)
        ttk.Entry(entry_frame, textvariable=self.excel_file_var, state="readonly").grid(row=0, column=1, sticky=EW, pady=5)
        ttk.Button(entry_frame, text='Examinar', command=self.select_excel_file, bootstyle="outline-secondary").grid(row=0, column=2, sticky=E, padx=(5,0), pady=5)

        ttk.Label(entry_frame, text='Carpeta Entrada (Hijos):').grid(row=1, column=0, sticky=W, padx=(0,5), pady=5)
        ttk.Entry(entry_frame, textvariable=self.input_dir_var, state="readonly").grid(row=1, column=1, sticky=EW, pady=5)
        ttk.Button(entry_frame, text='Examinar', command=self.select_input_dir, bootstyle="outline-secondary").grid(row=1, column=2, sticky=E, padx=(5,0), pady=5)

        ttk.Label(entry_frame, text='Carpeta Salida (Deptos.):').grid(row=2, column=0, sticky=W, padx=(0,5), pady=5)
        ttk.Entry(entry_frame, textvariable=self.output_dir_var, state="readonly").grid(row=2, column=1, sticky=EW, pady=5)
        ttk.Button(entry_frame, text='Examinar', command=self.select_output_dir, bootstyle="outline-secondary").grid(row=2, column=2, sticky=E, padx=(5,0), pady=5)

        cols_frame = ttk.LabelFrame(main_frame, text="Configuración de Columnas Excel", bootstyle="info")
        cols_frame.grid(row=1, column=0, sticky=EW, pady=(0,10), ipady=5, ipadx=5)
        cols_frame.columnconfigure(1, weight=1)
        cols_frame.columnconfigure(3, weight=1)

        ttk.Label(cols_frame, text='Col. Nombres Hijos:').grid(row=0, column=0, sticky=W, padx=(5,5), pady=5)
        ttk.Entry(cols_frame, textvariable=self.child_col_var).grid(row=0, column=1, sticky=EW, padx=(0,10), pady=5)

        ttk.Label(cols_frame, text='Col. Departamentos:').grid(row=0, column=2, sticky=W, padx=(5,5), pady=5)
        ttk.Entry(cols_frame, textvariable=self.depto_col_var).grid(row=0, column=3, sticky=EW, padx=(0,5), pady=5)

        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=2, column=0, sticky=E, pady=(10,15))

        ttk.Checkbutton(action_frame, text='Incluir SKU en nombre depto.', variable=self.include_count_var, bootstyle="info-square-toggle").pack(side=LEFT, padx=(0,10))
        self.btn_start = ttk.Button(action_frame, text='Iniciar Proceso', command=self.start_organization_process, bootstyle="success")
        self.btn_start.pack(side=LEFT)

        progress_status_frame = ttk.Frame(main_frame)
        progress_status_frame.grid(row=3, column=0, sticky=EW, pady=(0,5))
        progress_status_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(progress_status_frame, variable=self.progress_var, maximum=100, mode='determinate', bootstyle="info-striped")
        self.progress_bar.grid(row=0, column=0, sticky=EW, pady=(0,5))

        self.status_label = ttk.Label(progress_status_frame, text='Listo para iniciar.')
        self.status_label.grid(row=1, column=0, sticky=W, pady=(0,10))

        log_labelframe = ttk.LabelFrame(main_frame, text='Registro de Actividad', padding=(10,5), bootstyle="info")
        log_labelframe.grid(row=5, column=0, sticky=NSEW, pady=(5,0))
        log_labelframe.columnconfigure(0, weight=1)
        log_labelframe.rowconfigure(0, weight=1)

        # El estado inicial se establece correctamente en el constructor de ScrolledText
        self.log_text = ScrolledText(log_labelframe, wrap='word', height=10, autohide=True, state=DISABLED)
        self.log_text.grid(row=0, column=0, sticky=NSEW)

    def select_excel_file(self):
        path = filedialog.askopenfilename(parent=self.master, filetypes=[('Excel', '*.xlsx *.xls')])
        if path:
            self.excel_file_var.set(path)

    def select_input_dir(self):
        path = filedialog.askdirectory(parent=self.master, title="Seleccionar Carpeta de Entrada Principal")
        if path:
            self.input_dir_var.set(path)
            if not self.output_dir_var.get():
                self.output_dir_var.set(path)

    def select_output_dir(self):
        path = filedialog.askdirectory(parent=self.master, title="Seleccionar Carpeta de Salida para Departamentos")
        if path:
            self.output_dir_var.set(path)

    def _organize_folders_logic(self, excel_file, input_dir, output_dir, child_col, depto_col, include_count):
        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            messagebox.showerror("Error al leer Excel", f"No se pudo leer el archivo Excel:\n{e}", parent=self.master)
            self.status_label.config(text='Error al leer Excel.')
            return

        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                self._add_to_log(f"Carpeta de salida creada: {output_dir}")
        except Exception as e:
            messagebox.showerror("Error de Directorio", f"No se pudo crear la carpeta de salida '{output_dir}':\n{e}", parent=self.master)
            self.status_label.config(text='Error al crear directorio de salida.')
            return

        depto_paths = {}
        if depto_col not in df.columns:
            messagebox.showerror("Error de Columna", f"La columna de departamento '{depto_col}' no existe en el archivo Excel.", parent=self.master)
            self.status_label.config(text=f"Columna '{depto_col}' no encontrada.")
            return
        
        for depto_raw in df[depto_col].dropna().unique():
            key = str(depto_raw).strip()
            if not key: continue
            depto_path = os.path.join(output_dir, key)
            if not os.path.exists(depto_path):
                try:
                    os.makedirs(depto_path)
                    self._add_to_log(f'Carpeta de departamento creada: {depto_path}')
                except Exception as e:
                    self._add_to_log(f'ERROR al crear carpeta de departamento {depto_path}: {e}')
                    continue
            else:
                 self._add_to_log(f'Carpeta de departamento existente: {depto_path}')
            depto_paths[key] = depto_path

        if child_col not in df.columns:
            messagebox.showerror("Error de Columna", f"La columna de nombres hijos '{child_col}' no existe en el archivo Excel.", parent=self.master)
            self.status_label.config(text=f"Columna '{child_col}' no encontrada.")
            return

        total_rows = len(df)
        processed_count = 0
        for index, row in df.iterrows():
            hijo_val = row.get(child_col)
            depto_val = row.get(depto_col)

            progress = ((index + 1) / total_rows) * 100
            self.progress_var.set(progress)
            self.master.update_idletasks()

            if pd.isna(hijo_val) or pd.isna(depto_val):
                self._add_to_log(f'Fila {index + 1}: Saltada por valor NaN en hijo o departamento.')
                continue
            
            # Corregir conversión para números flotantes que terminan en .0
            if isinstance(hijo_val, float) and hijo_val == int(hijo_val):
                hijo = str(int(hijo_val)).strip()
            else:
                hijo = str(hijo_val).strip()
            depto = str(depto_val).strip()

            if not hijo:
                self._add_to_log(f'Fila {index + 1}: Saltada, nombre de hijo vacío.')
                continue
            if not depto:
                self._add_to_log(f'Fila {index + 1}: Saltada, nombre de departamento vacío para hijo "{hijo}".')
                continue

            hijo_path = os.path.join(input_dir, hijo)
            depto_target_path_base = depto_paths.get(depto)

            self.status_label.config(text=f'Procesando: {hijo} → {depto}')
            self._add_to_log(f'Intentando mover: {hijo_path}  ==>  {os.path.join(depto_target_path_base, hijo) if depto_target_path_base else "N/A"}')


            if depto_target_path_base and os.path.exists(hijo_path) and os.path.isdir(hijo_path):
                try:
                    final_destination_for_hijo = os.path.join(depto_target_path_base, hijo)
                    if os.path.exists(final_destination_for_hijo):
                        self._add_to_log(f'Advertencia: Carpeta {hijo} ya existe en {depto_target_path_base}. Se omite el movimiento.')
                    else:
                        shutil.move(hijo_path, depto_target_path_base)
                        self._add_to_log(f'OK: Carpeta {hijo} movida a {depto_target_path_base}')
                        processed_count += 1
                except Exception as e:
                    self._add_to_log(f'ERROR al mover {hijo_path} a {depto_target_path_base}: {e}')
            elif not depto_target_path_base:
                self._add_to_log(f'Error: Departamento "{depto}" no válido o no se pudo crear su carpeta para "{hijo}".')
            elif not os.path.exists(hijo_path):
                self._add_to_log(f'Error: Carpeta de entrada no existe: {hijo_path}')
            elif not os.path.isdir(hijo_path):
                self._add_to_log(f'Error: Elemento de entrada no es una carpeta: {hijo_path}')
            
            self.master.update_idletasks()


        self.status_label.config(text='Renombrando carpetas de departamento...')
        self.master.update_idletasks()
        for depto_key, depto_path_original in list(depto_paths.items()):
            if not os.path.exists(depto_path_original):
                self._add_to_log(f"Info: Carpeta {depto_path_original} no encontrada para renombrar.")
                continue
            try:
                num_sub = len([
                    name for name in os.listdir(depto_path_original)
                    if os.path.isdir(os.path.join(depto_path_original, name))
                ])
                
                new_name_base = depto_key
                if include_count:
                    new_name = f"{new_name_base} ({num_sub} SKU)"
                else:
                    new_name = new_name_base
                
                current_basename = os.path.basename(depto_path_original)

                if new_name != current_basename:
                    new_final_path = os.path.join(output_dir, new_name)
                    
                    if os.path.exists(new_final_path) and new_final_path.lower() != depto_path_original.lower():
                         self._add_to_log(f'Conflicto: {new_final_path} ya existe. No se renombró {current_basename}.')
                    elif new_final_path.lower() == depto_path_original.lower() and new_final_path != depto_path_original:
                        os.rename(depto_path_original, new_final_path)
                        depto_paths[depto_key] = new_final_path
                        self._add_to_log(f'Renombrada (ajuste mayús/minús): {current_basename} → {new_name}')
                    elif new_final_path.lower() != depto_path_original.lower():
                        os.rename(depto_path_original, new_final_path)
                        depto_paths[depto_key] = new_final_path 
                        self._add_to_log(f'Renombrada: {current_basename} → {new_name}')

            except Exception as e:
                self._add_to_log(f'ERROR al renombrar/contar en {depto_path_original}: {e}')
            self.master.update_idletasks()

        self.progress_var.set(100)
        self.status_label.config(text=f'Completado. {processed_count} carpetas procesadas.')
        self._add_to_log(f'--- PROCESO COMPLETADO --- {processed_count} carpetas movidas.')
        messagebox.showinfo('Éxito', f'Organización completada. Se procesaron {processed_count} carpetas.', parent=self.master)

    def start_organization_process(self):
        excel_file = self.excel_file_var.get()
        input_dir = self.input_dir_var.get()
        output_dir = self.output_dir_var.get()
        child_col = self.child_col_var.get().strip()
        depto_col = self.depto_col_var.get().strip()
        include_count = self.include_count_var.get()

        if not child_col:
            child_col = 'upc_ripley'
            self.child_col_var.set(child_col)
        if not depto_col:
            depto_col = 'coddepto'
            self.depto_col_var.set(depto_col)

        if not excel_file or not input_dir or not output_dir:
            messagebox.showwarning('Advertencia', 'Seleccione todas las rutas y asegúrese de que las columnas estén definidas.', parent=self.master)
            return

        self.progress_var.set(0)
        self.status_label.config(text='Iniciando proceso...')
        
        # CORREGIDO: Usar self.log_text.text.config() para el estado
        self.log_text.text.config(state=NORMAL)
        self.log_text.delete('1.0', END) # .delete() debería estar bien delegado
        self._add_to_log("--- INICIANDO PROCESO DE ORGANIZACIÓN ---")

        self.btn_start.config(state=DISABLED)

        try:
            self._organize_folders_logic(
                excel_file, input_dir, output_dir,
                child_col, depto_col, include_count
            )
        except Exception as e:
            self._add_to_log(f"Error catastrófico durante la organización: {e}")
            messagebox.showerror("Error Inesperado", f"Ocurrió un error durante la organización:\n{e}", parent=self.master)
            self.status_label.config(text='Error crítico durante la organización.')
        finally:
            self.btn_start.config(state=NORMAL)
            self.status_label.config(text='Proceso finalizado. Listo para otra operación.')
            self.progress_var.set(0)

if __name__ == "__main__":
    root = ttk.Window()
    setup_theme(root)
    app = DepartamentalizarApp(root)
    root.mainloop()