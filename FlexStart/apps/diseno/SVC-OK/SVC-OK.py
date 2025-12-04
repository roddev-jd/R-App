import sys
import os
import shutil
import pandas as pd
import threading
import queue # Para comunicación entre hilos

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

class FolderMoverThread(threading.Thread):
    def __init__(self, planilla_path, src_dir, dst_dir, ui_queue):
        super().__init__()
        self.planilla_path = planilla_path
        self.src_dir = src_dir
        self.dst_dir = dst_dir
        self.ui_queue = ui_queue
        self._stop_event = threading.Event() # Para posible cancelación futura

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            self.ui_queue.put(("log", 'Leyendo planilla...'))
            # Leer solo la columna necesaria y convertir a string para asegurar compatibilidad
            df = pd.read_excel(self.planilla_path, usecols=['Composición Producto'], dtype={'Composición Producto': str})
            valid_items_from_excel = set(df['Composición Producto'].dropna().str.strip())

            self.ui_queue.put(("log", f'Planilla leída. {len(valid_items_from_excel)} elementos válidos encontrados.'))

            if not os.path.isdir(self.src_dir):
                raise FileNotFoundError(f"El directorio fuente no existe: {self.src_dir}")
            if not os.path.isdir(self.dst_dir):
                os.makedirs(self.dst_dir, exist_ok=True) # Crear destino si no existe
                self.ui_queue.put(("log", f'Directorio destino creado: {self.dst_dir}'))

            items_in_src_dir = [d for d in os.listdir(self.src_dir) if os.path.isdir(os.path.join(self.src_dir, d))]
            total_folders_to_check = len(items_in_src_dir)
            self.ui_queue.put(("log", f'Se analizarán {total_folders_to_check} carpetas en {self.src_dir}'))

            moved_count = 0
            processed_count = 0

            for i, folder_name in enumerate(items_in_src_dir, 1):
                if self._stop_event.is_set():
                    self.ui_queue.put(("log", "Proceso cancelado por el usuario."))
                    self.ui_queue.put(("finished", False, "Proceso cancelado.")) # Indicar que no terminó ok
                    return

                processed_count = i
                current_folder_path = os.path.join(self.src_dir, folder_name)

                if folder_name not in valid_items_from_excel:
                    msg = f'Moviendo {folder_name}...'
                    self.ui_queue.put(("log", msg))
                    destination_folder_path = os.path.join(self.dst_dir, folder_name)
                    try:
                        if os.path.exists(destination_folder_path):
                            self.ui_queue.put(("log", f'ADVERTENCIA: La carpeta "{folder_name}" ya existe en el destino. Omitiendo movimiento.'))
                        else:
                            shutil.move(current_folder_path, destination_folder_path)
                            moved_count += 1
                            self.ui_queue.put(("log", f'ÉXITO: "{folder_name}" movida a "{self.dst_dir}".'))
                    except Exception as e:
                        self.ui_queue.put(("log", f'ERROR moviendo "{folder_name}": {e}'))
                else:
                    self.ui_queue.put(("log", f'Omitido "{folder_name}" (en lista de "Composición Producto").'))

                self.ui_queue.put(("progress", processed_count, total_folders_to_check))

            final_message = f'Proceso completado. Carpetas movidas: {moved_count} de {processed_count} analizadas (que no estaban en la lista).'
            self.ui_queue.put(("finished", True, final_message))

        except FileNotFoundError as fnf_e: # Capturar error de archivo no encontrado específicamente
            self.ui_queue.put(("log", f"ERROR CRÍTICO: {fnf_e}"))
            self.ui_queue.put(("finished", False, str(fnf_e)))
        except Exception as e:
            self.ui_queue.put(("log", f"ERROR INESPERADO en el hilo de trabajo: {e}"))
            self.ui_queue.put(("finished", False, str(e)))


class FolderMoverApp:
    def __init__(self, master):
        self.master = master
        master.title('SEPARADOR DE CARPETAS OK REDACCIÓN') # Título actualizado
        # master.geometry("800x650") # Geometría se establece al final

        self.ui_queue = queue.Queue()
        self.worker_thread = None

        # Variables de Tkinter
        self.planilla_path_var = tk.StringVar()
        self.source_dir_var = tk.StringVar()
        self.dest_dir_var = tk.StringVar()
        self.status_text_var = tk.StringVar(value="Esperando...")
        self.progress_var = tk.DoubleVar(value=0.0)

        self._build_ui()
        self.master.protocol("WM_DELETE_WINDOW", self._on_closing) # Manejar cierre

    def _build_ui(self):
        main_frame = ttk.Frame(self.master, padding="15 15 15 15")
        main_frame.pack(fill=BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1) # Columna de Entries se expande

        # --- Fila 0: Planilla ---
        ttk.Label(main_frame, text="Planilla:").grid(row=0, column=0, sticky=W, padx=(0,5), pady=5)
        entry_planilla = ttk.Entry(main_frame, textvariable=self.planilla_path_var)
        entry_planilla.grid(row=0, column=1, sticky=EW, pady=5)
        btn_browse_planilla = ttk.Button(main_frame, text="Examinar", command=self.select_planilla, bootstyle="outline-secondary")
        btn_browse_planilla.grid(row=0, column=2, sticky=E, padx=(5,0), pady=5)

        # --- Fila 1: Carpeta Fuente ---
        ttk.Label(main_frame, text="Carpetas a Analizar:").grid(row=1, column=0, sticky=W, padx=(0,5), pady=5)
        entry_source = ttk.Entry(main_frame, textvariable=self.source_dir_var)
        entry_source.grid(row=1, column=1, sticky=EW, pady=5)
        btn_browse_source = ttk.Button(main_frame, text="Examinar", command=self.select_source, bootstyle="outline-secondary")
        btn_browse_source.grid(row=1, column=2, sticky=E, padx=(5,0), pady=5)

        # --- Fila 2: Carpeta Destino ---
        ttk.Label(main_frame, text="Destino (no coincidentes):").grid(row=2, column=0, sticky=W, padx=(0,5), pady=5)
        entry_dest = ttk.Entry(main_frame, textvariable=self.dest_dir_var)
        entry_dest.grid(row=2, column=1, sticky=EW, pady=5)
        btn_browse_dest = ttk.Button(main_frame, text="Examinar", command=self.select_dest, bootstyle="outline-secondary")
        btn_browse_dest.grid(row=2, column=2, sticky=E, padx=(5,0), pady=5)

        # --- Fila 3: Botones de Acción ---
        action_buttons_frame = ttk.Frame(main_frame)
        action_buttons_frame.grid(row=3, column=0, columnspan=3, sticky=E, pady=(10,5))

        self.run_btn = ttk.Button(action_buttons_frame, text="Mover Carpetas", command=self.start_process, bootstyle="success")
        self.run_btn.pack(side=LEFT, padx=(0,10)) # Cambiado a LEFT para orden original

        quit_btn = ttk.Button(action_buttons_frame, text="Salir", command=self._on_closing, bootstyle="secondary")
        quit_btn.pack(side=LEFT)


        # --- Fila 4: Barra de Progreso ---
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100, mode='determinate', bootstyle="info")
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky=EW, pady=(5,0))

        # --- Fila 5: Etiqueta de Estado ---
        status_label = ttk.Label(main_frame, textvariable=self.status_text_var, anchor=W)
        status_label.grid(row=5, column=0, columnspan=3, sticky=EW, pady=(0,10))

        # --- Fila 6: Log ---
        log_frame = ttk.LabelFrame(main_frame, text="Log de Operaciones", padding=(10,5), bootstyle="info")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=NSEW)
        main_frame.rowconfigure(6, weight=1) # Hacer que la fila del log se expanda
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_area = ScrolledText(log_frame, state=DISABLED, wrap=WORD, height=10, autohide=True)
        # El atributo 'text' del ScrolledText es el widget Text subyacente.
        # La inicialización con state=DISABLED generalmente funciona bien.
        self.log_area.grid(row=0, column=0, sticky=NSEW)

    def _add_to_log(self, message):
        self.log_area.text.config(state=NORMAL) # MODIFICADO AQUÍ
        self.log_area.insert(END, message + "\n")
        self.log_area.see(END)
        self.log_area.text.config(state=DISABLED) # MODIFICADO AQUÍ

    def select_planilla(self):
        path = filedialog.askopenfilename(title='Seleccionar planilla', filetypes=[('Archivos Excel', '*.xlsx *.xls')])
        if path:
            self.planilla_path_var.set(path)
            # Auto-llenar directorio fuente si está vacío
            base_dir = os.path.dirname(path)
            if not self.source_dir_var.get():
                self.source_dir_var.set(base_dir)

    def select_source(self):
        path = filedialog.askdirectory(title='Seleccionar carpeta a analizar')
        if path:
            self.source_dir_var.set(path)

    def select_dest(self):
        path = filedialog.askdirectory(title='Seleccionar carpeta destino para no coincidentes')
        if path:
            self.dest_dir_var.set(path)

    def start_process(self):
        plan_path = self.planilla_path_var.get()
        src_path = self.source_dir_var.get()
        dst_path = self.dest_dir_var.get()

        if not all([plan_path, src_path, dst_path]):
            messagebox.showwarning('Faltan datos', 'Debe seleccionar todos los campos: Planilla, Carpeta a Analizar y Destino.')
            return
        if not os.path.isfile(plan_path):
            messagebox.showerror('Error de Archivo', f"La ruta de la planilla no es válida:\n{plan_path}")
            return
        if not os.path.isdir(src_path):
             messagebox.showerror('Error de Carpeta', f"La ruta de la carpeta a analizar no es válida:\n{src_path}")
             return
        # No es necesario que dst_path exista aún, el worker lo creará.

        self.run_btn.config(state=DISABLED)
        self.log_area.text.config(state=NORMAL) # MODIFICADO AQUÍ
        self.log_area.delete('1.0', END)
        self.log_area.text.config(state=DISABLED) # MODIFICADO AQUÍ
        self._add_to_log("Iniciando proceso...")
        self.status_text_var.set("Iniciando...")
        self.progress_var.set(0)

        self.worker_thread = FolderMoverThread(plan_path, src_path, dst_path, self.ui_queue)
        self.worker_thread.start()
        self.master.after(100, self._check_queue) # Iniciar el chequeo de la cola

    def _check_queue(self):
        try:
            while True: # Procesar todos los mensajes en la cola
                message_tuple = self.ui_queue.get_nowait()
                msg_type = message_tuple[0]

                if msg_type == "log":
                    self._add_to_log(message_tuple[1])
                elif msg_type == "progress":
                    count, total = message_tuple[1], message_tuple[2]
                    if total > 0 : # Evitar división por cero si no hay carpetas
                        self.progress_bar.config(maximum=total) # Asegurar que el máximo está bien puesto
                        self.progress_var.set(count)
                        self.status_text_var.set(f'Procesados {count} de {total}')
                    else:
                        self.progress_var.set(0)
                        self.status_text_var.set('No hay carpetas para procesar en origen.')
                elif msg_type == "finished":
                    ok, msg_text = message_tuple[1], message_tuple[2]
                    self.status_text_var.set(msg_text)
                    if ok:
                        messagebox.showinfo('Proceso Listo', msg_text)
                    else:
                        messagebox.showerror('Error en Proceso', msg_text)
                    self.run_btn.config(state=NORMAL)
                    self.worker_thread = None # Limpiar referencia al hilo
                    return # Detener el chequeo de la cola si el proceso terminó
        except queue.Empty:
            pass # La cola está vacía, no hay nada que hacer por ahora

        # Si el hilo sigue vivo, programar otra revisión
        if self.worker_thread and self.worker_thread.is_alive():
            self.master.after(100, self._check_queue)
        elif self.worker_thread and not self.worker_thread.is_alive(): # El hilo terminó pero no envió "finished" o ya se procesó
            self.run_btn.config(state=NORMAL) # Asegurar que el botón se rehabilita
            self.worker_thread = None


    def _on_closing(self):
        """Maneja el cierre de la ventana."""
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Confirmar Salida", "El proceso está en ejecución. ¿Está seguro que desea salir? Esto detendrá el proceso actual."):
                self.worker_thread.stop() # Señal para que el hilo se detenga si es posible
                # Esperar un poco a que el hilo termine si se implementa la espera.
                # Por ahora, simplemente destruimos. El hilo daemon podría seguir un poco.
                self.master.destroy()
            else:
                return # No cerrar
        else:
            self.master.destroy()


if __name__ == '__main__':
    root = ttk.Window()
    setup_theme(root)
    app = FolderMoverApp(root)
    root.geometry("800x600") # Ajusta según necesidad
    root.mainloop()