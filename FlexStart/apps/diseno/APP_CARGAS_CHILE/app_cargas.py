"""
Aplicación para comparar nombres de carpetas con datos en Azure Blob Storage
y generar reportes Excel con coincidencias exactas y relacionadas.
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue
from datetime import datetime
from io import StringIO
from pathlib import Path
import shutil

import pandas as pd
from azure.storage.blob import BlobServiceClient
import keyring


class AppCargas:
    """Aplicación principal para comparar carpetas con datos de Azure Blob"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("APP CARGAS")
        self.root.geometry("750x700")
        
        # Variables
        self.ubicacion_carpetas = tk.StringVar()
        self.container_url = "https://blobaac.blob.core.windows.net/datascience"
        self.blob_name = "tabla_wop_completa.csv"
        self.blob_materialidad = "TABLAS_VERTICA/c1_materialidad.csv"
        
        # Variables para threading y eventos
        self.processing = False
        self.event_queue = queue.Queue()
        self.progress_var = tk.DoubleVar()
        self.progress_text = tk.StringVar(value="Listo")
        
        # Variable para controlar el JOIN con materialidad (ahora siempre True)
        self.usar_materialidad = tk.BooleanVar(value=True)
        
        # Variable para controlar el agrupamiento por departamento
        self.agrupar_por_depto = tk.BooleanVar(value=False)
        
        # Variables para planillas adicionales
        self.generar_moda = tk.BooleanVar(value=False)
        self.generar_producto = tk.BooleanVar(value=False)
        self.fecha_planilla = tk.StringVar(value="")
        self.modelo_moda = tk.StringVar(value="")
        self.medidas_modelo = tk.StringVar(value="")
        
        # Variables para archivo de responsables
        self.generar_responsables = tk.BooleanVar(value=False)
        
        # Variable para template de email
        self.generar_template_email = tk.BooleanVar(value=False)
        
        # Variables para fuente de datos
        self.fuente_datos = tk.StringVar(value="base_datos")  # "base_datos" o "archivo_local"
        self.archivo_local_path = tk.StringVar(value="")
        
        # Variables para manejo de caché
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
        self.cache_file_principal = os.path.join(self.cache_dir, "tabla_wop_completa.csv")
        self.cache_file_materialidad = os.path.join(self.cache_dir, "c1_materialidad.csv")
        self.cache_status = tk.StringVar(value="Sin caché")
        
        # Crear directorio de caché si no existe
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        self.setup_ui()
        self.start_event_processor()
        self.verificar_cache_status()
        
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        titulo = ttk.Label(main_frame, text="APLICATIVO CARGAS ESTUDIO CHILE", font=("Arial", 14, "bold"))
        titulo.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Selección de ubicación
        ttk.Label(main_frame, text="Ubicación de carpetas:").grid(row=1, column=0, sticky=tk.W, pady=(0, 3))
        
        ubicacion_frame = ttk.Frame(main_frame)
        ubicacion_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 8))
        
        ttk.Entry(ubicacion_frame, textvariable=self.ubicacion_carpetas, width=50).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(ubicacion_frame, text="Seleccionar", command=self.seleccionar_ubicacion).grid(row=0, column=1, padx=(5, 0))
        
        ubicacion_frame.columnconfigure(0, weight=1)
        
        # Selección de fuente de datos
        fuente_frame = ttk.LabelFrame(main_frame, text="Fuente de Datos", padding="5")
        fuente_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 8))
        
        # Radio buttons para seleccionar fuente
        ttk.Radiobutton(fuente_frame, text="Base de datos (Azure Blob Storage)", 
                       variable=self.fuente_datos, value="base_datos",
                       command=self.on_fuente_datos_change).grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
        
        ttk.Radiobutton(fuente_frame, text="Archivo local (Excel/CSV con columnas 'upc_ripley' y 'talla')", 
                       variable=self.fuente_datos, value="archivo_local",
                       command=self.on_fuente_datos_change).grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # Frame para archivo local
        self.archivo_frame = ttk.Frame(fuente_frame)
        self.archivo_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Entry(self.archivo_frame, textvariable=self.archivo_local_path, width=50, state="disabled").grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.btn_seleccionar_archivo = ttk.Button(self.archivo_frame, text="Seleccionar Archivo", 
                                                 command=self.seleccionar_archivo_local, state="disabled")
        self.btn_seleccionar_archivo.grid(row=0, column=1, padx=(5, 0))
        
        self.archivo_frame.columnconfigure(0, weight=1)
        
        
        # Barra de progreso
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(progress_frame, text="Estado:").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(progress_frame, textvariable=self.progress_text).grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        progress_frame.columnconfigure(1, weight=1)
        
        # Checkbox para agrupamiento por departamento
        agrupamiento_frame = ttk.Frame(main_frame)
        agrupamiento_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 5))
        
        self.checkbox_agrupamiento = ttk.Checkbutton(
            agrupamiento_frame, 
            text="Agrupar carpetas por departamento (columna 'depto')",
            variable=self.agrupar_por_depto
        )
        self.checkbox_agrupamiento.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Frame para planillas adicionales
        planillas_frame = ttk.LabelFrame(main_frame, text="Planillas Adicionales", padding="5")
        planillas_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Checkboxes para tipos de planilla
        self.checkbox_moda = ttk.Checkbutton(
            planillas_frame,
            text="Generar planilla MODA (SKU_HIJO_LARGO, Fecha, MODELO)",
            variable=self.generar_moda,
            command=self.on_planilla_change
        )
        self.checkbox_moda.grid(row=0, column=0, sticky=tk.W, pady=(0, 2))
        
        self.checkbox_producto = ttk.Checkbutton(
            planillas_frame,
            text="Generar planilla PRODUCTO (SKU_HIJO_LARGO, Fecha)",
            variable=self.generar_producto,
            command=self.on_planilla_change
        )
        self.checkbox_producto.grid(row=1, column=0, sticky=tk.W, pady=(0, 2))
        
        # Frame para campos de entrada
        self.campos_frame = ttk.Frame(planillas_frame)
        self.campos_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Campo fecha (siempre visible cuando se selecciona una planilla)
        ttk.Label(self.campos_frame, text="Fecha:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.entry_fecha = ttk.Entry(self.campos_frame, textvariable=self.fecha_planilla, width=15)
        self.entry_fecha.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # Campo modelo (solo visible para MODA)
        self.label_modelo = ttk.Label(self.campos_frame, text="MODELO:")
        self.label_modelo.grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.entry_modelo = ttk.Entry(self.campos_frame, textvariable=self.modelo_moda, width=20)
        self.entry_modelo.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Campo medidas del modelo (solo visible para template de email)
        self.label_medidas = ttk.Label(self.campos_frame, text="MEDIDAS:")
        self.label_medidas.grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.entry_medidas = ttk.Entry(self.campos_frame, textvariable=self.medidas_modelo, width=15)
        self.entry_medidas.grid(row=0, column=5, sticky=tk.W)
        
        # Inicialmente ocultar campos
        self.toggle_campos_visibility(False)
        self.toggle_medidas_visibility(False)
        
        # Sección para archivo de responsables
        ttk.Separator(planillas_frame, orient='horizontal').grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(5, 5))
        
        self.checkbox_responsables = ttk.Checkbutton(
            planillas_frame,
            text="Generar archivo de responsables por departamento",
            variable=self.generar_responsables,
            command=self.on_responsables_change
        )
        self.checkbox_responsables.grid(row=4, column=0, sticky=tk.W, pady=(0, 2))
        
        # Nota: Siempre se usa CHILE.xlsx para responsables
        
        # Separador para template de email
        ttk.Separator(planillas_frame, orient='horizontal').grid(row=6, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(5, 5))
        
        # Checkbox para template de email
        self.checkbox_template_email = ttk.Checkbutton(
            planillas_frame,
            text="Generar template HTML para email con información de la carga",
            variable=self.generar_template_email,
            command=self.on_template_email_change
        )
        self.checkbox_template_email.grid(row=7, column=0, sticky=tk.W, pady=(0, 2))
        
        planillas_frame.columnconfigure(0, weight=1)
        
        # Botón de procesamiento
        self.btn_procesar = ttk.Button(main_frame, text="Procesar y Generar Reporte", 
                                      command=self.iniciar_procesamiento)
        self.btn_procesar.grid(row=8, column=0, columnspan=3, pady=5)
        
        # Visor de eventos en tiempo real
        eventos_frame = ttk.LabelFrame(main_frame, text="Eventos en Tiempo Real", padding="3")
        eventos_frame.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        
        self.eventos_text = tk.Text(eventos_frame, height=6, width=70, font=("Consolas", 8))
        self.eventos_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        eventos_scrollbar = ttk.Scrollbar(eventos_frame, orient=tk.VERTICAL, command=self.eventos_text.yview)
        eventos_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.eventos_text.configure(yscrollcommand=eventos_scrollbar.set)
        
        eventos_frame.columnconfigure(0, weight=1)
        eventos_frame.rowconfigure(0, weight=1)
        
        # Configurar grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
    
    def start_event_processor(self):
        """Inicia el procesador de eventos en tiempo real"""
        self.root.after(100, self.process_events)
    
    def process_events(self):
        """Procesa eventos de la cola para actualizar la interfaz"""
        try:
            while True:
                event_type, data = self.event_queue.get_nowait()
                
                if event_type == "log":
                    self.add_log_message(data)
                elif event_type == "progress":
                    self.update_progress(data)
                elif event_type == "status":
                    self.progress_text.set(data)
                elif event_type == "enable_button":
                    self.btn_procesar.config(state=tk.NORMAL)
                elif event_type == "disable_button":
                    self.btn_procesar.config(state=tk.DISABLED)
                    
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_events)
    
    def add_log_message(self, mensaje):
        """Añade un mensaje al visor de eventos con timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {mensaje}\n"
        
        self.eventos_text.insert(tk.END, formatted_message)
        self.eventos_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress(self, value):
        """Actualiza la barra de progreso"""
        self.progress_var.set(value)
        self.root.update_idletasks()
    
    def log_thread_safe(self, mensaje):
        """Envía un mensaje de log de forma thread-safe"""
        self.event_queue.put(("log", mensaje))
    
    def update_status_thread_safe(self, status):
        """Actualiza el estado de forma thread-safe"""
        self.event_queue.put(("status", status))
    
    def update_progress_thread_safe(self, value):
        """Actualiza el progreso de forma thread-safe"""
        self.event_queue.put(("progress", value))
        
    def seleccionar_ubicacion(self):
        """Permite al usuario seleccionar la ubicación de las carpetas"""
        carpeta = filedialog.askdirectory(title="Seleccionar ubicación de carpetas")
        if carpeta:
            self.ubicacion_carpetas.set(carpeta)
            self.add_log_message(f"Ubicación seleccionada: {carpeta}")
    
    def on_fuente_datos_change(self):
        """Controla la habilitación/deshabilitación de controles según la fuente de datos"""
        if self.fuente_datos.get() == "archivo_local":
            # Habilitar controles de archivo local
            self.archivo_frame.children['!entry'].config(state="normal")
            self.btn_seleccionar_archivo.config(state="normal")
        else:
            # Deshabilitar controles de archivo local
            self.archivo_frame.children['!entry'].config(state="disabled")
            self.btn_seleccionar_archivo.config(state="disabled")
    
    def seleccionar_archivo_local(self):
        """Permite seleccionar un archivo Excel o CSV local"""
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo de datos",
            filetypes=[
                ("Archivos Excel", "*.xlsx *.xls"),
                ("Archivos CSV", "*.csv"),
                ("Todos los archivos", "*.*")
            ]
        )
        if archivo:
            self.archivo_local_path.set(archivo)
            self.add_log_message(f"Archivo seleccionado: {archivo}")
    
    def iniciar_procesamiento(self):
        """Inicia el procesamiento en un hilo separado"""
        if self.processing:
            return
            
        if not self.ubicacion_carpetas.get():
            messagebox.showwarning("Advertencia", "Por favor selecciona una ubicación de carpetas")
            return
        
        # Validar campos de planillas adicionales
        if not self.validar_campos_planilla():
            return
        
        self.processing = True
        self.event_queue.put(("disable_button", None))
        self.update_progress(0)
        self.update_status_thread_safe("Iniciando procesamiento...")
        
        # Limpiar el visor de eventos
        self.eventos_text.delete(1.0, tk.END)
        
        # Iniciar procesamiento en hilo separado
        thread = threading.Thread(target=self.procesar_datos_worker)
        thread.daemon = True
        thread.start()
    
    def procesar_datos_worker(self):
        """Worker function que se ejecuta en hilo separado"""
        try:
            self.log_thread_safe("=== INICIANDO PROCESAMIENTO ===")
            
            # Paso 1: Conectar y descargar CSV principal (15%)
            self.update_status_thread_safe("Descargando CSV principal de Azure Blob...")
            self.update_progress_thread_safe(5)
            
            df = self.cargar_datos_principal()
            if df is None:
                return
            
            self.update_progress_thread_safe(15)
            
            # Paso 2: Descargar CSV de materialidad (25%) - siempre activado
            self.update_status_thread_safe("Descargando CSV de materialidad...")
            df_materialidad = self.descargar_csv_materialidad()
            if df_materialidad is None:
                self.log_thread_safe("⚠️ Error al descargar materialidad, continuando sin enriquecimiento")
            else:
                self.log_thread_safe("✅ CSV de materialidad descargado exitosamente")
            
            self.update_progress_thread_safe(25)
            
            # Paso 3: Obtener nombres de carpetas (35%)
            self.update_status_thread_safe("Escaneando carpetas...")
            nombres_carpetas = self.obtener_nombres_carpetas(self.ubicacion_carpetas.get())
            if not nombres_carpetas:
                return
            
            self.update_progress_thread_safe(35)
            
            # Paso 4: Encontrar coincidencias (55%)
            self.update_status_thread_safe("Buscando coincidencias...")
            df_exactas, df_relacionadas = self.encontrar_coincidencias(df, nombres_carpetas)
            
            if df_exactas.empty:
                self.log_thread_safe("No se encontraron coincidencias exactas")
                self.update_status_thread_safe("Sin coincidencias")
                messagebox.showinfo("Información", "No se encontraron coincidencias entre los nombres de carpetas y el CSV")
                return
            
            self.update_progress_thread_safe(55)
            
            # Paso 5: Enriquecer con datos de materialidad (80%) - siempre activado
            if df_materialidad is not None:
                self.update_status_thread_safe("Enriqueciendo con datos de materialidad...")
                df_relacionadas_enriquecido, df_exactas_enriquecido = self.enriquecer_con_materialidad(
                    df_relacionadas, df_exactas, df_materialidad
                )
            else:
                self.log_thread_safe("⚠️ Sin datos de materialidad disponibles - continuando sin enriquecimiento")
                df_relacionadas_enriquecido, df_exactas_enriquecido = df_relacionadas, df_exactas
            
            self.update_progress_thread_safe(80)
            
            # Paso 6: Generar Excel (90%)
            self.update_status_thread_safe("Generando archivo Excel...")
            self.generar_excel(df_relacionadas_enriquecido, df_exactas_enriquecido)
            
            self.update_progress_thread_safe(90)
            
            # Paso 7: Planillas adicionales (92%) - solo si está activado
            if self.generar_moda.get() or self.generar_producto.get():
                self.update_status_thread_safe("Generando planillas adicionales...")
                
                if self.generar_moda.get():
                    self.generar_planilla_adicional(nombres_carpetas, 'moda')
                
                if self.generar_producto.get():
                    self.generar_planilla_adicional(nombres_carpetas, 'producto')
            
            self.update_progress_thread_safe(92)
            
            # Paso 8: Archivo de responsables (95%) - solo si está activado
            df_responsables_resultado = None
            if self.generar_responsables.get():
                self.update_status_thread_safe("Generando archivo de responsables...")
                
                # Extraer departamentos de las coincidencias exactas
                if 'depto' in df_exactas.columns:
                    departamentos_encontrados = df_exactas['depto'].dropna().tolist()

                    self.log_thread_safe(f"Generando archivo de responsables para {len(departamentos_encontrados)} departamentos")
                    ruta_responsables = self.generar_archivo_responsables(departamentos_encontrados)
                    
                    # Cargar el archivo generado para usar en el template de email
                    if ruta_responsables and os.path.exists(ruta_responsables):
                        try:
                            import pandas as pd
                            df_responsables_resultado = pd.read_excel(ruta_responsables)
                            self.log_thread_safe(f"Datos de responsables cargados para template de email: {len(df_responsables_resultado)} registros")
                        except Exception as e:
                            self.log_thread_safe(f"⚠️ Error al cargar responsables para template: {e}")
                else:
                    self.log_thread_safe("⚠️ No se encontró columna 'depto' para generar archivo de responsables")
            
            self.update_progress_thread_safe(95)
            
            # Paso 9: Template de Email (97%) - solo si está activado
            if self.generar_template_email.get():
                self.update_status_thread_safe("Generando template de email...")
                self.generar_template_email_metodo(df_exactas_enriquecido, df_responsables_resultado)
            
            self.update_progress_thread_safe(97)
            
            # Paso 10: Agrupamiento por departamento (100%) - solo si está activado
            if self.agrupar_por_depto.get():
                self.update_status_thread_safe("Agrupando carpetas por departamento...")
                # El agrupamiento se ejecuta en generar_excel() después de mostrar el mensaje de éxito
            
            self.update_progress_thread_safe(100)
            self.update_status_thread_safe("Procesamiento completado")
            self.log_thread_safe("=== PROCESAMIENTO COMPLETADO ===")
            
        except Exception as e:
            self.log_thread_safe(f"Error en procesamiento: {e}")
            self.update_status_thread_safe("Error en procesamiento")
            messagebox.showerror("Error", f"Error durante el procesamiento: {e}")
        finally:
            self.processing = False
            self.event_queue.put(("enable_button", None))
    
    def obtener_connection_string(self):
        """Obtiene la cadena de conexión desde el llavero del sistema"""
        try:
            # Intentar obtener desde el llavero
            connection_string = keyring.get_password("azure_storage", "blobaac")
            if connection_string:
                return connection_string
            
            # Si no está en el llavero, usar la variable de entorno
            connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                return connection_string
            
            # Como último recurso, usar la cadena proporcionada
            return 'DefaultEndpointsProtocol=https;AccountName=blobaac;AccountKey=hb5SiEOct+sJTsCermzS1uxr1S/+3NtjUvQ8NAPCLKMOO+GDUekrgW9Q5MX5XRW04IiqKsj/RzJ1ShZvEfd/kA==;EndpointSuffix=core.windows.net'
            
        except Exception as e:
            self.log_thread_safe(f"Error al obtener credenciales: {e}")
            return None
    
    def cargar_datos_principal(self):
        """Carga los datos principales desde la fuente seleccionada (Azure Blob o archivo local)"""
        if self.fuente_datos.get() == "archivo_local":
            return self.cargar_archivo_local()
        else:
            return self.descargar_csv_blob()
    
    def cargar_archivo_local(self):
        """Carga datos desde un archivo Excel o CSV local"""
        try:
            archivo_path = self.archivo_local_path.get()
            if not archivo_path or not os.path.exists(archivo_path):
                raise Exception("Debe seleccionar un archivo válido")
            
            self.log_thread_safe(f"Cargando archivo local: {archivo_path}")
            
            # Determinar el tipo de archivo y cargar
            if archivo_path.lower().endswith(('.xlsx', '.xls')):
                df = pd.read_excel(archivo_path)
                self.log_thread_safe(f"Archivo Excel cargado. Filas: {len(df)}, Columnas: {len(df.columns)}")
            else:
                df = pd.read_csv(archivo_path)
                self.log_thread_safe(f"Archivo CSV cargado. Filas: {len(df)}, Columnas: {len(df.columns)}")
            
            # Verificar que tenga las columnas mínimas necesarias para archivo local
            columnas_requeridas = ['upc_ripley']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
            if columnas_faltantes:
                raise Exception(f"El archivo debe contener las columnas: {', '.join(columnas_faltantes)}")
            
            # Crear una columna 'sku_hijo_largo' que apunte a 'upc_ripley' para compatibilidad
            df['sku_hijo_largo'] = df['upc_ripley']
            self.log_thread_safe("✓ Columna 'upc_ripley' mapeada como 'sku_hijo_largo' para compatibilidad")
            
            # Mapear columnas adicionales para compatibilidad con el sistema existente
            mapeo_columnas = {
                'codskupadrelargo': 'sku_padre_largo',
                'desskuhijo': 'sku_descripcion', 
                'coddepto': 'depto',
                'compromiso_r': 'COMPROMISO_R',
                'codskupadre': 'sku_padre_corto'
            }
            
            for col_orig, col_dest in mapeo_columnas.items():
                if col_orig in df.columns and col_dest not in df.columns:
                    df[col_dest] = df[col_orig]
                    self.log_thread_safe(f"✓ Columna '{col_orig}' mapeada como '{col_dest}' para compatibilidad")
            
            # Verificar si tiene la columna 'talla' 
            if 'talla' in df.columns:
                self.log_thread_safe("✓ Columna 'talla' encontrada en el archivo")
            else:
                self.log_thread_safe("⚠️ Columna 'talla' no encontrada en el archivo")
            
            return df
            
        except Exception as e:
            self.log_thread_safe(f"Error al cargar archivo local: {e}")
            raise e

    def descargar_csv_blob(self):
        """Descarga el CSV desde Azure Blob Storage o lo carga desde caché"""
        try:
            # Verificar si existe en caché
            if os.path.exists(self.cache_file_principal):
                self.log_thread_safe("Archivo encontrado en caché, cargando...")
                
                # Mostrar información del caché
                size_mb = os.path.getsize(self.cache_file_principal) / (1024 * 1024)
                mod_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file_principal))
                self.log_thread_safe(f"Archivo en caché: {size_mb:.1f}MB - Última modificación: {mod_time.strftime('%d/%m/%Y %H:%M')}")
                
                # Cargar desde caché
                df = pd.read_csv(self.cache_file_principal)
                self.log_thread_safe(f"CSV cargado desde caché. Filas: {len(df)}, Columnas: {len(df.columns)}")
                return df
            
            # No existe en caché, descargar desde Azure
            self.log_thread_safe("Archivo no encontrado en caché, descargando desde Azure Blob Storage...")
            
            connection_string = self.obtener_connection_string()
            if not connection_string:
                raise Exception("No se pudo obtener la cadena de conexión")
            
            self.log_thread_safe("Estableciendo conexión con el blob service...")
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # Extraer nombre del contenedor de la URL
            container_name = self.container_url.rsplit('/', maxsplit=1)[-1]
            
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=self.blob_name
            )
            
            self.log_thread_safe(f"Descargando {self.blob_name}...")
            blob_data = blob_client.download_blob().readall()
            
            # Guardar en caché
            self.log_thread_safe("Guardando archivo en caché...")
            with open(self.cache_file_principal, 'wb') as f:
                f.write(blob_data)
            
            # Convertir a DataFrame
            csv_string = blob_data.decode('utf-8')
            df = pd.read_csv(StringIO(csv_string))
            
            # Actualizar estado del caché
            self.verificar_cache_status()
            
            self.log_thread_safe(f"CSV descargado y guardado en caché. Filas: {len(df)}, Columnas: {len(df.columns)}")
            return df
            
        except Exception as e:
            self.log_thread_safe(f"Error al descargar CSV: {e}")
            return None
    
    def descargar_csv_materialidad(self):
        """Descarga el CSV de materialidad desde Azure Blob Storage o lo carga desde caché"""
        try:
            # Verificar si existe en caché
            if os.path.exists(self.cache_file_materialidad):
                self.log_thread_safe("Archivo de materialidad encontrado en caché, cargando...")
                
                # Mostrar información del caché
                size_mb = os.path.getsize(self.cache_file_materialidad) / (1024 * 1024)
                mod_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file_materialidad))
                self.log_thread_safe(f"Archivo en caché: {size_mb:.1f}MB - Última modificación: {mod_time.strftime('%d/%m/%Y %H:%M')}")
                
                # Cargar desde caché
                df_materialidad = pd.read_csv(self.cache_file_materialidad, sep=';')
                self.log_thread_safe(f"CSV materialidad cargado desde caché. Filas: {len(df_materialidad)}, Columnas: {len(df_materialidad.columns)}")
                return df_materialidad
            
            # No existe en caché, descargar desde Azure
            self.log_thread_safe("Archivo de materialidad no encontrado en caché, descargando desde Azure Blob Storage...")
            
            connection_string = self.obtener_connection_string()
            if not connection_string:
                raise Exception("No se pudo obtener la cadena de conexión")
            
            self.log_thread_safe("Estableciendo conexión para CSV de materialidad...")
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            
            # Usar el mismo contenedor datascience pero con la ruta completa como blob
            container_name = self.container_url.rsplit('/', maxsplit=1)[-1]
            self.log_thread_safe(f"Usando contenedor: {container_name}")
            self.log_thread_safe(f"Ruta del blob: {self.blob_materialidad}")
            
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=self.blob_materialidad
            )
            
            self.log_thread_safe(f"Descargando {self.blob_materialidad}...")
            blob_data = blob_client.download_blob().readall()
            
            # Guardar en caché
            self.log_thread_safe("Guardando archivo de materialidad en caché...")
            with open(self.cache_file_materialidad, 'wb') as f:
                f.write(blob_data)
            
            # Convertir a DataFrame - el archivo usa separador ; (punto y coma)
            csv_string = blob_data.decode('utf-8')
            df_materialidad = pd.read_csv(StringIO(csv_string), sep=';')
            
            # Actualizar estado del caché
            self.verificar_cache_status()
            
            self.log_thread_safe(f"CSV materialidad descargado y guardado en caché. Filas: {len(df_materialidad)}, Columnas: {len(df_materialidad.columns)}")
            self.log_thread_safe(f"Columnas en materialidad: {list(df_materialidad.columns)}")
            
            return df_materialidad
            
        except Exception as e:
            self.log_thread_safe(f"Error al descargar CSV de materialidad: {e}")
            return None
    
    def obtener_nombres_carpetas(self, ubicacion):
        """Obtiene los nombres de las carpetas en la ubicación especificada"""
        try:
            carpetas = []
            path = Path(ubicacion)
            
            if not path.exists():
                raise Exception(f"La ubicación {ubicacion} no existe")
            
            self.log_thread_safe(f"Escaneando directorio: {ubicacion}")
            
            for item in path.iterdir():
                if item.is_dir():
                    carpetas.append(item.name)
            
            self.log_thread_safe(f"Se encontraron {len(carpetas)} carpetas: {', '.join(carpetas[:5])}{'...' if len(carpetas) > 5 else ''}")
            return carpetas
            
        except Exception as e:
            self.log_thread_safe(f"Error al obtener carpetas: {e}")
            return []
    
    def diagnosticar_datos(self, df, nombres_carpetas):
        """Diagnóstica los datos para encontrar problemas de coincidencias"""
        self.log_thread_safe("=== INICIANDO DIAGNÓSTICO ===")
        
        # Identificar el tipo de fuente de datos
        fuente = self.fuente_datos.get()
        self.log_thread_safe(f"Fuente de datos: {fuente}")
        
        # Verificar columnas del CSV
        self.log_thread_safe(f"Columnas en el archivo: {list(df.columns)}")
        
        # Información específica según la fuente
        if fuente == "archivo_local":
            if 'upc_ripley' in df.columns:
                self.log_thread_safe("✓ Columna 'upc_ripley' encontrada en archivo local")
                primeros_upc = df['upc_ripley'].dropna().head(10).tolist()
                self.log_thread_safe(f"Primeros 10 UPC Ripley: {primeros_upc}")
            else:
                self.log_thread_safe("❌ ERROR: La columna 'upc_ripley' no existe en el archivo local")
            
            if 'talla' in df.columns:
                self.log_thread_safe("✓ Columna 'talla' encontrada en archivo local")
                tallas_ejemplo = df['talla'].dropna().head(10).tolist()
                self.log_thread_safe(f"Primeras 10 tallas: {tallas_ejemplo}")
            else:
                self.log_thread_safe("⚠️ Columna 'talla' no encontrada en archivo local")
        
        # Verificar si existe la columna sku_hijo_largo (debe existir siempre después del mapeo)
        if 'sku_hijo_largo' not in df.columns:
            self.log_thread_safe("❌ ERROR: La columna 'sku_hijo_largo' no existe después del mapeo")
            self.log_thread_safe(f"Columnas disponibles: {', '.join(df.columns)}")
            return
        
        # Mostrar información básica del archivo
        self.log_thread_safe(f"Total de filas en archivo: {len(df)}")
        self.log_thread_safe(f"Valores únicos en sku_hijo_largo: {df['sku_hijo_largo'].nunique()}")
        
        # Mostrar primeros valores de sku_hijo_largo
        primeros_skus = df['sku_hijo_largo'].dropna().head(10).tolist()
        self.log_thread_safe(f"Primeros 10 valores sku_hijo_largo (mapeados): {primeros_skus}")
        
        # Mostrar nombres de carpetas
        self.log_thread_safe(f"Total de carpetas encontradas: {len(nombres_carpetas)}")
        self.log_thread_safe(f"Primeras 10 carpetas: {nombres_carpetas[:10]}")
        
        # Buscar coincidencias exactas (sensible a mayúsculas/minúsculas)
        coincidencias_exactas = df[df['sku_hijo_largo'].isin(nombres_carpetas)]
        self.log_thread_safe(f"Coincidencias exactas (case-sensitive): {len(coincidencias_exactas)}")
        
        if len(coincidencias_exactas) == 0:
            self.log_thread_safe("❌ No se encontraron coincidencias exactas")
            
            # Buscar coincidencias ignorando mayúsculas/minúsculas
            df_lower = df.copy()
            df_lower['sku_hijo_largo_lower'] = df_lower['sku_hijo_largo'].astype(str).str.lower()
            nombres_lower = [str(nombre).lower() for nombre in nombres_carpetas]
            
            coincidencias_case_insensitive = df_lower[df_lower['sku_hijo_largo_lower'].isin(nombres_lower)]
            self.log_thread_safe(f"Coincidencias ignorando mayús/minús: {len(coincidencias_case_insensitive)}")
            
            if len(coincidencias_case_insensitive) > 0:
                self.log_thread_safe("✅ Encontradas coincidencias ignorando case!")
                for _, row in coincidencias_case_insensitive.head(5).iterrows():
                    self.log_thread_safe(f"  - CSV: '{row['sku_hijo_largo']}' vs Carpeta: {[n for n in nombres_carpetas if str(n).lower() == str(row['sku_hijo_largo']).lower()]}")
            
            # Buscar coincidencias parciales
            self.log_thread_safe("Buscando coincidencias parciales...")
            for carpeta in nombres_carpetas[:5]:  # Solo las primeras 5 para no saturar
                parciales = df[df['sku_hijo_largo'].astype(str).str.contains(str(carpeta), case=False, na=False)]
                if len(parciales) > 0:
                    self.log_thread_safe(f"  - Carpeta '{carpeta}' tiene {len(parciales)} coincidencias parciales")
                    ejemplos = parciales['sku_hijo_largo'].head(3).tolist()
                    self.log_thread_safe(f"    Ejemplos: {ejemplos}")
        else:
            self.log_thread_safe("✅ Coincidencias exactas encontradas!")
            for _, row in coincidencias_exactas.head(5).iterrows():
                self.log_thread_safe(f"  - Coincidencia: '{row['sku_hijo_largo']}'")
        
        # Verificar tipos de datos
        self.log_thread_safe(f"Tipo de datos en sku_hijo_largo: {df['sku_hijo_largo'].dtype}")
        self.log_thread_safe(f"Valores nulos en sku_hijo_largo: {df['sku_hijo_largo'].isnull().sum()}")
        
        # Verificar columnas necesarias para coincidencias relacionadas
        if 'sku_padre_largo' in df.columns:
            self.log_thread_safe(f"Columna sku_padre_largo - Valores únicos: {df['sku_padre_largo'].nunique()}, Nulos: {df['sku_padre_largo'].isnull().sum()}")
            ejemplos_padre = df['sku_padre_largo'].dropna().head(5).tolist()
            self.log_thread_safe(f"Ejemplos sku_padre_largo: {ejemplos_padre}")
        else:
            self.log_thread_safe("❌ COLUMNA 'sku_padre_largo' NO ENCONTRADA")
        
        if 'color' in df.columns:
            self.log_thread_safe(f"Columna color - Valores únicos: {df['color'].nunique()}, Nulos: {df['color'].isnull().sum()}")
            ejemplos_color = df['color'].dropna().head(5).tolist()
            self.log_thread_safe(f"Ejemplos color: {ejemplos_color}")
        else:
            self.log_thread_safe("❌ COLUMNA 'color' NO ENCONTRADA")
        
        # Verificar si hay registros con coincidencias exactas y sus sku_padre_largo/color
        if len(coincidencias_exactas) > 0:
            self.log_thread_safe("🔍 Analizando datos de coincidencias exactas para búsqueda relacionada:")
            for _, row in coincidencias_exactas.head(3).iterrows():
                sku_padre = row.get('sku_padre_largo', 'N/A')
                color = row.get('color', 'N/A')
                self.log_thread_safe(f"  - SKU: {row['sku_hijo_largo']} → Padre: '{sku_padre}', Color: '{color}'")
                
                if sku_padre != 'N/A' and color != 'N/A':
                    registros_relacionados = df[(df['sku_padre_largo'] == sku_padre) & (df['color'] == color)]
                    self.log_thread_safe(f"    → Encontraría {len(registros_relacionados)} registros relacionados")
        
        self.log_thread_safe("=== FIN DIAGNÓSTICO ===")

    def encontrar_coincidencias(self, df, nombres_carpetas):
        """Encuentra coincidencias exactas y relacionadas"""
        try:
            # Ejecutar diagnóstico primero
            self.diagnosticar_datos(df, nombres_carpetas)
            
            self.log_thread_safe("Buscando coincidencias exactas...")
            
            # CORRECCIÓN: Normalizar datos para manejar tipos int vs string
            df_normalizado = df.copy()
            # Convertir sku_hijo_largo a string y normalizar
            df_normalizado['sku_hijo_largo_norm'] = df_normalizado['sku_hijo_largo'].astype(str).str.strip()
            # Convertir nombres de carpetas a string y normalizar
            nombres_normalizados = [str(nombre).strip() for nombre in nombres_carpetas]
            
            self.log_thread_safe(f"Tipos de datos después de normalización:")
            self.log_thread_safe(f"  - CSV (primeros 5): {df_normalizado['sku_hijo_largo_norm'].head(5).tolist()}")
            self.log_thread_safe(f"  - Carpetas (primeras 5): {nombres_normalizados[:5]}")
            
            # Verificación detallada de los primeros elementos para debugging
            if len(nombres_normalizados) > 0 and len(df_normalizado) > 0:
                self.log_thread_safe("🔍 ANÁLISIS DETALLADO DE COINCIDENCIAS:")
                for carpeta in nombres_normalizados[:3]:  # Solo las primeras 3
                    # Análisis de la carpeta
                    self.log_thread_safe(f"  Analizando carpeta: '{carpeta}' (len: {len(carpeta)}, tipo: {type(carpeta)})")
                    
                    # Buscar coincidencias exactas
                    matches = df_normalizado[df_normalizado['sku_hijo_largo_norm'] == carpeta]
                    self.log_thread_safe(f"    Coincidencias exactas: {len(matches)}")
                    
                    if len(matches) > 0:
                        ejemplos = matches['sku_hijo_largo_norm'].head(2).tolist()
                        self.log_thread_safe(f"    Ejemplos encontrados: {ejemplos}")
                    else:
                        # Si no hay coincidencias exactas, buscar similares
                        similares = df_normalizado[
                            df_normalizado['sku_hijo_largo_norm'].str.contains(carpeta, case=False, na=False, regex=False)
                        ]
                        if len(similares) > 0:
                            self.log_thread_safe(f"    Coincidencias parciales: {len(similares)}")
                            ejemplos_parciales = similares['sku_hijo_largo_norm'].head(3).tolist()
                            self.log_thread_safe(f"    Ejemplos parciales: {ejemplos_parciales}")
                        else:
                            # Mostrar valores más cercanos para debugging
                            csv_values = df_normalizado['sku_hijo_largo_norm'].head(5).tolist()
                            self.log_thread_safe(f"    No encontrado. Primeros valores CSV: {csv_values}")
                            
                            # Análisis carácter por carácter del primer valor
                            if len(csv_values) > 0:
                                first_csv = csv_values[0]
                                self.log_thread_safe(f"    Comparación detallada:")
                                self.log_thread_safe(f"      Carpeta: '{carpeta}' → bytes: {carpeta.encode('utf-8')}")
                                self.log_thread_safe(f"      CSV[0]:  '{first_csv}' → bytes: {first_csv.encode('utf-8')}")
                
                # Verificar si hay coincidencias case-insensitive
                self.log_thread_safe("🔍 VERIFICACIÓN CASE-INSENSITIVE:")
                for carpeta in nombres_normalizados[:3]:
                    case_insensitive_matches = df_normalizado[
                        df_normalizado['sku_hijo_largo_norm'].str.lower() == carpeta.lower()
                    ]
                    if len(case_insensitive_matches) > 0:
                        self.log_thread_safe(f"  Carpeta '{carpeta}' → {len(case_insensitive_matches)} coincidencias case-insensitive")
            
            # Coincidencias exactas con datos normalizados (string vs string)
            coincidencias_exactas = df_normalizado[df_normalizado['sku_hijo_largo_norm'].isin(nombres_normalizados)].copy()
            # Eliminar la columna auxiliar
            if 'sku_hijo_largo_norm' in coincidencias_exactas.columns:
                coincidencias_exactas = coincidencias_exactas.drop('sku_hijo_largo_norm', axis=1)
            
            self.log_thread_safe(f"Coincidencias exactas encontradas (normalizadas): {len(coincidencias_exactas)}")
            
            if coincidencias_exactas.empty:
                self.log_thread_safe("❌ No se encontraron coincidencias después de normalización")
                return coincidencias_exactas, pd.DataFrame()
            
            self.log_thread_safe("Buscando registros relacionados por sku_padre_largo y color...")
            # Para cada coincidencia exacta, encontrar TODOS los registros relacionados
            coincidencias_relacionadas = []
            
            # Obtener las combinaciones únicas de sku_padre_largo de las coincidencias exactas
            padres_exactos = coincidencias_exactas['sku_padre_largo'].unique()
            
            contador = 1
            for sku_padre in padres_exactos:
                self.log_thread_safe(f"Procesando sku_padre {contador}/{len(padres_exactos)}: '{sku_padre}'")
                
                # Buscar TODAS las filas con el mismo sku_padre_largo en el DataFrame original
                # Esto incluye registros que terminan en P aunque no tengan coincidencia exacta
                # y maneja correctamente valores nulos/vacíos en color
                relacionadas = df[df['sku_padre_largo'] == sku_padre].copy()
                
                self.log_thread_safe(f"  - Encontrados {len(relacionadas)} registros relacionados por sku_padre_largo")
                
                # Mostrar información detallada sobre los colores encontrados
                colores_encontrados = relacionadas['color'].value_counts(dropna=False)
                self.log_thread_safe(f"  - Colores en los registros: {dict(colores_encontrados)}")
                
                if len(relacionadas) > 0:
                    coincidencias_relacionadas.append(relacionadas)
                else:
                    self.log_thread_safe(f"  - ⚠️ No se encontraron registros relacionados para sku_padre_largo='{sku_padre}'")
                
                contador += 1
            
            # Combinar todas las coincidencias relacionadas y eliminar duplicados
            if coincidencias_relacionadas:
                self.log_thread_safe(f"Combinando {len(coincidencias_relacionadas)} grupos de registros relacionados...")
                df_relacionadas = pd.concat(coincidencias_relacionadas, ignore_index=True)
                
                filas_antes_dedup = len(df_relacionadas)
                df_relacionadas = df_relacionadas.drop_duplicates()
                filas_despues_dedup = len(df_relacionadas)
                
                self.log_thread_safe(f"Registros antes de deduplicar: {filas_antes_dedup}")
                self.log_thread_safe(f"Registros después de deduplicar: {filas_despues_dedup}")
                self.log_thread_safe(f"Duplicados eliminados: {filas_antes_dedup - filas_despues_dedup}")
            else:
                self.log_thread_safe("❌ No se encontraron registros relacionados para ninguna coincidencia exacta")
                df_relacionadas = pd.DataFrame()
            
            self.log_thread_safe(f"Total de coincidencias relacionadas (incluyendo exactas): {len(df_relacionadas)}")
            
            # Verificar que las coincidencias relacionadas contienen las exactas
            if not coincidencias_exactas.empty and not df_relacionadas.empty:
                exactas_en_relacionadas = len(df_relacionadas[df_relacionadas['sku_hijo_largo'].isin(coincidencias_exactas['sku_hijo_largo'])])
                self.log_thread_safe(f"Verificación: {exactas_en_relacionadas}/{len(coincidencias_exactas)} coincidencias exactas están incluidas en relacionadas")
            
            # Si no hay coincidencias relacionadas pero sí exactas, usar las exactas como relacionadas
            if df_relacionadas.empty and not coincidencias_exactas.empty:
                self.log_thread_safe("⚠️ Usando coincidencias exactas como relacionadas (fallback)")
                df_relacionadas = coincidencias_exactas.copy()
            
            return coincidencias_exactas, df_relacionadas
            
        except Exception as e:
            self.log_thread_safe(f"Error al encontrar coincidencias: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def enriquecer_con_materialidad(self, df_relacionadas, df_exactas, df_materialidad):
        """Enriquece los DataFrames con datos de materialidad usando JOIN entre sku_padre_corto y COD_PADRE"""
        try:
            self.log_thread_safe("=== INICIANDO ENRIQUECIMIENTO CON MATERIALIDAD ===")
            
            if df_materialidad is None or df_materialidad.empty:
                self.log_thread_safe("❌ CSV de materialidad no disponible")
                return df_relacionadas, df_exactas
            
            # Verificar que las columnas necesarias existan
            if 'COD_PADRE' not in df_materialidad.columns:
                self.log_thread_safe("❌ ERROR: Columna 'COD_PADRE' no encontrada en materialidad")
                self.log_thread_safe(f"Columnas disponibles: {list(df_materialidad.columns)}")
                return df_relacionadas, df_exactas
            
            if 'COMPROMISO_R' not in df_materialidad.columns:
                self.log_thread_safe("❌ ERROR: Columna 'COMPROMISO_R' no encontrada en materialidad")
                self.log_thread_safe(f"Columnas disponibles: {list(df_materialidad.columns)}")
                return df_relacionadas, df_exactas
            
            # Verificar que sku_padre_corto exista en los DataFrames principales
            for nombre, df in [("relacionadas", df_relacionadas), ("exactas", df_exactas)]:
                if not df.empty and 'sku_padre_corto' not in df.columns:
                    self.log_thread_safe(f"❌ ERROR: Columna 'sku_padre_corto' no encontrada en {nombre}")
                    self.log_thread_safe(f"Columnas disponibles en {nombre}: {list(df.columns)}")
                    return df_relacionadas, df_exactas
            
            # Normalizar tipos de datos para el JOIN
            df_materialidad_norm = df_materialidad.copy()
            df_materialidad_norm['COD_PADRE_norm'] = df_materialidad_norm['COD_PADRE'].astype(str).str.strip()
            
            self.log_thread_safe(f"Datos de materialidad (antes de deduplicar):")
            self.log_thread_safe(f"  - Total filas: {len(df_materialidad)}")
            self.log_thread_safe(f"  - COD_PADRE únicos: {df_materialidad['COD_PADRE'].nunique()}")
            self.log_thread_safe(f"  - COMPROMISO_R únicos: {df_materialidad['COMPROMISO_R'].nunique()}")
            self.log_thread_safe(f"  - Primeros COD_PADRE: {df_materialidad['COD_PADRE'].head(5).tolist()}")
            self.log_thread_safe(f"  - Tipo de COD_PADRE: {df_materialidad['COD_PADRE'].dtype}")
            
            # CORRECCIÓN: Deduplicar materialidad por COD_PADRE para evitar duplicados en el JOIN
            # Si hay múltiples COMPROMISO_R para el mismo COD_PADRE, tomar el primero (first)
            df_materialidad_dedup = df_materialidad_norm.drop_duplicates(subset=['COD_PADRE_norm'], keep='first')
            
            self.log_thread_safe(f"Datos de materialidad (después de deduplicar):")
            self.log_thread_safe(f"  - Total filas: {len(df_materialidad_dedup)}")
            self.log_thread_safe(f"  - COD_PADRE únicos: {df_materialidad_dedup['COD_PADRE_norm'].nunique()}")
            
            # Verificar si hubo duplicados eliminados
            duplicados_eliminados = len(df_materialidad_norm) - len(df_materialidad_dedup)
            if duplicados_eliminados > 0:
                self.log_thread_safe(f"  ⚠️ Se eliminaron {duplicados_eliminados} duplicados por COD_PADRE")
            
            # Función para enriquecer un DataFrame específico
            def enriquecer_dataframe(df, nombre_df):
                if df.empty:
                    self.log_thread_safe(f"⚠️ DataFrame {nombre_df} está vacío, saltando...")
                    return df
                
                self.log_thread_safe(f"Enriqueciendo DataFrame {nombre_df}...")
                
                # Normalizar sku_padre_corto eliminando nulos y convirtiendo a entero
                df_temp = df.copy()
                
                # Filtrar valores nulos y convertir a entero
                df_temp_clean = df_temp.dropna(subset=['sku_padre_corto']).copy()
                df_temp_clean['sku_padre_corto_norm'] = df_temp_clean['sku_padre_corto'].astype(float).astype(int).astype(str).str.strip()
                
                self.log_thread_safe(f"  - Filas antes del JOIN: {len(df_temp)}")
                self.log_thread_safe(f"  - Filas después de limpiar nulos: {len(df_temp_clean)}")
                self.log_thread_safe(f"  - sku_padre_corto únicos: {df_temp_clean['sku_padre_corto'].nunique()}")
                self.log_thread_safe(f"  - Primeros sku_padre_corto (limpios): {df_temp_clean['sku_padre_corto'].head(5).tolist()}")
                self.log_thread_safe(f"  - Primeros sku_padre_corto_norm: {df_temp_clean['sku_padre_corto_norm'].head(5).tolist()}")
                
                # Encontrar coincidencias manuales
                valores_sku = set(df_temp_clean['sku_padre_corto_norm'].unique())
                valores_cod = set(df_materialidad_dedup['COD_PADRE_norm'].unique())
                coincidencias_encontradas = valores_sku.intersection(valores_cod)
                self.log_thread_safe(f"  - Coincidencias manuales encontradas: {len(coincidencias_encontradas)}")
                if len(coincidencias_encontradas) > 0:
                    self.log_thread_safe(f"  - Primeras coincidencias: {list(coincidencias_encontradas)[:5]}")
                
                # Realizar LEFT JOIN solo con registros limpios usando materialidad deduplicada
                df_enriquecido = df_temp_clean.merge(
                    df_materialidad_dedup[['COD_PADRE_norm', 'COMPROMISO_R']],
                    left_on='sku_padre_corto_norm',
                    right_on='COD_PADRE_norm',
                    how='left'
                )
                
                # Agregar registros que no tenían sku_padre_corto válido (con COMPROMISO_R = NaN)
                registros_nulos = df_temp[df_temp['sku_padre_corto'].isna()].copy()
                if len(registros_nulos) > 0:
                    registros_nulos['COMPROMISO_R'] = None
                    df_enriquecido = pd.concat([df_enriquecido, registros_nulos], ignore_index=True)
                
                # Limpiar columnas auxiliares
                columnas_a_eliminar = ['sku_padre_corto_norm', 'COD_PADRE_norm']
                for col in columnas_a_eliminar:
                    if col in df_enriquecido.columns:
                        df_enriquecido = df_enriquecido.drop(col, axis=1)
                
                # VERIFICACIÓN: Asegurar que no hay duplicados no deseados
                filas_originales = len(df_temp)
                filas_resultado = len(df_enriquecido)
                if filas_resultado != filas_originales:
                    self.log_thread_safe(f"  ⚠️ ADVERTENCIA: El JOIN cambió el número de filas de {filas_originales} a {filas_resultado}")
                
                # Verificar duplicados por sku_hijo_largo si existe esa columna
                if 'sku_hijo_largo' in df_enriquecido.columns:
                    skus_unicos_original = df_temp['sku_hijo_largo'].nunique() if 'sku_hijo_largo' in df_temp.columns else 0
                    skus_unicos_resultado = df_enriquecido['sku_hijo_largo'].nunique()
                    if skus_unicos_original > 0 and skus_unicos_resultado != skus_unicos_original:
                        self.log_thread_safe(f"  ⚠️ ADVERTENCIA: sku_hijo_largo únicos cambió de {skus_unicos_original} a {skus_unicos_resultado}")
                
                # Estadísticas del JOIN
                filas_con_compromiso = df_enriquecido['COMPROMISO_R'].notna().sum()
                filas_sin_compromiso = df_enriquecido['COMPROMISO_R'].isna().sum()
                
                self.log_thread_safe(f"  - Filas después del JOIN: {len(df_enriquecido)}")
                self.log_thread_safe(f"  - Filas con COMPROMISO_R: {filas_con_compromiso}")
                self.log_thread_safe(f"  - Filas sin COMPROMISO_R: {filas_sin_compromiso}")
                
                if filas_con_compromiso > 0:
                    valores_compromiso = df_enriquecido['COMPROMISO_R'].dropna().unique()
                    self.log_thread_safe(f"  - Valores únicos de COMPROMISO_R: {list(valores_compromiso)}")
                
                return df_enriquecido
            
            # Enriquecer ambos DataFrames
            df_relacionadas_enriquecido = enriquecer_dataframe(df_relacionadas, "relacionadas")
            df_exactas_enriquecido = enriquecer_dataframe(df_exactas, "exactas")
            
            self.log_thread_safe("✅ Enriquecimiento con materialidad completado")
            
            return df_relacionadas_enriquecido, df_exactas_enriquecido
            
        except Exception as e:
            self.log_thread_safe(f"Error al enriquecer con materialidad: {e}")
            return df_relacionadas, df_exactas
    
    def generar_excel(self, df_relacionadas, df_exactas):
        """Genera el archivo Excel con dos hojas"""
        try:
            # Crear nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"reporte_coincidencias_{timestamp}.xlsx"
            
            # Obtener la ruta completa usando la ubicación de las carpetas analizadas
            ubicacion_carpetas = self.ubicacion_carpetas.get()
            ruta_completa = os.path.join(ubicacion_carpetas, nombre_archivo)
            
            self.log_thread_safe(f"Creando archivo Excel en: {ruta_completa}")
            
            # Definir las columnas que queremos incluir en el reporte
            columnas_reporte = ['sku_padre_largo', 'sku_hijo_largo', 'sku_descripcion', 'depto', 'color', 'marca', 'COMPROMISO_R']
            
            # Añadir columnas específicas para archivo local
            if self.fuente_datos.get() == "archivo_local":
                # Añadir 'upc_ripley' si está disponible
                if not df_exactas.empty and 'upc_ripley' in df_exactas.columns:
                    columnas_reporte.append('upc_ripley')
                elif not df_relacionadas.empty and 'upc_ripley' in df_relacionadas.columns:
                    columnas_reporte.append('upc_ripley')
                
                # Verificar si la columna 'talla' existe en cualquiera de los DataFrames
                tiene_talla = False
                if not df_exactas.empty and 'talla' in df_exactas.columns:
                    tiene_talla = True
                elif not df_relacionadas.empty and 'talla' in df_relacionadas.columns:
                    tiene_talla = True
                
                if tiene_talla:
                    columnas_reporte.append('talla')
                    self.log_thread_safe("✓ Incluidas columnas 'upc_ripley' y 'talla' en el reporte")
            
            # Filtrar columnas para ambos DataFrames
            def filtrar_columnas(df, nombre_df):
                if df.empty:
                    return df
                
                # Verificar qué columnas existen en el DataFrame
                columnas_disponibles = [col for col in columnas_reporte if col in df.columns]
                columnas_faltantes = [col for col in columnas_reporte if col not in df.columns]
                
                self.log_thread_safe(f"Filtrando columnas para {nombre_df}:")
                self.log_thread_safe(f"  - Columnas disponibles: {columnas_disponibles}")
                if columnas_faltantes:
                    self.log_thread_safe(f"  - Columnas faltantes: {columnas_faltantes}")
                
                # Retornar DataFrame con solo las columnas disponibles del reporte
                return df[columnas_disponibles].copy()
            
            # Aplicar filtro de columnas
            df_relacionadas_filtrado = filtrar_columnas(df_relacionadas, "Relacionadas")
            df_exactas_filtrado = filtrar_columnas(df_exactas, "Exactas")
            
            # Crear archivo Excel
            with pd.ExcelWriter(ruta_completa, engine='openpyxl') as writer:
                # Hoja 1: Coincidencias relacionadas (exactas + mismo sku_padre_largo y color)
                self.log_thread_safe("Escribiendo hoja 'Coincidencias Relacionadas'...")
                df_relacionadas_filtrado.to_excel(writer, sheet_name='Coincidencias Relacionadas', index=False)
                
                # Hoja 2: Solo coincidencias exactas
                self.log_thread_safe("Escribiendo hoja 'Coincidencias Exactas'...")
                df_exactas_filtrado.to_excel(writer, sheet_name='Coincidencias Exactas', index=False)
            
            self.log_thread_safe(f"Archivo Excel generado exitosamente: {ruta_completa}")
            self.log_thread_safe(f"- Hoja 1 (Relacionadas): {len(df_relacionadas_filtrado)} filas, {len(df_relacionadas_filtrado.columns)} columnas")
            self.log_thread_safe(f"- Hoja 2 (Exactas): {len(df_exactas_filtrado)} filas, {len(df_exactas_filtrado.columns)} columnas")
            self.log_thread_safe(f"- Columnas incluidas: {list(df_relacionadas_filtrado.columns)}")
            
            # Mostrar información sobre la columna COMPROMISO_R
            if 'COMPROMISO_R' in df_relacionadas_filtrado.columns:
                filas_con_compromiso = df_relacionadas_filtrado['COMPROMISO_R'].notna().sum()
                self.log_thread_safe(f"- Registros con COMPROMISO_R: {filas_con_compromiso}")
                if filas_con_compromiso > 0:
                    valores_unicos = df_relacionadas_filtrado['COMPROMISO_R'].dropna().nunique()
                    self.log_thread_safe(f"- Valores únicos de COMPROMISO_R: {valores_unicos}")
            
            # Mostrar mensaje de éxito
            mensaje_exito = f"Reporte generado exitosamente:\n{ruta_completa}\n\n"
            mensaje_exito += f"Hoja 1: {len(df_relacionadas_filtrado)} registros relacionados\n"
            mensaje_exito += f"Hoja 2: {len(df_exactas_filtrado)} registros exactos\n"
            mensaje_exito += f"Columnas: {len(df_relacionadas_filtrado.columns)}\n\n"
            
            if 'COMPROMISO_R' in df_relacionadas_filtrado.columns:
                filas_con_compromiso = df_relacionadas_filtrado['COMPROMISO_R'].notna().sum()
                mensaje_exito += f"✅ Enriquecimiento aplicado:\n{filas_con_compromiso} registros con COMPROMISO_R"
            else:
                mensaje_exito += "ℹ️ Sin enriquecimiento:\nSolo datos básicos incluidos"
            
            messagebox.showinfo("Éxito", mensaje_exito)
            
            # Ejecutar agrupamiento por departamento si está habilitado
            if self.agrupar_por_depto.get():
                self.log_thread_safe("Iniciando agrupamiento por departamento...")
                self.agrupar_carpetas_por_departamento(ruta_completa)
            
        except Exception as e:
            self.log_thread_safe(f"Error al generar Excel: {e}")
            messagebox.showerror("Error", f"Error al generar el archivo Excel: {e}")
    
    def agrupar_carpetas_por_departamento(self, ruta_excel):
        """Agrupa las carpetas por departamento basándose en los datos del Excel generado"""
        try:
            self.log_thread_safe("=== INICIANDO AGRUPAMIENTO POR DEPARTAMENTO ===")
            
            # Leer el archivo Excel generado
            self.log_thread_safe(f"Leyendo archivo Excel: {ruta_excel}")
            df_exactas = pd.read_excel(ruta_excel, sheet_name='Coincidencias Exactas')
            
            # Verificar que existan las columnas necesarias
            if 'sku_hijo_largo' not in df_exactas.columns:
                self.log_thread_safe("❌ ERROR: Columna 'sku_hijo_largo' no encontrada en el Excel")
                return
            
            if 'depto' not in df_exactas.columns:
                self.log_thread_safe("❌ ERROR: Columna 'depto' no encontrada en el Excel")
                return
            
            self.log_thread_safe(f"Datos leídos: {len(df_exactas)} registros")
            
            # Agrupar por departamento
            agrupamiento = df_exactas.groupby('depto')['sku_hijo_largo'].apply(list).to_dict()
            
            self.log_thread_safe(f"Departamentos encontrados: {len(agrupamiento)}")
            for depto, skus in agrupamiento.items():
                self.log_thread_safe(f"  - {depto}: {len(skus)} SKUs")
            
            # Obtener ruta base donde están las carpetas
            ubicacion_carpetas = self.ubicacion_carpetas.get()
            if not ubicacion_carpetas:
                self.log_thread_safe("❌ ERROR: No se ha seleccionado ubicación de carpetas")
                return
            
            # Crear carpetas de departamento y mover carpetas correspondientes
            carpetas_movidas = 0
            carpetas_no_encontradas = []
            
            for depto, skus in agrupamiento.items():
                # Crear nombre de carpeta departamento con formato "DXXX (N SKU)"
                nombre_carpeta_depto = f"{depto} ({len(skus)} SKU)"
                ruta_carpeta_depto = os.path.join(ubicacion_carpetas, nombre_carpeta_depto)
                
                self.log_thread_safe(f"Procesando departamento {depto} con {len(skus)} SKUs...")
                
                # Crear carpeta de departamento si no existe
                if not os.path.exists(ruta_carpeta_depto):
                    os.makedirs(ruta_carpeta_depto)
                    self.log_thread_safe(f"  ✅ Carpeta creada: {nombre_carpeta_depto}")
                else:
                    self.log_thread_safe(f"  ℹ️ Carpeta ya existe: {nombre_carpeta_depto}")
                
                # Mover cada carpeta SKU al departamento correspondiente
                for sku in skus:
                    sku_str = str(sku)
                    ruta_carpeta_sku = os.path.join(ubicacion_carpetas, sku_str)
                    ruta_destino = os.path.join(ruta_carpeta_depto, sku_str)
                    
                    if os.path.exists(ruta_carpeta_sku) and os.path.isdir(ruta_carpeta_sku):
                        # Verificar si ya existe en el destino
                        if os.path.exists(ruta_destino):
                            self.log_thread_safe(f"    ⚠️ Carpeta {sku_str} ya existe en {depto}, saltando...")
                        else:
                            try:
                                shutil.move(ruta_carpeta_sku, ruta_destino)
                                carpetas_movidas += 1
                                self.log_thread_safe(f"    ✅ Movida: {sku_str} → {nombre_carpeta_depto}")
                            except Exception as e:
                                self.log_thread_safe(f"    ❌ Error moviendo {sku_str}: {e}")
                    else:
                        carpetas_no_encontradas.append(sku_str)
                        self.log_thread_safe(f"    ⚠️ Carpeta no encontrada: {sku_str}")
            
            # Resumen del agrupamiento
            self.log_thread_safe("=== RESUMEN DEL AGRUPAMIENTO ===")
            self.log_thread_safe(f"✅ Carpetas movidas exitosamente: {carpetas_movidas}")
            self.log_thread_safe(f"⚠️ Carpetas no encontradas: {len(carpetas_no_encontradas)}")
            
            if carpetas_no_encontradas:
                self.log_thread_safe("Carpetas no encontradas:")
                for carpeta in carpetas_no_encontradas[:10]:  # Mostrar solo las primeras 10
                    self.log_thread_safe(f"  - {carpeta}")
                if len(carpetas_no_encontradas) > 10:
                    self.log_thread_safe(f"  ... y {len(carpetas_no_encontradas) - 10} más")
            
            # Mostrar mensaje de éxito
            mensaje_agrupamiento = f"Agrupamiento completado:\n\n"
            mensaje_agrupamiento += f"📁 Departamentos creados: {len(agrupamiento)}\n"
            mensaje_agrupamiento += f"✅ Carpetas movidas: {carpetas_movidas}\n"
            mensaje_agrupamiento += f"⚠️ Carpetas no encontradas: {len(carpetas_no_encontradas)}\n\n"
            mensaje_agrupamiento += f"Las carpetas han sido organizadas por departamento en:\n{ubicacion_carpetas}"
            
            messagebox.showinfo("Agrupamiento Completado", mensaje_agrupamiento)
            
        except Exception as e:
            self.log_thread_safe(f"Error en agrupamiento por departamento: {e}")
            messagebox.showerror("Error", f"Error durante el agrupamiento: {e}")
    
    def verificar_cache_status(self):
        """Verifica el estado del caché y actualiza la UI"""
        try:
            cache_info = []

            # Verificar CSV principal
            if os.path.exists(self.cache_file_principal):
                size_mb = os.path.getsize(self.cache_file_principal) / (1024 * 1024)
                mod_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file_principal))
                cache_info.append(f"Principal ({size_mb:.1f}MB - {mod_time.strftime('%d/%m %H:%M')})")

            # Verificar CSV materialidad
            if os.path.exists(self.cache_file_materialidad):
                size_mb = os.path.getsize(self.cache_file_materialidad) / (1024 * 1024)
                mod_time = datetime.fromtimestamp(os.path.getmtime(self.cache_file_materialidad))
                cache_info.append(f"Materialidad ({size_mb:.1f}MB - {mod_time.strftime('%d/%m %H:%M')})")

            if cache_info:
                status_text = f"Caché disponible: {', '.join(cache_info)}"
                self.cache_status.set(status_text)
            else:
                self.cache_status.set("Sin caché")

        except Exception as e:
            self.cache_status.set(f"Error verificando caché: {e}")
    
    
    def on_planilla_change(self):
        """Maneja cambios en los checkboxes de planillas"""
        # Mostrar/ocultar campos según selección
        mostrar_campos = self.generar_moda.get() or self.generar_producto.get()
        self.toggle_campos_visibility(mostrar_campos)
        
        # Mostrar/ocultar campo MODELO según tipo de planilla
        mostrar_modelo = self.generar_moda.get()
        self.toggle_modelo_visibility(mostrar_modelo)
        
        # Controlar visibilidad del campo MEDIDAS
        self.update_medidas_visibility()
        
        # Solo permitir una opción a la vez
        if self.generar_moda.get() and self.generar_producto.get():
            # Si se seleccionó MODA, desactivar PRODUCTO
            if self.generar_moda.get():
                self.generar_producto.set(False)
            else:
                self.generar_moda.set(False)
    
    def on_template_email_change(self):
        """Maneja cambios en el checkbox de template de email"""
        # Controlar visibilidad del campo MEDIDAS
        self.update_medidas_visibility()
    
    def update_medidas_visibility(self):
        """Actualiza la visibilidad del campo MEDIDAS"""
        # Mostrar MEDIDAS cuando se genera planilla MODA (para que se use en el template de email)
        mostrar_medidas = self.generar_moda.get()
        self.toggle_medidas_visibility(mostrar_medidas)
    
    def toggle_campos_visibility(self, mostrar):
        """Muestra u oculta los campos de entrada"""
        if mostrar:
            self.campos_frame.grid()
        else:
            self.campos_frame.grid_remove()
    
    def toggle_modelo_visibility(self, mostrar):
        """Muestra u oculta el campo MODELO"""
        if mostrar:
            self.label_modelo.grid()
            self.entry_modelo.grid()
        else:
            self.label_modelo.grid_remove()
            self.entry_modelo.grid_remove()
    
    def toggle_medidas_visibility(self, mostrar):
        """Muestra u oculta el campo MEDIDAS"""
        if mostrar:
            self.label_medidas.grid()
            self.entry_medidas.grid()
        else:
            self.label_medidas.grid_remove()
            self.entry_medidas.grid_remove()
    
    def validar_campos_planilla(self):
        """Valida que los campos necesarios estén completos"""
        if not (self.generar_moda.get() or self.generar_producto.get()):
            return True  # No se necesita validación si no se generan planillas adicionales
        
        if not self.fecha_planilla.get().strip():
            messagebox.showwarning("Advertencia", "Por favor ingresa una fecha para la planilla")
            return False
        
        if self.generar_moda.get() and not self.modelo_moda.get().strip():
            messagebox.showwarning("Advertencia", "Por favor ingresa un modelo para la planilla MODA")
            return False
        
        return True
    
    def generar_planilla_adicional(self, nombres_carpetas, tipo_planilla):
        """Genera planilla adicional según el tipo especificado"""
        try:
            self.log_thread_safe(f"=== GENERANDO PLANILLA {tipo_planilla.upper()} ===")
            
            if not nombres_carpetas:
                self.log_thread_safe("❌ No hay nombres de carpetas para generar planilla")
                return
            
            # Crear DataFrame base
            df_planilla = pd.DataFrame({
                'SKU_HIJO_LARGO': nombres_carpetas
            })
            
            # Añadir fecha (replicada para todos los registros)
            fecha = self.fecha_planilla.get().strip()
            df_planilla['Fecha'] = fecha
            
            # Añadir modelo si es MODA
            if tipo_planilla.lower() == 'moda':
                modelo = self.modelo_moda.get().strip()
                df_planilla['MODELO'] = modelo
                self.log_thread_safe(f"Planilla MODA: {len(df_planilla)} registros con fecha='{fecha}' y modelo='{modelo}'")
            else:
                self.log_thread_safe(f"Planilla PRODUCTO: {len(df_planilla)} registros con fecha='{fecha}'")
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"planilla_{tipo_planilla.lower()}_{timestamp}.xlsx"
            
            # Obtener ruta completa
            ubicacion_carpetas = self.ubicacion_carpetas.get()
            ruta_completa = os.path.join(ubicacion_carpetas, nombre_archivo)
            
            # Guardar archivo Excel
            self.log_thread_safe(f"Guardando planilla {tipo_planilla} en: {ruta_completa}")
            df_planilla.to_excel(ruta_completa, index=False)
            
            self.log_thread_safe(f"✅ Planilla {tipo_planilla} generada exitosamente")
            self.log_thread_safe(f"- Archivo: {nombre_archivo}")
            self.log_thread_safe(f"- Registros: {len(df_planilla)}")
            self.log_thread_safe(f"- Columnas: {list(df_planilla.columns)}")
            
            return ruta_completa
            
        except Exception as e:
            self.log_thread_safe(f"Error al generar planilla {tipo_planilla}: {e}")
            return None
    
    def on_responsables_change(self):
        """Maneja cambios en el checkbox de responsables"""
        # Ya no es necesario mostrar/ocultar selección de país
        pass
    
    def cargar_datos_responsables(self):
        """Carga los datos de responsables desde CHILE.xlsx"""
        try:
            archivo_path = os.path.join("docs", "CHILE.xlsx")
            
            if not os.path.exists(archivo_path):
                self.log_thread_safe(f"❌ Archivo {archivo_path} no encontrado")
                return None
            
            self.log_thread_safe(f"Cargando datos de responsables desde {archivo_path}")
            df_responsables = pd.read_excel(archivo_path)
            
            # Verificar columnas necesarias
            columnas_requeridas = ['DEPTOS', 'célula', 'redactora', 'diseñadora']
            columnas_faltantes = [col for col in columnas_requeridas if col not in df_responsables.columns]
            
            if columnas_faltantes:
                self.log_thread_safe(f"⚠️ Columnas faltantes en {pais}: {columnas_faltantes}")
                self.log_thread_safe(f"Columnas disponibles: {list(df_responsables.columns)}")
            
            # Limpiar datos - eliminar filas con DEPTOS vacío
            df_responsables = df_responsables.dropna(subset=['DEPTOS'])
            
            self.log_thread_safe(f"Datos de CHILE cargados: {len(df_responsables)} departamentos")
            self.log_thread_safe(f"Departamentos encontrados: {df_responsables['DEPTOS'].nunique()} únicos")

            return df_responsables

        except Exception as e:
            self.log_thread_safe(f"Error al cargar datos de CHILE: {e}")
            return None
    
    def generar_archivo_responsables(self, departamentos_encontrados):
        """Genera archivo con responsables por departamento usando CHILE.xlsx"""
        try:
            self.log_thread_safe("=== GENERANDO ARCHIVO DE RESPONSABLES (CHILE) ===")

            if not departamentos_encontrados:
                self.log_thread_safe("❌ No hay departamentos para procesar")
                return None

            # Cargar datos de responsables
            df_responsables = self.cargar_datos_responsables()
            if df_responsables is None:
                return None
            
            # Crear lista de departamentos únicos encontrados en las coincidencias
            departamentos_unicos = list(set(departamentos_encontrados))
            self.log_thread_safe(f"Departamentos a procesar: {len(departamentos_unicos)}")
            self.log_thread_safe(f"Lista: {departamentos_unicos[:10]}{'...' if len(departamentos_unicos) > 10 else ''}")
            
            # Buscar coincidencias entre departamentos encontrados y archivo de responsables
            resultados = []
            departamentos_sin_responsable = []
            
            for depto in departamentos_unicos:
                # Buscar el departamento en los datos
                coincidencia = df_responsables[df_responsables['DEPTOS'] == depto]
                
                if not coincidencia.empty:
                    # Tomar la primera coincidencia si hay múltiples
                    fila = coincidencia.iloc[0]
                    
                    resultado = {
                        'DEPARTAMENTO': depto,
                        'DIVISION': fila.get('DIVISION', ''),
                        'DESC_DEPTOS': fila.get('DESC DEPTOS', ''),
                        'CELULA': fila.get('célula', ''),
                        'REDACTORA': fila.get('redactora', ''),
                        'DISENADORA': fila.get('diseñadora', '')
                    }
                    resultados.append(resultado)
                    
                    self.log_thread_safe(f"  ✅ {depto}: {fila.get('célula', 'N/A')} - {fila.get('redactora', 'N/A')}")
                else:
                    departamentos_sin_responsable.append(depto)
                    self.log_thread_safe(f"  ⚠️ {depto}: Sin responsable encontrado")
            
            if not resultados:
                self.log_thread_safe("❌ No se encontraron coincidencias con los responsables")
                return None
            
            # Crear DataFrame con los resultados
            df_resultado = pd.DataFrame(resultados)
            
            # Generar nombre de archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"responsables_chile_{timestamp}.xlsx"
            
            # Obtener ruta completa
            ubicacion_carpetas = self.ubicacion_carpetas.get()
            ruta_completa = os.path.join(ubicacion_carpetas, nombre_archivo)
            
            # Guardar archivo Excel
            self.log_thread_safe(f"Guardando archivo de responsables en: {ruta_completa}")
            df_resultado.to_excel(ruta_completa, index=False)
            
            # Resumen
            self.log_thread_safe(f"✅ Archivo de responsables generado exitosamente")
            self.log_thread_safe(f"- Archivo: {nombre_archivo}")
            self.log_thread_safe(f"- Departamentos con responsable: {len(resultados)}")
            self.log_thread_safe(f"- Departamentos sin responsable: {len(departamentos_sin_responsable)}")
            self.log_thread_safe(f"- Columnas: {list(df_resultado.columns)}")
            
            if departamentos_sin_responsable:
                self.log_thread_safe(f"Departamentos sin responsable: {departamentos_sin_responsable[:5]}{'...' if len(departamentos_sin_responsable) > 5 else ''}")
            
            return ruta_completa
            
        except Exception as e:
            self.log_thread_safe(f"Error al generar archivo de responsables: {e}")
            return None
    
    def generar_template_email_metodo(self, df_exactas, df_responsables_resultado=None):
        """Genera un template HTML para email con la información de la carga"""
        try:
            self.log_thread_safe("=== GENERANDO TEMPLATE DE EMAIL ===")
            
            if df_exactas.empty:
                self.log_thread_safe("❌ No hay datos exactos para generar template de email")
                return None
            
            # Obtener información básica
            fecha_actual = datetime.now().strftime("%d_%m_%Y")
            cantidad_sku = len(df_exactas)

            # Crear nombre del archivo/enlace (siempre CHILE)
            nombre_archivo = f"{fecha_actual} ({cantidad_sku} SKU) CHILE"
            
            # Obtener MODELO y MEDIDAS para el template (solo para planillas MODA)
            marc_value = ""
            if self.generar_moda.get() and (self.modelo_moda.get().strip() or self.medidas_modelo.get().strip()):
                modelo_nombre = self.modelo_moda.get().strip() if self.modelo_moda.get().strip() else "MODELO"
                modelo_medidas = self.medidas_modelo.get().strip() if self.medidas_modelo.get().strip() else "1.90 CM"
                marc_value = f"{modelo_nombre}    {modelo_medidas}"
            
            # Crear HTML template
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; font-size: 12px; }}
        table {{ border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #000; padding: 2px 5px; text-align: left; line-height: 1; }}
        th {{ background-color: #f0f0f0; font-weight: bold; }}
        .marc-box {{ border: 2px solid #000; padding: 5px; display: inline-block; margin: 10px 0; }}
        .link {{ color: blue; text-decoration: underline; }}
    </style>
</head>
<body>
    <p>Hola chicos,</p>
    
    <p>Llegó carga:</p>
    
    <p><span class="link">📎 {nombre_archivo}</span></p>
"""
            
            # Tabla de responsables por departamento
            if df_responsables_resultado is not None and not df_responsables_resultado.empty:
                self.log_thread_safe("Agregando tabla de responsables al template")
                html_content += """
    <table>
        <tr>
            <th>DEPTOS</th>
            <th>redactora</th>
            <th>diseñadora</th>
        </tr>
"""
                for _, row in df_responsables_resultado.iterrows():
                    depto = row.get('DEPARTAMENTO', '')
                    redactora = row.get('REDACTORA', '')
                    disenadora = row.get('DISENADORA', '')
                    
                    html_content += f"""        <tr>
            <td>{depto}</td>
            <td>{redactora}</td>
            <td>{disenadora}</td>
        </tr>
"""
                html_content += "    </table>\n"
            else:
                self.log_thread_safe("⚠️ No hay datos de responsables para incluir en el template")
            
            # MODELO Y MEDIDAS (solo si hay información)
            if marc_value:
                html_content += f"""
    <div class="marc-box">
        <strong>{marc_value}</strong>
    </div>
"""
            
            # Tabla de productos
            self.log_thread_safe("Agregando tabla de productos al template")
            html_content += """
    <table>
        <tr>
            <th>ean_hijo</th>
            <th>ean_padre</th>
            <th>sku_descripcion</th>
            <th>cod dpto</th>
            <th>marca</th>
            <th>color</th>
        </tr>
"""
            
            # Agregar todas las filas de productos
            for i, (_, row) in enumerate(df_exactas.iterrows()):
                ean_hijo = row.get('sku_hijo_largo', '')
                ean_padre = row.get('sku_padre_largo', '')
                variacion = row.get('sku_descripcion', '')
                cod_dpto = row.get('depto', '')
                marca = row.get('marca', '')
                color = row.get('color', '')
                
                html_content += f"""        <tr>
            <td>{ean_hijo}</td>
            <td>{ean_padre}</td>
            <td>{variacion}</td>
            <td>{cod_dpto}</td>
            <td>{marca}</td>
            <td>{color}</td>
        </tr>
"""
            
            
            html_content += """    </table>

    <p>Saludos!</p>
</body>
</html>"""
            
            # Guardar archivo HTML
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo_html = f"template_email_{timestamp}.html"
            ubicacion_carpetas = self.ubicacion_carpetas.get()
            ruta_completa = os.path.join(ubicacion_carpetas, nombre_archivo_html)
            
            with open(ruta_completa, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.log_thread_safe(f"✅ Template de email generado: {ruta_completa}")
            self.log_thread_safe(f"- Archivo HTML: {nombre_archivo_html}")
            self.log_thread_safe(f"- SKUs incluidos: {len(df_exactas)}")
            
            if df_responsables_resultado is not None:
                self.log_thread_safe(f"- Responsables incluidos: {len(df_responsables_resultado)}")
            
            return ruta_completa
            
        except Exception as e:
            self.log_thread_safe(f"Error al generar template de email: {e}")
            return None
    
    def run(self):
        """Ejecuta la aplicación"""
        self.root.mainloop()


if __name__ == "__main__":
    app = AppCargas()
    app.run()