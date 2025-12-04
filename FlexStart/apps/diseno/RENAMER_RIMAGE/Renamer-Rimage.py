#!/usr/bin/env python3
# -*- coding: utf‑8 -*-

import os
import re
import threading
import queue # For thread-safe GUI updates
import tkinter as tk
from tkinter import filedialog, messagebox # Keep standard dialogs
import ttkbootstrap as ttk
from ttkbootstrap.constants import * # ttkbootstrap constants
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

# --- Reglas de mapeo (sin cambios funcionales) ---
IMAGE_RE = re.compile(r"^(image)(\d+)", re.IGNORECASE)

def nuevo_nombre_archivo(nombre_carpeta_base: str, nombre_archivo_original: str) -> str | None:
    """Devuelve el nuevo nombre (sin ruta) o None si no aplica."""
    base_original, ext_original = os.path.splitext(nombre_archivo_original)
    ext_normalizada = ext_original.lower()

    if ext_normalizada not in {'.jpg', '.jpeg', '.png', '.webp'}:
        return None  # extensión no soportada

    base_original_lc = base_original.lower()

    if base_original_lc.startswith("full_image"):
        # Usa el nombre de la carpeta base para el nuevo nombre
        return f"{nombre_carpeta_base}_2{ext_normalizada}"

    m = IMAGE_RE.match(base_original_lc)
    if m:
        num = m.group(2)  # digitos después de 'image'
        # Usa el nombre de la carpeta base para el nuevo nombre
        return f"{nombre_carpeta_base}-{num}{ext_normalizada}"

    return None  # no coincide la regla


# --- Lógica principal (adaptada para usar cola de actualizaciones) ---
def procesar_renombrado_en_hilo(ruta_raiz: str, update_queue: queue.Queue):
    """Realiza el renombrado y envía actualizaciones a la GUI a través de la cola."""
    total_archivos_a_inspeccionar, procesados, renombrados, omitidos, conflictos = 0, 0, 0, 0, 0

    try:
        # Primera pasada: contar cuántos archivos vamos a inspeccionar
        for _, _, files_list in os.walk(ruta_raiz):
            total_archivos_a_inspeccionar += len(files_list)

        if total_archivos_a_inspeccionar == 0:
            update_queue.put(("status", "No se encontraron archivos para procesar."))
            update_queue.put(("finished", {
                'procesados': 0, 'renombrados': 0, 'omitidos': 0, 'conflictos': 0, 'total_inspeccionados': 0
            }))
            return

        update_queue.put(("progress_max", total_archivos_a_inspeccionar)) # Para configurar el máximo de la barra

        for dir_actual, _, files_en_dir_actual in os.walk(ruta_raiz):
            nombre_carpeta_actual_base = os.path.basename(dir_actual)
            for nombre_archivo_actual in files_en_dir_actual:
                procesados += 1
                
                # Llamar a la función de lógica de nombres
                nuevo_nombre_final = nuevo_nombre_archivo(nombre_carpeta_actual_base, nombre_archivo_actual)

                if nuevo_nombre_final is None:
                    omitidos += 1
                else:
                    ruta_origen = os.path.join(dir_actual, nombre_archivo_actual)
                    ruta_destino = os.path.join(dir_actual, nuevo_nombre_final)
                    
                    if ruta_origen == ruta_destino : # Evitar renombrar a sí mismo
                        omitidos +=1 
                    elif os.path.exists(ruta_destino):
                        conflictos += 1
                    else:
                        try:
                            os.rename(ruta_origen, ruta_destino)
                            renombrados += 1
                        except Exception as e:
                            # Si hay un error en el renombrado, se cuenta como omitido o conflicto si aplica
                            update_queue.put(("log", f"Error renombrando '{nombre_archivo_actual}' a '{nuevo_nombre_final}': {e}"))
                            omitidos +=1 # O manejar como un nuevo tipo de error

                # Actualizar barra y texto de estado vía cola
                # Enviar el número de archivos procesados para la barra de progreso
                update_queue.put(("progress_value", procesados))
                status_text = (f"Procesados: {procesados}/{total_archivos_a_inspeccionar}  |  "
                               f"Renombrados: {renombrados}  |  Omitidos: {omitidos}  |  Conflictos: {conflictos}")
                update_queue.put(("status", status_text))
        
        # Enviar resultados finales
        results = {
            'procesados': procesados,
            'renombrados': renombrados,
            'omitidos': omitidos,
            'conflictos': conflictos,
            'total_inspeccionados': total_archivos_a_inspeccionar
        }
        update_queue.put(("finished", results))

    except Exception as e:
        update_queue.put(("log", f"Error inesperado en el procesamiento: {e}"))
        update_queue.put(("status", "Error durante el procesamiento."))
        update_queue.put(("finished", { # Enviar un 'finished' para re-habilitar UI
            'procesados': procesados, 'renombrados': renombrados, 'omitidos': omitidos, 'conflictos': conflictos, 'error': str(e)
        }))


# --- Interfaz Tkinter (ttkbootstrap) ---
class AppRenombrador(ttk.Window):
    def __init__(self):
        super().__init__()
        setup_theme(self)
        self.title("Renombrador de Imágenes (ttkbootstrap)")
        self.geometry("600x220") # Ajustar tamaño si es necesario
        self.resizable(False, False)

        self.update_queue = queue.Queue()
        self.worker_thread = None

        # Variables de Tkinter
        self.dir_var = tk.StringVar()
        self.estado_var = tk.StringVar(value="Listo.")

        self._build_ui()
        self._process_gui_updates() # Iniciar el listener de la cola

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=True)

        # Configurar peso de columnas para expansión de Entry
        main_frame.columnconfigure(0, weight=1) # Columna del label
        main_frame.columnconfigure(1, weight=3) # Columna del entry
        # Columna del botón no necesita peso si no se expande

        ttk.Label(main_frame, text="Carpeta a analizar:").grid(row=0, column=0, columnspan=3, sticky=W, pady=(0,2))
        
        self.entry_directorio = ttk.Entry(main_frame, textvariable=self.dir_var, width=60)
        self.entry_directorio.grid(row=1, column=0, columnspan=2, sticky=EW, pady=2)
        
        self.btn_examinar = ttk.Button(main_frame, text="Examinar…", command=self.elegir_carpeta, bootstyle="outline-secondary")
        self.btn_examinar.grid(row=1, column=2, padx=(5,0), pady=2, sticky=E)

        self.btn_iniciar = ttk.Button(main_frame, text="Iniciar Renombrado", command=self.iniciar_proceso, bootstyle="success", width=20)
        self.btn_iniciar.grid(row=2, column=0, columnspan=3, pady=15)

        self.progreso_barra = ttk.Progressbar(main_frame, orient=HORIZONTAL, mode="determinate", length=100, bootstyle="info-striped") # Usar info-striped
        self.progreso_barra.grid(row=3, column=0, columnspan=3, sticky=EW, pady=(0,5))

        self.lbl_estado = ttk.Label(main_frame, textvariable=self.estado_var, anchor=W)
        self.lbl_estado.grid(row=4, column=0, columnspan=3, pady=(5, 0), sticky=W)
        
        self.protocol("WM_DELETE_WINDOW", self._on_closing)


    def elegir_carpeta(self):
        carpeta_seleccionada = filedialog.askdirectory(title="Selecciona la carpeta raíz a procesar")
        if carpeta_seleccionada:
            self.dir_var.set(carpeta_seleccionada)
            self.estado_var.set(f"Carpeta seleccionada: {os.path.basename(carpeta_seleccionada)}")

    def iniciar_proceso(self):
        ruta_directorio = self.dir_var.get().strip()
        if not ruta_directorio or not os.path.isdir(ruta_directorio):
            messagebox.showerror("Ruta no válida", "Selecciona una carpeta válida antes de continuar.", parent=self)
            return

        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Proceso en curso", "Un proceso de renombrado ya está en ejecución.", parent=self)
            return

        self.btn_iniciar.config(state=DISABLED)
        self.progreso_barra["value"] = 0
        self.progreso_barra["maximum"] = 100 # Default, se ajustará con mensaje 'progress_max'
        self.estado_var.set("Iniciando análisis...")

        self.worker_thread = threading.Thread(
            target=procesar_renombrado_en_hilo, 
            args=(ruta_directorio, self.update_queue), 
            daemon=True
        )
        self.worker_thread.start()

    def _process_gui_updates(self):
        try:
            while True: # Procesar todos los mensajes disponibles sin bloquear
                message_type, data = self.update_queue.get_nowait()

                if message_type == "progress_max":
                    self.progreso_barra["maximum"] = data if data > 0 else 100
                elif message_type == "progress_value":
                    self.progreso_barra["value"] = data
                elif message_type == "status":
                    self.estado_var.set(data)
                elif message_type == "log": # Podríamos tener un ScrolledText para logs más detallados
                    print(f"LOG: {data}") # Por ahora, imprimir en consola
                elif message_type == "finished":
                    self._handle_finished_process(data)
        
        except queue.Empty: # No hay más mensajes en la cola
            pass
        finally:
            # Volver a programar la revisión de la cola
            if self.winfo_exists(): # Solo si la ventana aún existe
                self.after(100, self._process_gui_updates)

    def _handle_finished_process(self, results):
        self.btn_iniciar.config(state=NORMAL)
        self.progreso_barra["value"] = 0 # O el máximo si se quiere mostrar completado
        
        if 'error' in results:
            self.estado_var.set(f"Proceso finalizado con error: {results.get('error')}")
            messagebox.showerror("Error en Proceso", f"El proceso de renombrado encontró un error crítico:\n{results.get('error')}", parent=self)
        else:
            self.estado_var.set("Proceso completado. Listo.")
            summary_message = (
                f"Archivos inspeccionados: {results.get('total_inspeccionados', results.get('procesados',0))}\n" # 'procesados' es el total de archivos iterados
                f"Renombrados: {results.get('renombrados',0)}\n"
                f"Omitidos (sin regla o sin cambios): {results.get('omitidos',0)}\n"
                f"Conflictos (archivo destino ya existía): {results.get('conflictos',0)}"
            )
            messagebox.showinfo("Renombrado Terminado", summary_message, parent=self)
        self.worker_thread = None # Limpiar referencia al hilo

    def _on_closing(self):
        """Manejar cierre de ventana."""
        if self.worker_thread and self.worker_thread.is_alive():
            if messagebox.askyesno("Proceso en Curso",
                                   "El proceso de renombrado está en curso. ¿Está seguro de que desea salir?",
                                   parent=self):
                # Nota: El hilo es daemon, se cerrará con la app.
                # No hay un mecanismo de 'stop' implementado para el hilo de trabajo.
                self.destroy()
            # else: El usuario eligió no cerrar.
        else:
            self.destroy()


if __name__ == "__main__":
    app = AppRenombrador()
    app.mainloop()