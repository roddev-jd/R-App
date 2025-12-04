import os
import sys
import pandas as pd
from PIL import Image
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import threading
import queue


class ImageProcessorThread(threading.Thread):
    """Hilo para procesar imágenes sin bloquear la interfaz"""

    def __init__(self, excel_file, images_folder, logos_folder, output_folder,
                 output_format, overwrite_originals, generate_report, altura_logo,
                 column_mapping, result_queue):
        super().__init__(daemon=True)
        self.excel_file = excel_file
        self.images_folder = images_folder
        self.logos_folder = logos_folder
        self.output_folder = output_folder
        self.output_format = output_format
        self.overwrite_originals = overwrite_originals
        self.generate_report = generate_report
        self.altura_logo = altura_logo
        self.column_mapping = column_mapping
        self.result_queue = result_queue

    def run(self):
        try:
            df = pd.read_excel(self.excel_file)
            df.columns = df.columns.str.strip().str.lower()
        except Exception as e:
            self.result_queue.put(('finished', {
                'errors': [f"No se pudo leer la planilla Excel: {e}"],
                'report_path': None
            }))
            return

        total = len(df)
        self.result_queue.put(('total', total))
        error_report = []

        for index, row in df.iterrows():
            try:
                # Usar mapeo de columnas personalizado (convertir a minúsculas para coincidir con df.columns)
                talla_col = self.column_mapping.get('talla', 'talla').lower().strip()
                upc_col = self.column_mapping.get('upc_ripley', 'upc_ripley').lower().strip()
                compromiso_col = self.column_mapping.get('compromiso_r', 'compromiso_r').lower().strip()

                print(f"Fila {index+2}: Buscando columnas - UPC: '{upc_col}', Talla: '{talla_col}', Compromiso: '{compromiso_col}'")

                talla_value = str(row.get(talla_col, "")).strip()
                if talla_value.lower() == "nan":
                    talla_value = ""
                upc_ripley = str(row.get(upc_col, "")).strip()
                if upc_ripley.lower() == "nan":
                    upc_ripley = ""
                compromiso_r = str(row.get(compromiso_col, "")).strip()
                if compromiso_r.lower() == "nan":
                    compromiso_r = ""

                if upc_ripley == "":
                    error_report.append(f"Fila {index+2}: UPC vacío.")
                    continue

                image_file = None
                for root_dir, _, files in os.walk(self.images_folder):
                    for file in files:
                        nombre, ext = os.path.splitext(file)
                        if ext.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                            if upc_ripley in nombre and nombre.endswith("_2"):
                                image_file = os.path.join(root_dir, file)
                                break
                    if image_file:
                        break

                if not image_file:
                    error_report.append(f"Fila {index+2}: No se encontró imagen para UPC: {upc_ripley}")
                    continue

                # Procesar imagen con PIL
                with Image.open(image_file) as im:
                    # Preservar información original de la imagen
                    icc_profile = im.info.get("icc_profile")
                    original_mode = im.mode
                    original_size = im.size

                    # Convertir a RGBA solo si es necesario para aplicar logos
                    if im.mode != "RGBA":
                        im = im.convert("RGBA")

                    # Lista para almacenar logos aplicados (para debugging)
                    logos_aplicados = []

                    # 1. Aplicar logo según el valor de la columna "talla"
                    if talla_value:
                        # Buscar logo con diferentes variaciones según los archivos reales
                        posibles_logos = [
                            f"{talla_value}.png",  # S.png, M.png, L.png, 28.png, 30.png, etc.
                            f"{talla_value.upper()}.png",  # S.png, M.png, L.png, etc.
                            f"{talla_value.lower()}.png",  # s.png, m.png, l.png, etc.
                            f"talla-{talla_value}.png",  # talla-S.png, talla-M.png, etc.
                            f"talla-{talla_value.upper()}.png",
                            f"talla-{talla_value.lower()}.png",
                            # Casos especiales para combinaciones
                            f"{talla_value}-{talla_value}.png",  # S-S.png, M-M.png, etc.
                            f"XS-{talla_value}.png",  # XS-S.png, XS-M.png, etc.
                            f"S-{talla_value}.png",   # S-M.png, S-L.png, etc.
                            # Para logos de altura (si el valor coincide con un logo de altura)
                            f"altura-{talla_value}.png",  # altura-1,67.png, altura-1,69.png, etc.
                        ]

                        logo_encontrado = False
                        for posible_logo in posibles_logos:
                            logo_path = os.path.join(self.logos_folder, posible_logo)
                            if os.path.exists(logo_path):
                                try:
                                    with Image.open(logo_path) as logo:
                                        logo = logo.convert("RGBA")
                                        # Los logos tienen el mismo tamaño que las imágenes, solo superponer
                                        im.paste(logo, (0, 0), logo)
                                        logos_aplicados.append(f"Talla: {posible_logo}")
                                        logo_encontrado = True
                                        break
                                except Exception as e:
                                    error_report.append(f"Fila {index+2}: Error al aplicar logo {posible_logo}: {e}")

                        if not logo_encontrado:
                            error_report.append(f"Fila {index+2}: No se encontró logo para talla '{talla_value}'. Buscó: {', '.join(posibles_logos)}")

                    # 2. Aplicar logo de compromiso si existe valor en compromiso_r
                    print(f"Fila {index+2}: Valor compromiso_r = '{compromiso_r}' (tipo: {type(compromiso_r)})")

                    # Verificar diferentes variaciones del archivo de compromiso
                    posibles_compromiso = [
                        "compromiso.png",
                        "compromiso_r.png",
                        "COMPROMISO.png",
                        "COMPROMISO_R.png",
                        "Compromiso.png"
                    ]

                    if compromiso_r and str(compromiso_r).strip() and str(compromiso_r).strip().lower() not in ["nan", "none", ""]:
                        compromiso_encontrado = False

                        for compromiso_file in posibles_compromiso:
                            compromiso_logo_path = os.path.join(self.logos_folder, compromiso_file)
                            print(f"Fila {index+2}: Buscando compromiso en: {compromiso_logo_path}")

                            if os.path.exists(compromiso_logo_path):
                                print(f"Fila {index+2}: Encontrado archivo compromiso: {compromiso_file}")
                                try:
                                    with Image.open(compromiso_logo_path) as compromiso_logo:
                                        compromiso_logo = compromiso_logo.convert("RGBA")
                                        # Los logos tienen el mismo tamaño que las imágenes, solo superponer
                                        im.paste(compromiso_logo, (0, 0), compromiso_logo)
                                        logos_aplicados.append(f"Compromiso: {compromiso_file}")
                                        compromiso_encontrado = True
                                        break
                                except Exception as e:
                                    error_report.append(f"Fila {index+2}: Error al aplicar logo de compromiso {compromiso_file}: {e}")

                        if not compromiso_encontrado:
                            error_report.append(f"Fila {index+2}: No se encontró ningún archivo de compromiso. Buscó: {', '.join(posibles_compromiso)}")
                    else:
                        print(f"Fila {index+2}: Columna compromiso_r vacía o inválida ('{compromiso_r}'), no se aplica logo de compromiso")

                    # 3. Aplicar logo de altura manual (si está seleccionado)
                    if self.altura_logo and os.path.exists(self.altura_logo):
                        try:
                            with Image.open(self.altura_logo) as altura_logo:
                                altura_logo = altura_logo.convert("RGBA")
                                # Los logos tienen el mismo tamaño que las imágenes, solo superponer
                                im.paste(altura_logo, (0, 0), altura_logo)
                                logos_aplicados.append(f"Altura Manual: {os.path.basename(self.altura_logo)}")
                        except Exception as e:
                            error_report.append(f"Fila {index+2}: Error al aplicar logo de altura manual: {e}")
                    elif self.altura_logo:
                        error_report.append(f"Fila {index+2}: No se encontró el archivo de altura: {self.altura_logo}")

                    # Debug: agregar información sobre logos aplicados
                    if logos_aplicados:
                        print(f"Logos aplicados a {os.path.basename(image_file)}: {', '.join(logos_aplicados)}")
                    else:
                        print(f"No se aplicaron logos a {os.path.basename(image_file)}")
                        error_report.append(f"Fila {index+2}: No se encontraron logos para aplicar")

                    # Guardar imagen procesada en formato WebP
                    base_name = os.path.splitext(os.path.basename(image_file))[0]
                    output_dir = self.output_folder if not self.overwrite_originals else os.path.dirname(image_file)
                    output_file_path = os.path.join(output_dir, f"{base_name}.webp")

                    # Guardar en formato WebP preservando calidad y transparencia
                    im.save(output_file_path, format="WEBP", quality=100, icc_profile=icc_profile)

            except Exception as e:
                error_report.append(f"Fila {index+2}: Error al procesar la imagen {os.path.basename(image_file if image_file else 'desconocida')}: {e}")

            finally:
                self.result_queue.put(('progress', index + 1))

        # Generar reporte de errores
        reporte_path_final = None
        if self.generate_report and error_report:
            report_location = self.output_folder if self.output_folder and not self.overwrite_originals else os.path.dirname(self.excel_file)
            reporte_path_final = os.path.join(report_location, "reporte_errores.txt")
            try:
                with open(reporte_path_final, "w", encoding="utf-8") as f:
                    f.write("Reporte de Errores/Incidencias:\n\n" + "\n".join(error_report))
            except Exception as e:
                error_report.append(f"CRÍTICO: No se pudo escribir el reporte de errores: {e}")
                reporte_path_final = None

        self.result_queue.put(('finished', {
            'errors': error_report,
            'report_path': reporte_path_final
        }))


class ImageLogoApplier(tk.Tk):
    def __init__(self):
        super().__init__()

        self.excel_file = ""
        self.images_folder = ""
        self.logos_folder = ""
        self.output_folder = ""
        self.altura_file = ""
        self.processor_thread = None
        self.excel_columns = []
        self.column_mapping = {
            'upc_ripley': 'upc_ripley',
            'talla': 'talla',
            'compromiso_r': 'compromiso_r'
        }

        # Cola para comunicación con el hilo
        self.result_queue = queue.Queue()

        self.init_ui()
        self.show_warning_message()

    def init_ui(self):
        self.title("Aplicador de Logos en Imágenes v3.0 (tkinter)")
        self.geometry("800x600")
        self.resizable(True, True)

        # Frame principal con scroll
        main_frame = ttk.Frame(self, padding="20 20 20 20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        current_row = 0

        # Título
        title_label = tk.Label(main_frame, text="Aplicador de Logos en Imágenes",
                               font=("", 16, "bold"))
        title_label.grid(row=current_row, column=0, columnspan=3, pady=(0, 15))
        current_row += 1

        # Grupo de configuración
        config_frame = ttk.LabelFrame(main_frame, text="Configuración de Archivos", padding="10 10 10 10")
        config_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        config_frame.columnconfigure(1, weight=1)
        current_row += 1

        # 1. Planilla Excel
        ttk.Label(config_frame, text="1. Planilla Excel:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.excel_entry = ttk.Entry(config_frame, state='readonly')
        self.excel_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(config_frame, text="Seleccionar", command=self.select_excel_file).grid(row=0, column=2, pady=5)

        # 2. Carpeta de Imágenes
        ttk.Label(config_frame, text="2. Carpeta de Imágenes:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.images_entry = ttk.Entry(config_frame, state='readonly')
        self.images_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(config_frame, text="Seleccionar", command=self.select_images_folder).grid(row=1, column=2, pady=5)

        # 3. Carpeta de Logos
        ttk.Label(config_frame, text="3. Carpeta de Logos:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.logos_entry = ttk.Entry(config_frame, state='readonly')
        self.logos_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(config_frame, text="Seleccionar", command=self.select_logos_folder).grid(row=2, column=2, pady=5)

        # 4. Logo Altura (Manual)
        ttk.Label(config_frame, text="4. Logo Altura (Manual):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.altura_entry = ttk.Entry(config_frame, state='readonly')
        self.altura_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(config_frame, text="Seleccionar", command=self.select_altura_file).grid(row=3, column=2, pady=5)

        # Información adicional sobre logos de altura
        altura_info = tk.Label(config_frame, text="Se aplica a todas las imágenes. Selecciona manualmente el archivo PNG",
                              fg="#666", font=("", 8))
        altura_info.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))

        # 5. Información sobre logos automáticos
        info_label = tk.Label(config_frame, text="5. Los logos se aplican automáticamente según la planilla",
                             fg="#666", font=("", 10, "italic"))
        info_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=5)

        # Grupo de mapeo de columnas (inicialmente oculto)
        self.mapping_frame = ttk.LabelFrame(main_frame, text="Mapeo de Columnas", padding="10 10 10 10")
        self.mapping_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        self.mapping_frame.columnconfigure(1, weight=1)
        self.mapping_frame.grid_remove()  # Ocultar inicialmente
        current_row += 1

        # Información sobre mapeo
        mapping_info = tk.Label(self.mapping_frame, text="Selecciona qué columnas de tu Excel corresponden a cada campo:",
                               fg="#333", font=("", 10, "bold"))
        mapping_info.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Campo para UPC (obligatorio)
        ttk.Label(self.mapping_frame, text="Columna UPC (Obligatorio):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.upc_entry = ttk.Entry(self.mapping_frame)
        self.upc_entry.insert(0, "upc_ripley")
        self.upc_entry.bind('<KeyRelease>', lambda e: self.update_column_mapping())
        self.upc_entry.grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Campo para Talla (opcional)
        ttk.Label(self.mapping_frame, text="Columna Talla (Opcional):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.talla_entry = ttk.Entry(self.mapping_frame)
        self.talla_entry.insert(0, "talla")
        self.talla_entry.bind('<KeyRelease>', lambda e: self.update_column_mapping())
        self.talla_entry.grid(row=2, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Campo para Compromiso (opcional)
        ttk.Label(self.mapping_frame, text="Columna Compromiso (Opcional):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.compromiso_entry = ttk.Entry(self.mapping_frame)
        self.compromiso_entry.insert(0, "compromiso_r")
        self.compromiso_entry.bind('<KeyRelease>', lambda e: self.update_column_mapping())
        self.compromiso_entry.grid(row=3, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Botón para refrescar columnas
        ttk.Button(self.mapping_frame, text="Refrescar Columnas",
                  command=self.load_excel_columns).grid(row=4, column=0, columnspan=3, pady=10)

        # Grupo de opciones
        options_frame = ttk.LabelFrame(main_frame, text="Opciones de Procesamiento", padding="10 10 10 10")
        options_frame.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        options_frame.columnconfigure(1, weight=1)
        current_row += 1

        # Opción de reemplazar originales
        self.overwrite_var = tk.BooleanVar()
        self.overwrite_check = ttk.Checkbutton(options_frame, text="Reemplazar imágenes originales",
                                               variable=self.overwrite_var,
                                               command=self.toggle_output_folder_state)
        self.overwrite_check.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)

        # 6. Carpeta de Salida
        ttk.Label(options_frame, text="6. Carpeta de Salida:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_entry = ttk.Entry(options_frame, state='readonly')
        self.output_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.output_button = ttk.Button(options_frame, text="Seleccionar", command=self.select_output_folder)
        self.output_button.grid(row=1, column=2, pady=5)

        # Generar reporte
        self.report_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Generar reporte de errores",
                       variable=self.report_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)

        # Barra de progreso
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.grid(row=current_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 15))
        self.progress_bar.grid_remove()  # Ocultar inicialmente
        current_row += 1

        # Botón de procesar
        self.process_button = ttk.Button(main_frame, text="Procesar Imágenes",
                                        command=self.start_processing)
        self.process_button.grid(row=current_row, column=0, columnspan=3, pady=10, ipady=10)

        # Configurar expansión de columnas
        main_frame.columnconfigure(0, weight=0)
        main_frame.columnconfigure(1, weight=1)
        main_frame.columnconfigure(2, weight=0)

    def show_warning_message(self):
        """Muestra mensaje de advertencia inicial"""
        messagebox.showwarning(
            "Recomendación Importante",
            "Antes de comenzar, por favor, comprime la carpeta original de las imágenes "
            "para tener un respaldo en caso de generarse un error inesperado durante el proceso."
        )

    def select_excel_file(self):
        """Selecciona archivo Excel"""
        file = filedialog.askopenfilename(
            title="Seleccionar Planilla Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if file:
            self.excel_file = file
            self.excel_entry.config(state='normal')
            self.excel_entry.delete(0, tk.END)
            self.excel_entry.insert(0, file)
            self.excel_entry.config(state='readonly')
            self.load_excel_columns()

    def select_images_folder(self):
        """Selecciona carpeta de imágenes"""
        folder = filedialog.askdirectory(title="Seleccionar Carpeta de Imágenes")
        if folder:
            self.images_folder = folder
            self.images_entry.config(state='normal')
            self.images_entry.delete(0, tk.END)
            self.images_entry.insert(0, folder)
            self.images_entry.config(state='readonly')

    def select_logos_folder(self):
        """Selecciona carpeta de logos"""
        folder = filedialog.askdirectory(title="Seleccionar Carpeta de Logos")
        if folder:
            self.logos_folder = folder
            self.logos_entry.config(state='normal')
            self.logos_entry.delete(0, tk.END)
            self.logos_entry.insert(0, folder)
            self.logos_entry.config(state='readonly')

    def select_output_folder(self):
        """Selecciona carpeta de salida"""
        folder = filedialog.askdirectory(title="Seleccionar Carpeta de Salida")
        if folder:
            self.output_folder = folder
            self.output_entry.config(state='normal')
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)
            self.output_entry.config(state='readonly')

    def select_altura_file(self):
        """Selecciona archivo PNG de altura"""
        file = filedialog.askopenfilename(
            title="Seleccionar Logo de Altura",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
        )
        if file:
            self.altura_file = file
            self.altura_entry.config(state='normal')
            self.altura_entry.delete(0, tk.END)
            self.altura_entry.insert(0, file)
            self.altura_entry.config(state='readonly')
            print(f"Logo de altura seleccionado: {file}")

    def load_excel_columns(self):
        """Carga las columnas del archivo Excel seleccionado"""
        if not self.excel_file:
            return

        try:
            # Leer solo la primera fila para obtener los nombres de columnas
            df_sample = pd.read_excel(self.excel_file, nrows=1)
            self.excel_columns = list(df_sample.columns)

            print(f"Columnas detectadas: {self.excel_columns}")  # Debug

            # Intentar hacer coincidencias automáticas inteligentes
            self.auto_match_columns()

            # Mostrar el grupo de mapeo
            self.mapping_frame.grid()

            # Crear mensaje con columnas disponibles
            columnas_texto = "\n• ".join(self.excel_columns)
            messagebox.showinfo(
                "Columnas cargadas",
                f"✅ Se cargaron {len(self.excel_columns)} columnas del Excel.\n\n"
                "📝 Escribe el nombre exacto de las columnas en los campos de abajo.\n"
                "🔍 El sistema intentó detectar automáticamente las columnas.\n\n"
                f"📋 Columnas disponibles:\n• {columnas_texto}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error al cargar columnas",
                f"No se pudieron cargar las columnas del Excel:\n{str(e)}"
            )
            self.mapping_frame.grid_remove()

    def auto_match_columns(self):
        """Intenta hacer coincidencias automáticas basadas en nombres similares"""
        # Solo auto-detectar si las columnas por defecto no existen

        # Verificar si UPC por defecto existe, sino buscar alternativa
        if 'upc_ripley' not in self.excel_columns:
            upc_keywords = ['upc', 'codigo', 'code', 'sku', 'barcode']
            for col in self.excel_columns:
                col_lower = col.lower().strip()
                if any(keyword in col_lower for keyword in upc_keywords):
                    self.upc_entry.delete(0, tk.END)
                    self.upc_entry.insert(0, col)
                    print(f"Auto-detectado UPC alternativo: {col}")
                    break
        else:
            print(f"Usando UPC por defecto: upc_ripley")

        # Verificar si Talla por defecto existe, sino buscar alternativa
        if 'talla' not in self.excel_columns:
            talla_keywords = ['talla', 'size', 'tamaño', 'medida']
            for col in self.excel_columns:
                col_lower = col.lower().strip()
                if any(keyword in col_lower for keyword in talla_keywords):
                    self.talla_entry.delete(0, tk.END)
                    self.talla_entry.insert(0, col)
                    print(f"Auto-detectado Talla alternativa: {col}")
                    break
        else:
            print(f"Usando Talla por defecto: talla")

        # Verificar si Compromiso por defecto existe, sino buscar alternativa
        if 'compromiso_r' not in self.excel_columns:
            compromiso_keywords = ['compromiso', 'commitment', 'pledge']
            for col in self.excel_columns:
                col_lower = col.lower().strip()
                if any(keyword in col_lower for keyword in compromiso_keywords):
                    self.compromiso_entry.delete(0, tk.END)
                    self.compromiso_entry.insert(0, col)
                    print(f"Auto-detectado Compromiso alternativo: {col}")
                    break
        else:
            print(f"Usando Compromiso por defecto: compromiso_r")

    def update_column_mapping(self):
        """Actualiza el mapeo de columnas cuando cambia la selección"""
        upc_text = self.upc_entry.get().strip()
        talla_text = self.talla_entry.get().strip()
        compromiso_text = self.compromiso_entry.get().strip()

        print(f"Mapeo actualizado - UPC: '{upc_text}', Talla: '{talla_text}', Compromiso: '{compromiso_text}'")  # Debug

        self.column_mapping = {}

        # UPC es obligatorio
        if upc_text:
            self.column_mapping['upc_ripley'] = upc_text

        # Talla es opcional
        if talla_text:
            self.column_mapping['talla'] = talla_text

        # Compromiso es opcional
        if compromiso_text:
            self.column_mapping['compromiso_r'] = compromiso_text

        print(f"Column mapping final: {self.column_mapping}")  # Debug

    def toggle_output_folder_state(self):
        """Habilita/deshabilita la carpeta de salida según la opción de reemplazar"""
        if self.overwrite_var.get():
            self.output_entry.config(state='normal')
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, "Las imágenes se guardarán en su ubicación original")
            self.output_entry.config(state='readonly')
            self.output_button.config(state='disabled')
        else:
            self.output_entry.config(state='normal')
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, self.output_folder)
            self.output_entry.config(state='readonly')
            self.output_button.config(state='normal')

    def start_processing(self):
        """Inicia el procesamiento de imágenes"""
        # Validar entradas básicas
        if (not self.excel_file or not self.images_folder or not self.logos_folder or
                (not self.overwrite_var.get() and not self.output_folder)):
            messagebox.showerror(
                "Error",
                "Por favor, completa los campos requeridos (1, 2, 3).\n"
                "Además, debes seleccionar una Carpeta de Salida (5) O activar la opción para reemplazar originales."
            )
            return

        # Validar mapeo de columnas
        if not self.column_mapping.get('upc_ripley'):
            messagebox.showerror(
                "Error de Mapeo",
                "Debes escribir el nombre de una columna para el campo UPC (obligatorio)."
            )
            return

        # Validar que las columnas existen en el Excel
        if hasattr(self, 'excel_columns') and self.excel_columns:
            missing_defaults = []
            missing_custom = []

            # Convertir columnas Excel a minúsculas para comparación
            excel_columns_lower = [col.lower().strip() for col in self.excel_columns]

            # Verificar columnas por defecto vs personalizadas
            default_columns = {'upc_ripley': 'upc_ripley', 'talla': 'talla', 'compromiso_r': 'compromiso_r'}

            for field, col_name in self.column_mapping.items():
                col_name_lower = col_name.lower().strip()
                if col_name_lower not in excel_columns_lower:
                    if col_name == default_columns.get(field):
                        # Es una columna por defecto que falta
                        field_name_spanish = {'upc_ripley': 'UPC', 'talla': 'Talla', 'compromiso_r': 'Compromiso'}.get(field, field)
                        missing_defaults.append(f"'{col_name}' (campo {field_name_spanish})")
                    else:
                        # Es una columna personalizada que falta
                        field_name_spanish = {'upc_ripley': 'UPC', 'talla': 'Talla', 'compromiso_r': 'Compromiso'}.get(field, field)
                        missing_custom.append(f"'{col_name}' (campo {field_name_spanish})")

            if missing_defaults or missing_custom:
                columnas_disponibles = "\n• ".join(self.excel_columns)
                mensaje = ""

                if missing_defaults:
                    mensaje += f"🔍 Las siguientes columnas por defecto no se encontraron:\n\n"
                    mensaje += '• ' + '\n• '.join(missing_defaults) + '\n\n'
                    mensaje += f"💡 Debes especificar nombres alternativos para estas columnas para continuar.\n\n"

                if missing_custom:
                    mensaje += f"❌ Las siguientes columnas personalizadas no existen:\n\n"
                    mensaje += '• ' + '\n• '.join(missing_custom) + '\n\n'

                mensaje += f"📋 Columnas disponibles en tu Excel:\n• {columnas_disponibles}\n\n"
                mensaje += f"✏️ Edita los nombres en los campos de mapeo para corregir esto."

                messagebox.showerror(
                    "⚠️ Columnas no encontradas",
                    mensaje
                )
                return

        if self.overwrite_var.get():
            reply = messagebox.askyesno(
                "Confirmación de Reemplazo",
                "Estás a punto de SOBREESCRIBIR las imágenes originales. Esta acción no se puede deshacer.\n\n"
                "¿Estás seguro de que quieres continuar?"
            )
            if not reply:
                return

        # Deshabilitar botón y mostrar barra de progreso
        self.process_button.config(state='disabled')
        self.progress_bar.grid()
        self.progress_bar['value'] = 0

        # Crear y configurar hilo de procesamiento
        self.processor_thread = ImageProcessorThread(
            excel_file=self.excel_file,
            images_folder=self.images_folder,
            logos_folder=self.logos_folder,
            output_folder=self.output_folder,
            output_format="webp",  # Siempre WebP
            overwrite_originals=self.overwrite_var.get(),
            generate_report=self.report_var.get(),
            altura_logo=self.altura_file,
            column_mapping=self.column_mapping,
            result_queue=self.result_queue
        )

        # Iniciar procesamiento
        self.processor_thread.start()

        # Iniciar verificación de la cola
        self.check_queue()

    def check_queue(self):
        """Verifica la cola de resultados del hilo"""
        try:
            while True:
                msg_type, data = self.result_queue.get_nowait()

                if msg_type == 'progress':
                    self.progress_bar['value'] = data
                elif msg_type == 'total':
                    self.progress_bar['maximum'] = data
                elif msg_type == 'finished':
                    self.process_finished(data)
                    return
        except queue.Empty:
            pass

        # Continuar verificando la cola
        self.after(100, self.check_queue)

    def process_finished(self, result_data):
        """Maneja la finalización del procesamiento"""
        self.progress_bar.grid_remove()
        self.progress_bar['value'] = 0
        self.process_button.config(state='normal')

        error_report = result_data['errors']
        report_path = result_data['report_path']

        # Crear mensaje detallado
        mensaje = "Proceso terminado.\n\n"

        if report_path:
            mensaje += f"✅ Se generó el reporte de errores en:\n{report_path}\n\n"

        if error_report:
            mensaje += f"⚠️ Se encontraron {len(error_report)} errores/incidencias:\n"
            summary = "\n".join(error_report[:10])  # Mostrar hasta 10 errores
            if len(error_report) > 10:
                summary += f"\n... y {len(error_report)-10} errores más."
            mensaje += summary
        else:
            mensaje += "✅ No se encontraron errores."

        # Mostrar mensaje con detalles
        if report_path:
            messagebox.showinfo("Proceso terminado", mensaje)
        elif error_report:
            messagebox.showwarning("Proceso terminado con errores", mensaje)
        else:
            messagebox.showinfo("Proceso terminado", mensaje)


def main():
    app = ImageLogoApplier()
    app.mainloop()


if __name__ == "__main__":
    main()
