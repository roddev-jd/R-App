"""
Aplicación para comparar nombres de carpetas con datos en SharePoint Online
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
import msal
import requests
import getpass
from typing import Optional
import urllib3
import base64

# Deshabilitar advertencias SSL para entornos corporativos
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SharePointAuth:
    """Handles SharePoint authentication using Microsoft Authentication Library (MSAL)."""

    # Azure CLI public client ID
    CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
    AUTHORITY = "https://login.microsoftonline.com/common"
    SCOPES = ["https://graph.microsoft.com/.default"]
    CACHE_DIR_NAME = ".appsuite_cache"

    def __init__(self) -> None:
        """Initialize SharePoint authentication with user-specific token cache."""
        self.cache_filename = self._get_cache_filename()
        self.cache = self._load_token_cache()
        self.app = self._create_msal_app()

    def _get_cache_filename(self) -> Path:
        """Get user-specific cache filename."""
        current_user = getpass.getuser()
        cache_dir = Path.home() / self.CACHE_DIR_NAME
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / f"sharepoint_token_cache_{current_user}.bin"

    def _load_token_cache(self) -> msal.SerializableTokenCache:
        """Load existing token cache or create new one."""
        cache = msal.SerializableTokenCache()
        if self.cache_filename.exists():
            cache.deserialize(self.cache_filename.read_text(encoding='utf-8'))
        return cache

    def _create_msal_app(self) -> msal.PublicClientApplication:
        """Create MSAL public client application."""
        return msal.PublicClientApplication(
            self.CLIENT_ID,
            authority=self.AUTHORITY,
            token_cache=self.cache,
            verify=False
        )

    def _save_cache(self) -> None:
        """Save token cache to disk if it has changed."""
        if self.cache.has_state_changed:
            self.cache_filename.write_text(self.cache.serialize(), encoding='utf-8')

    def get_token(self) -> str:
        """Get access token, trying silent acquisition first, then interactive."""
        # Try silent token acquisition first
        result = self._try_silent_acquisition()

        # Fall back to interactive acquisition if needed
        if not result:
            result = self._try_interactive_acquisition()

        return self._extract_token(result)

    def _try_silent_acquisition(self) -> Optional[dict]:
        """Attempt silent token acquisition using cached accounts."""
        accounts = self.app.get_accounts()
        if not accounts:
            return None

        result = self.app.acquire_token_silent(self.SCOPES, account=accounts[0])
        if result:
            self._save_cache()
        return result

    def _try_interactive_acquisition(self) -> dict:
        """Perform interactive token acquisition."""
        result = self.app.acquire_token_interactive(self.SCOPES)
        self._save_cache()
        return result

    def _extract_token(self, result: dict) -> str:
        """Extract access token from MSAL result."""
        if "access_token" in result:
            return result["access_token"]

        error_msg = result.get("error_description", "No se pudo adquirir un token.")
        raise Exception(error_msg)


class AppCargas:
    """Aplicación principal para comparar carpetas con datos de SharePoint Online"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("APP CARGAS")
        self.root.geometry("750x700")
        
        # Variables
        self.ubicacion_carpetas = tk.StringVar()

        # Configuración SharePoint
        self.sharepoint_url = "https://ripleycorp.sharepoint.com/sites/Equipopyc/Documentos%20compartidos/mantenedor/PROYECTO/ARCHIVOS_PRODUCCI%C3%93N/DATA/formato_ppias.csv"
        
        # Variables para threading y eventos
        self.processing = False
        self.event_queue = queue.Queue()
        self.progress_var = tk.DoubleVar()
        self.progress_text = tk.StringVar(value="Listo")
        
        # Variable para controlar el JOIN con materialidad (ahora deshabilitado para SharePoint)
        self.usar_materialidad = tk.BooleanVar(value=False)
        
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

        # Variable para reporte completo con todas las columnas
        self.generar_reporte_completo = tk.BooleanVar(value=False)

        # Variable para control de caché de SharePoint
        self.forzar_descarga_sharepoint = tk.BooleanVar(value=False)

        # Variable para nombre de columna de departamentos en SharePoint
        self.columna_depto_sharepoint = tk.StringVar(value="COD DPTO")

        # Variables obsoletas eliminadas - ahora solo se usa SharePoint
        
        # Variables para manejo de caché - usar directorio del sistema
        self.cache_dir = Path.home() / SharePointAuth.CACHE_DIR_NAME / "data"
        self.cache_file_principal = self.cache_dir / "formato_ppias.csv"
        self.cache_status = tk.StringVar(value="Sin caché")

        # Crear directorio de caché si no existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Migrar cache existente del directorio local al sistema si existe
        self._migrate_local_cache()
        
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
        
        # Información de fuente de datos
        fuente_frame = ttk.LabelFrame(main_frame, text="Fuente de Datos", padding="5")
        fuente_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 8))

        # Información sobre SharePoint
        info_label = ttk.Label(fuente_frame, text="✓ Conectado a SharePoint Online - Peru Data Script (formato_ppias.csv)")
        info_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # Botón para probar conexión
        self.btn_test_conexion = ttk.Button(fuente_frame, text="Probar Conexión a SharePoint",
                                           command=self.probar_conexion_sharepoint)
        self.btn_test_conexion.grid(row=1, column=0, pady=(0, 5))

        # Botón para descargar datos desde SharePoint
        self.btn_descargar_datos = ttk.Button(fuente_frame, text="Descargar Datos desde SharePoint",
                                             command=self.descargar_datos_sharepoint)
        self.btn_descargar_datos.grid(row=2, column=0, pady=(5, 5))

        # Checkbox para forzar descarga (ignorar caché)
        self.checkbox_forzar_descarga = ttk.Checkbutton(
            fuente_frame,
            text="🔄 Forzar descarga nueva (ignorar caché)",
            variable=self.forzar_descarga_sharepoint,
            command=self.on_forzar_descarga_change
        )
        self.checkbox_forzar_descarga.grid(row=3, column=0, sticky=tk.W, pady=(5, 5))

        # Campo para nombre de columna de departamentos
        depto_config_frame = ttk.Frame(fuente_frame)
        depto_config_frame.grid(row=4, column=0, sticky=tk.W, pady=(5, 5))

        ttk.Label(depto_config_frame, text="Nombre columna departamentos:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.entry_columna_depto = ttk.Entry(depto_config_frame, textvariable=self.columna_depto_sharepoint, width=20)
        self.entry_columna_depto.grid(row=0, column=1, sticky=tk.W)


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
            text="Generar archivo de responsables por departamento (PERU)",
            variable=self.generar_responsables
        )
        self.checkbox_responsables.grid(row=4, column=0, sticky=tk.W, pady=(0, 2))
        
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

        # Checkbox para reporte completo con todas las columnas
        self.checkbox_reporte_completo = ttk.Checkbutton(
            planillas_frame,
            text="Generar INFO_REDACCION con TODAS las columnas de SharePoint",
            variable=self.generar_reporte_completo
        )
        self.checkbox_reporte_completo.grid(row=8, column=0, sticky=tk.W, pady=(0, 2))
        
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
    
# Funciones obsoletas eliminadas - ahora solo se usa SharePoint
    
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

            # Paso 1: Conectar y descargar CSV principal desde SharePoint (15%)
            self.update_status_thread_safe("Descargando CSV principal desde SharePoint...")
            self.update_progress_thread_safe(5)

            df = self.cargar_datos_principal()
            if df is None:
                self.log_thread_safe("❌ Error: No se pudieron cargar los datos principales desde SharePoint")
                self.update_status_thread_safe("Error al cargar datos")
                messagebox.showerror("Error", "No se pudieron cargar los datos desde SharePoint. Verifique la conexión.")
                return

            self.update_progress_thread_safe(15)
            
            # Paso 2: SharePoint no incluye datos de materialidad (25%)
            self.update_status_thread_safe("Fuente: SharePoint - Sin datos de materialidad...")
            df_materialidad = None
            self.log_thread_safe("⚠️ SharePoint: Los datos de materialidad no están disponibles en formato_ppias.csv")

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

                    self.log_thread_safe(f"Generando archivo de responsables para {len(departamentos_encontrados)} departamentos (PERU)")
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
            
            # Paso 9: INFO_REDACCION con Todas las Columnas (96%) - solo si está activado
            if self.generar_reporte_completo.get():
                self.update_status_thread_safe("Generando INFO_REDACCION con todas las columnas...")
                self.generar_reporte_completo_metodo(df_relacionadas_enriquecido, df_exactas_enriquecido, df)

            self.update_progress_thread_safe(96)

            # Paso 10: Template de Email (97%) - solo si está activado
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
    
    # Funciones auxiliares eliminadas - ahora se usan las de la clase SharePointAuth

    def obtener_sharepoint_token(self):
        """Obtiene un token válido para SharePoint usando la clase SharePointAuth"""
        try:
            self.log_thread_safe("=== INICIANDO AUTENTICACIÓN SHAREPOINT ===")

            # Usar la clase SharePointAuth (como en la aplicación funcional)
            if not hasattr(self, '_sharepoint_auth'):
                self._sharepoint_auth = SharePointAuth()

            self.log_thread_safe(f"Ubicación caché: {self._sharepoint_auth.cache_filename}")

            access_token = self._sharepoint_auth.get_token()

            self.log_thread_safe("=== TOKEN SHAREPOINT OBTENIDO EXITOSAMENTE ===")
            return access_token

        except ImportError as e:
            self.log_thread_safe(f"❌ Error: Biblioteca MSAL no instalada: {e}")
            raise Exception("La biblioteca MSAL no está instalada. Ejecute: pip install msal")
        except Exception as e:
            self.log_thread_safe(f"❌ Error al obtener token de SharePoint: {e}")
            return None
    
    def cargar_datos_principal(self):
        """Carga los datos principales desde SharePoint"""
        return self.descargar_csv_sharepoint()

    def descargar_csv_sharepoint(self):
        """Descarga el CSV desde SharePoint Online o lo carga desde caché"""
        try:
            # Verificar configuración de descarga forzada
            forzar_descarga = self.forzar_descarga_sharepoint.get()

            # Verificar si existe en caché y si no se está forzando descarga
            if self.cache_file_principal.exists() and not forzar_descarga:
                self.log_thread_safe("Archivo encontrado en caché, cargando...")

                # Mostrar información del caché
                size_mb = self.cache_file_principal.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(self.cache_file_principal.stat().st_mtime)
                self.log_thread_safe(f"Archivo en caché: {size_mb:.1f}MB - Última modificación: {mod_time.strftime('%d/%m/%Y %H:%M')}")

                # Cargar desde caché
                df = pd.read_csv(str(self.cache_file_principal))
                self.log_thread_safe(f"CSV cargado desde caché. Filas: {len(df)}, Columnas: {len(df.columns)}")

                # Aplicar mapeo de columnas de SharePoint
                return self.aplicar_mapeo_columnas_sharepoint(df)

            # Determinar razón para descargar
            if forzar_descarga:
                self.log_thread_safe("🔄 DESCARGA FORZADA - Ignorando caché, descargando versión más reciente desde SharePoint...")
            else:
                self.log_thread_safe("Archivo no encontrado en caché, descargando desde SharePoint...")

            # Obtener token de acceso
            access_token = self.obtener_sharepoint_token()
            if not access_token:
                raise Exception("No se pudo obtener token de acceso a SharePoint")

            # Codificar la URL de SharePoint para Microsoft Graph API
            self.log_thread_safe("Codificando URL para Microsoft Graph API...")
            sharepoint_url_bytes = self.sharepoint_url.encode('utf-8')
            encoded_url = base64.urlsafe_b64encode(sharepoint_url_bytes).decode('utf-8').rstrip('=')

            graph_url = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}/driveItem/content"
            self.log_thread_safe(f"URL Graph API: {graph_url[:100]}...")

            # Configurar headers para Microsoft Graph API
            headers = {
                'Authorization': f'Bearer {access_token}'
            }

            self.log_thread_safe("Descargando formato_ppias.csv desde SharePoint vía Graph API...")

            # Realizar petición HTTP a Microsoft Graph API
            response = requests.get(graph_url, headers=headers, verify=False, timeout=300)
            response.raise_for_status()

            # Guardar en caché
            self.log_thread_safe("Guardando archivo en caché...")
            with open(str(self.cache_file_principal), 'wb') as f:
                f.write(response.content)

            # Convertir a DataFrame
            csv_string = response.content.decode('utf-8')
            df = pd.read_csv(StringIO(csv_string))

            # Actualizar estado del caché
            self.verificar_cache_status()

            self.log_thread_safe(f"CSV descargado desde SharePoint y guardado en caché. Filas: {len(df)}, Columnas: {len(df.columns)}")
            self.log_thread_safe(f"Columnas originales de SharePoint: {list(df.columns)}")

            # Aplicar mapeo de columnas de SharePoint
            return self.aplicar_mapeo_columnas_sharepoint(df)

        except Exception as e:
            self.log_thread_safe(f"Error al descargar CSV desde SharePoint: {e}")
            return None

    def aplicar_mapeo_columnas_sharepoint(self, df):
        """Aplica el mapeo de columnas de SharePoint a las columnas esperadas por la aplicación"""
        try:
            self.log_thread_safe("Aplicando mapeo de columnas de SharePoint...")

            # Mapeo de columnas SharePoint → Sistema interno
            mapeo_columnas = {
                'EAN_HIJO': 'sku_hijo_largo',
                'EAN_PADRE': 'sku_padre_largo',
                'COLOR': 'color',
                'VARIACION_PMM': 'sku_descripcion',
                self.columna_depto_sharepoint.get(): 'depto',  # Columna configurable desde GUI
                'MARCA': 'marca',
                'TALLA': 'talla'  # Nueva columna
            }

            # Aplicar mapeo
            df_mapeado = df.copy()
            columnas_mapeadas = []

            for col_sharepoint, col_sistema in mapeo_columnas.items():
                if col_sharepoint in df_mapeado.columns:
                    df_mapeado[col_sistema] = df_mapeado[col_sharepoint]
                    columnas_mapeadas.append(f"{col_sharepoint} → {col_sistema}")
                else:
                    self.log_thread_safe(f"⚠️ Columna '{col_sharepoint}' no encontrada en SharePoint")

            # Mostrar mapeo realizado
            for mapeo in columnas_mapeadas:
                self.log_thread_safe(f"✓ Mapeo: {mapeo}")

            # Verificar columnas críticas
            columnas_criticas = ['sku_hijo_largo', 'sku_padre_largo', 'color']
            columnas_faltantes = [col for col in columnas_criticas if col not in df_mapeado.columns]

            if columnas_faltantes:
                self.log_thread_safe(f"❌ ADVERTENCIA: Faltan columnas críticas: {', '.join(columnas_faltantes)}")
            else:
                self.log_thread_safe("✓ Todas las columnas críticas están disponibles")

            # Mostrar estadísticas de columnas mapeadas
            if 'sku_hijo_largo' in df_mapeado.columns:
                valores_unicos = df_mapeado['sku_hijo_largo'].nunique()
                valores_nulos = df_mapeado['sku_hijo_largo'].isnull().sum()
                self.log_thread_safe(f"sku_hijo_largo: {valores_unicos} valores únicos, {valores_nulos} nulos")

            if 'talla' in df_mapeado.columns:
                tallas_unicas = df_mapeado['talla'].nunique()
                self.log_thread_safe(f"✓ Columna 'talla' disponible con {tallas_unicas} valores únicos")

            return df_mapeado

        except Exception as e:
            self.log_thread_safe(f"Error al aplicar mapeo de columnas: {e}")
            return df

    def probar_conexion_sharepoint(self):
        """Prueba la conexión a SharePoint y muestra información sobre el archivo"""
        try:
            # Deshabilitar botón durante la prueba
            self.btn_test_conexion.config(state="disabled", text="Probando conexión...")
            self.root.update()

            self.log_thread_safe("=== PROBANDO CONEXIÓN A SHAREPOINT ===")

            # Primero verificar si MSAL está instalado
            try:
                import msal
                self.log_thread_safe("✓ Biblioteca MSAL disponible")
            except ImportError:
                raise Exception("La biblioteca MSAL no está instalada.\n\nPor favor ejecuta:\npip install msal")

            # Obtener token de acceso
            access_token = self.obtener_sharepoint_token()
            if not access_token:
                # Ofrecer alternativa manual
                respuesta = messagebox.askyesno(
                    "Error de Autenticación",
                    "No se pudo obtener token automáticamente.\n\n" +
                    "Esto puede deberse a:\n" +
                    "• Permisos de la aplicación Azure CLI\n" +
                    "• Configuración de tenant corporativo\n" +
                    "• Políticas de seguridad de Ripley\n\n" +
                    "¿Quieres intentar con configuración alternativa?"
                )

                if respuesta:
                    return self.probar_configuracion_alternativa()
                else:
                    raise Exception("No se pudo obtener token de acceso a SharePoint")

            self.log_thread_safe("✓ Token de SharePoint obtenido exitosamente")

            # Codificar la URL de SharePoint para Microsoft Graph API
            self.log_thread_safe("Codificando URL para Microsoft Graph API...")
            sharepoint_url_bytes = self.sharepoint_url.encode('utf-8')
            encoded_url = base64.urlsafe_b64encode(sharepoint_url_bytes).decode('utf-8').rstrip('=')

            graph_url = f"https://graph.microsoft.com/v1.0/shares/u!{encoded_url}/driveItem"
            self.log_thread_safe(f"URL Graph API: {graph_url[:100]}...")

            # Configurar headers para Microsoft Graph API
            headers = {
                'Authorization': f'Bearer {access_token}'
            }

            # Hacer una petición para obtener información del archivo vía Graph API
            self.log_thread_safe("Verificando acceso al archivo formato_ppias.csv vía Graph API...")
            response = requests.get(graph_url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()

            self.log_thread_safe("✓ Acceso al archivo verificado")

            # Mostrar información del archivo desde Graph API
            try:
                file_info = response.json()
                if 'size' in file_info:
                    size_bytes = file_info['size']
                    size_mb = size_bytes / (1024 * 1024)
                    self.log_thread_safe(f"✓ Tamaño del archivo: {size_mb:.2f} MB")

                if 'lastModifiedDateTime' in file_info:
                    self.log_thread_safe(f"✓ Última modificación: {file_info['lastModifiedDateTime']}")

                if 'name' in file_info:
                    self.log_thread_safe(f"✓ Nombre del archivo: {file_info['name']}")

            except Exception as e:
                self.log_thread_safe(f"⚠️ No se pudo obtener información detallada del archivo: {e}")

            # Verificar caché local
            if self.cache_file_principal.exists():
                cache_size = self.cache_file_principal.stat().st_size / (1024 * 1024)
                cache_time = datetime.fromtimestamp(self.cache_file_principal.stat().st_mtime)
                self.log_thread_safe(f"✓ Archivo en caché: {cache_size:.2f} MB - {cache_time.strftime('%d/%m/%Y %H:%M')}")

            self.log_thread_safe("=== CONEXIÓN A SHAREPOINT EXITOSA ===")
            messagebox.showinfo("Conexión Exitosa",
                              "✓ Conexión a SharePoint verificada correctamente\n" +
                              "✓ Acceso al archivo formato_ppias.csv confirmado\n\n" +
                              "Ya puedes procesar los datos.")

        except requests.exceptions.RequestException as e:
            self.log_thread_safe(f"❌ Error de red: {e}")
            messagebox.showerror("Error de Conexión",
                               f"Error de conexión de red:\n\n{e}\n\n" +
                               "Verifica tu conexión a internet.")
        except Exception as e:
            self.log_thread_safe(f"❌ Error al probar conexión: {e}")
            messagebox.showerror("Error de Conexión",
                               f"No se pudo conectar a SharePoint:\n\n{e}")
        finally:
            # Rehabilitar botón
            self.btn_test_conexion.config(state="normal", text="Probar Conexión a SharePoint")

    def probar_configuracion_alternativa(self):
        """Prueba configuraciones alternativas para SharePoint"""
        self.log_thread_safe("=== PROBANDO CONFIGURACIÓN ALTERNATIVA ===")

        # Mostrar información de troubleshooting
        info_msg = """Pasos para resolver problemas de autenticación:

1. Verificar permisos en Azure AD:
   - Sites.Read.All
   - Files.Read.All

2. Configurar tenant específico:
   - Contactar al administrador de Azure AD de Ripley
   - Verificar que la app esté registrada en el tenant correcto

3. Verificar conectividad:
   - Acceso a https://ripleycorp.sharepoint.com
   - Permisos en el sitio Equipopyc

4. Limpiar caché de tokens:
   - Eliminar archivos en ~/.appsuite_cache/"""

        messagebox.showinfo("Información de Troubleshooting", info_msg)

        # Ofrecer limpiar caché
        if messagebox.askyesno("Limpiar Caché", "¿Quieres limpiar el caché de tokens para forzar nueva autenticación?"):
            self.limpiar_cache_tokens()

    def limpiar_cache_tokens(self):
        """Limpia el caché de tokens para forzar nueva autenticación"""
        try:
            cache_dir = Path.home() / SharePointAuth.CACHE_DIR_NAME
            if cache_dir.exists():
                for cache_file in cache_dir.glob("sharepoint_token_cache_*"):
                    cache_file.unlink()
                    self.log_thread_safe(f"✓ Eliminado: {cache_file}")

                self.log_thread_safe("✓ Caché de tokens limpiado")

                # Reinicializar la instancia de autenticación
                if hasattr(self, '_sharepoint_auth'):
                    delattr(self, '_sharepoint_auth')

                messagebox.showinfo("Caché Limpiado", "El caché de tokens ha sido limpiado.\n\nIntenta la conexión nuevamente.")
            else:
                self.log_thread_safe("No hay caché para limpiar")

        except Exception as e:
            self.log_thread_safe(f"Error al limpiar caché: {e}")

    def descargar_datos_sharepoint(self):
        """Descarga y procesa los datos desde SharePoint"""
        try:
            # Deshabilitar botón durante la descarga
            self.btn_descargar_datos.config(state="disabled", text="Descargando...")
            self.btn_test_conexion.config(state="disabled")
            self.root.update()

            self.log_thread_safe("=== INICIANDO DESCARGA DESDE SHAREPOINT ===")

            # Descargar CSV de SharePoint
            df = self.descargar_csv_sharepoint()
            if df is None or df.empty:
                raise Exception("No se pudieron obtener datos desde SharePoint")

            # Mostrar información sobre los datos descargados
            self.log_thread_safe(f"✓ Datos descargados: {len(df)} filas, {len(df.columns)} columnas")
            self.log_thread_safe(f"✓ Columnas disponibles: {list(df.columns)}")

            # Verificar que el mapeo de columnas sea correcto
            columnas_mapeadas = []
            columnas_faltantes = []

            mapeo_esperado = {
                'EAN_HIJO': 'sku_hijo_largo',
                'EAN_PADRE': 'sku_padre_largo',
                'COLOR': 'color',
                'VARIACION_PMM': 'sku_descripcion',
                'COD DPTO': 'depto',
                'MARCA': 'marca',
                'TALLA': 'talla'
            }

            for col_sharepoint, col_sistema in mapeo_esperado.items():
                if col_sharepoint in df.columns:
                    columnas_mapeadas.append(f"{col_sharepoint} → {col_sistema}")
                else:
                    columnas_faltantes.append(col_sharepoint)

            if columnas_mapeadas:
                self.log_thread_safe("✓ Mapeo de columnas verificado:")
                for mapeo in columnas_mapeadas:
                    self.log_thread_safe(f"  - {mapeo}")

            if columnas_faltantes:
                self.log_thread_safe("⚠️ Columnas faltantes en SharePoint:")
                for col in columnas_faltantes:
                    self.log_thread_safe(f"  - {col}")

            # Mostrar estadísticas de los datos
            if 'sku_hijo_largo' in df.columns:
                valores_unicos = df['sku_hijo_largo'].nunique()
                valores_nulos = df['sku_hijo_largo'].isnull().sum()
                self.log_thread_safe(f"✓ SKU hijos únicos: {valores_unicos}, nulos: {valores_nulos}")

            if 'talla' in df.columns:
                tallas_unicas = df['talla'].nunique()
                self.log_thread_safe(f"✓ Tallas únicas: {tallas_unicas}")

            self.log_thread_safe("=== DATOS SHAREPOINT LISTOS PARA PROCESAR ===")

            # Mostrar mensaje de éxito
            messagebox.showinfo("Descarga Exitosa",
                              f"✓ Datos descargados desde SharePoint\n" +
                              f"✓ {len(df)} registros procesados\n" +
                              f"✓ {len(columnas_mapeadas)} columnas mapeadas\n\n" +
                              "Los datos están listos para comparar con las carpetas.\n" +
                              "Ahora puedes usar 'Procesar y Generar Reporte'.")

        except Exception as e:
            self.log_thread_safe(f"❌ Error al descargar datos desde SharePoint: {e}")
            messagebox.showerror("Error de Descarga",
                               f"No se pudieron descargar los datos:\n\n{e}")
        finally:
            # Rehabilitar botones
            self.btn_descargar_datos.config(state="normal", text="Descargar Datos desde SharePoint")
            self.btn_test_conexion.config(state="normal")

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

    # FUNCIÓN AZURE LEGACY - NO UTILIZADA (ahora se usa SharePoint)
    # def descargar_csv_blob(self):
    #     """Esta función ha sido reemplazada por descargar_csv_sharepoint()"""
    #     pass
    
    # FUNCIÓN AZURE LEGACY - NO UTILIZADA (SharePoint no tiene datos de materialidad)
    # def descargar_csv_materialidad(self):
    #     """Esta función ha sido desactivada - SharePoint no incluye datos de materialidad"""
    #     return None
    
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

        # Fuente de datos: SharePoint
        self.log_thread_safe("Fuente de datos: SharePoint Online (formato_ppias.csv)")

        # Verificar columnas del CSV
        self.log_thread_safe(f"Columnas en el archivo: {list(df.columns)}")
        
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
            # Para cada coincidencia exacta, encontrar registros relacionados con la misma combinación de padre+color
            coincidencias_relacionadas = []

            # Obtener las combinaciones únicas de (sku_padre_largo, color) de las coincidencias exactas
            combinaciones_exactas = coincidencias_exactas[['sku_padre_largo', 'color']].drop_duplicates()

            self.log_thread_safe(f"Total de combinaciones únicas (padre + color): {len(combinaciones_exactas)}")

            contador = 1
            for _, row in combinaciones_exactas.iterrows():
                sku_padre = row['sku_padre_largo']
                color = row['color']

                # Manejar valores nulos en color
                if pd.isna(color) or color == '' or str(color).strip() == '':
                    self.log_thread_safe(f"Procesando combinación {contador}/{len(combinaciones_exactas)}: sku_padre='{sku_padre}', color=NULL/VACÍO")
                    # Buscar registros con el mismo sku_padre_largo Y color nulo/vacío
                    relacionadas = df[
                        (df['sku_padre_largo'] == sku_padre) &
                        ((df['color'].isna()) | (df['color'] == '') | (df['color'].astype(str).str.strip() == ''))
                    ].copy()
                else:
                    self.log_thread_safe(f"Procesando combinación {contador}/{len(combinaciones_exactas)}: sku_padre='{sku_padre}', color='{color}'")
                    # Buscar registros con el mismo sku_padre_largo Y el mismo color
                    relacionadas = df[
                        (df['sku_padre_largo'] == sku_padre) &
                        (df['color'] == color)
                    ].copy()

                self.log_thread_safe(f"  - Encontrados {len(relacionadas)} registros relacionados")

                if len(relacionadas) > 0:
                    coincidencias_relacionadas.append(relacionadas)
                else:
                    self.log_thread_safe(f"  - ⚠️ No se encontraron registros para esta combinación")

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
            columnas_reporte = ['sku_padre_largo', 'sku_hijo_largo', 'sku_descripcion', 'depto', 'color', 'marca', 'talla']
            
            # Todas las columnas ya están incluidas para SharePoint
            self.log_thread_safe("✓ Columnas configuradas para reporte SharePoint")
            
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

    def _migrate_local_cache(self):
        """Migra el cache del directorio local al directorio del sistema"""
        try:
            # Directorio local donde estaba el cache anteriormente
            old_cache_dir = Path(os.path.dirname(os.path.abspath(__file__))) / "cache"
            old_cache_file = old_cache_dir / "formato_ppias.csv"

            # Si existe el archivo en cache local y no existe en el nuevo cache del sistema
            if old_cache_file.exists() and not self.cache_file_principal.exists():
                print(f"Migrando cache de {old_cache_file} a {self.cache_file_principal}")

                # Copiar el archivo al nuevo directorio
                shutil.copy2(str(old_cache_file), str(self.cache_file_principal))
                print(f"Cache migrado exitosamente")

                # Opcional: eliminar el directorio cache local después de migrar
                try:
                    shutil.rmtree(str(old_cache_dir))
                    print(f"Directorio cache local eliminado: {old_cache_dir}")
                except Exception as e:
                    print(f"Advertencia: No se pudo eliminar directorio cache local: {e}")

        except Exception as e:
            print(f"Advertencia: Error durante migración de cache: {e}")

    def verificar_cache_status(self):
        """Verifica el estado del caché y actualiza la UI"""
        try:
            cache_info = []

            # Verificar si se forzará descarga
            forzar_descarga = self.forzar_descarga_sharepoint.get()

            # Verificar CSV principal de SharePoint
            if self.cache_file_principal.exists():
                size_mb = self.cache_file_principal.stat().st_size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(self.cache_file_principal.stat().st_mtime)

                if forzar_descarga:
                    cache_info.append(f"SharePoint ({size_mb:.1f}MB - {mod_time.strftime('%d/%m %H:%M')}) - 🔄 Se descargará nueva versión")
                else:
                    cache_info.append(f"SharePoint ({size_mb:.1f}MB - {mod_time.strftime('%d/%m %H:%M')}) - ✅ Se usará caché")

            if cache_info:
                status_text = f"Caché: {', '.join(cache_info)}"
                self.cache_status.set(status_text)
            elif forzar_descarga:
                self.cache_status.set("Sin caché - Se descargará desde SharePoint")
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

    def on_forzar_descarga_change(self):
        """Maneja cambios en el checkbox de forzar descarga"""
        # Actualizar el estado del caché para reflejar el cambio
        self.verificar_cache_status()
    
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
    
    def cargar_datos_responsables(self):
        """Carga los datos de responsables desde PERU.xlsx"""
        try:
            archivo_path = os.path.join("docs", "PERU.xlsx")
            
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
            
            self.log_thread_safe(f"Datos de PERU cargados: {len(df_responsables)} departamentos")
            self.log_thread_safe(f"Departamentos encontrados: {df_responsables['DEPTOS'].nunique()} únicos")

            return df_responsables

        except Exception as e:
            self.log_thread_safe(f"Error al cargar datos de PERU: {e}")
            return None
    
    def generar_archivo_responsables(self, departamentos_encontrados):
        """Genera archivo con responsables por departamento (PERU)"""
        try:
            self.log_thread_safe("=== GENERANDO ARCHIVO DE RESPONSABLES (PERU) ===")

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
            nombre_archivo = f"responsables_peru_{timestamp}.xlsx"
            
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

            # Crear nombre del archivo/enlace
            nombre_archivo = f"{fecha_actual} ({cantidad_sku} SKU) PERU"
            
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
            <th>talla</th>
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
                talla = row.get('talla', '')

                html_content += f"""        <tr>
            <td>{ean_hijo}</td>
            <td>{ean_padre}</td>
            <td>{variacion}</td>
            <td>{cod_dpto}</td>
            <td>{marca}</td>
            <td>{color}</td>
            <td>{talla}</td>
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

    def generar_reporte_completo_metodo(self, df_relacionadas, df_exactas, df_completo):
        """Genera un reporte Excel solo con la hoja de Relacionadas y columnas originales de la base de datos"""
        try:
            self.log_thread_safe("=== GENERANDO INFO_REDACCION ===")

            # Obtener solo las columnas originales de la base de datos (df_completo)
            columnas_originales = list(df_completo.columns)
            self.log_thread_safe(f"Total de columnas originales de la base de datos: {len(columnas_originales)}")
            self.log_thread_safe(f"Columnas disponibles: {', '.join(columnas_originales[:10])}{'...' if len(columnas_originales) > 10 else ''}")

            # Crear nombre de archivo con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"INFO_REDACCION_{timestamp}.xlsx"

            # Obtener ruta completa
            ubicacion_carpetas = self.ubicacion_carpetas.get()
            ruta_completa = os.path.join(ubicacion_carpetas, nombre_archivo)

            self.log_thread_safe(f"Creando INFO_REDACCION en: {ruta_completa}")

            # Preparar DataFrame solo con columnas originales (sin columnas añadidas durante el procesamiento)
            df_relacionadas_original = df_relacionadas.copy()

            # Filtrar solo las columnas que existen en el DataFrame original
            columnas_filtradas = [col for col in columnas_originales if col in df_relacionadas_original.columns]
            df_relacionadas_original = df_relacionadas_original[columnas_filtradas]

            # Crear archivo Excel con una sola hoja
            with pd.ExcelWriter(ruta_completa, engine='openpyxl') as writer:
                # Solo hoja de Relacionadas con columnas originales
                self.log_thread_safe("Escribiendo hoja 'Relacionadas - Completo'...")
                df_relacionadas_original.to_excel(writer, sheet_name='Relacionadas - Completo', index=False)

            # Estadísticas del reporte
            self.log_thread_safe(f"✅ INFO_REDACCION generado exitosamente: {nombre_archivo}")
            self.log_thread_safe(f"- Hoja única (Relacionadas): {len(df_relacionadas_original)} filas, {len(df_relacionadas_original.columns)} columnas")
            self.log_thread_safe(f"- Columnas originales incluidas: {len(columnas_filtradas)}")

            return ruta_completa

        except Exception as e:
            self.log_thread_safe(f"❌ Error al generar INFO_REDACCION: {e}")
            return None

    def run(self):
        """Ejecuta la aplicación"""
        self.root.mainloop()


if __name__ == "__main__":
    app = AppCargas()
    app.run()