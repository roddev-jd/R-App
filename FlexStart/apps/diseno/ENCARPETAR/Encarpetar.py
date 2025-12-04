#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import shutil
import threading
import re
from pathlib import Path

class OrganizadorImagenes:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Organizador de Imágenes")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        # Variables
        self.carpeta_origen = tk.StringVar()
        self.carpeta_destino = tk.StringVar()
        self.procesando = False
        
        # Extensiones de imagen soportadas
        self.extensiones_imagen = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp', '.svg'}
        
        self.crear_interfaz()
        
    def crear_interfaz(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar el grid para que se expanda
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Selección de carpeta origen
        ttk.Label(main_frame, text="Carpeta origen (imágenes):").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.carpeta_origen, width=50).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        ttk.Button(main_frame, text="Buscar", command=self.seleccionar_origen).grid(row=0, column=2, pady=5, padx=(5, 0))
        
        # Selección de carpeta destino
        ttk.Label(main_frame, text="Carpeta destino:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.carpeta_destino, width=50).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 0))
        ttk.Button(main_frame, text="Buscar", command=self.seleccionar_destino).grid(row=1, column=2, pady=5, padx=(5, 0))
        
        # Separador
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=20)
        
        # Botón de procesamiento
        self.btn_procesar = ttk.Button(main_frame, text="Comenzar Organización", command=self.iniciar_procesamiento)
        self.btn_procesar.grid(row=3, column=0, columnspan=3, pady=10)
        
        # Barra de progreso
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # Área de texto para mostrar progreso y resultados
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        self.texto_log = tk.Text(text_frame, height=15, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.texto_log.yview)
        self.texto_log.configure(yscrollcommand=scrollbar.set)
        
        self.texto_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Instrucciones iniciales
        instrucciones = """Instrucciones de uso:

1. Selecciona la carpeta origen que contiene las imágenes
2. Selecciona la carpeta destino donde se organizarán las imágenes
3. Haz clic en 'Comenzar Organización'

La aplicación procesará las imágenes de la siguiente manera:
- Las imágenes con nombres como 'ejemplo_001.jpg' o 'ejemplo-002.png' se moverán a una carpeta llamada 'ejemplo'
- Se crearán automáticamente las carpetas necesarias en el destino

Extensiones soportadas: JPG, JPEG, PNG, BMP, TIFF, TIF, GIF, WEBP, SVG
"""
        self.texto_log.insert(tk.END, instrucciones)
        self.texto_log.config(state=tk.DISABLED)
        
    def seleccionar_origen(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta origen con imágenes")
        if carpeta:
            self.carpeta_origen.set(carpeta)
            
    def seleccionar_destino(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta destino")
        if carpeta:
            self.carpeta_destino.set(carpeta)
            
    def log_mensaje(self, mensaje):
        self.texto_log.config(state=tk.NORMAL)
        self.texto_log.insert(tk.END, f"\n{mensaje}")
        self.texto_log.see(tk.END)
        self.texto_log.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
    def extraer_nombre_base(self, nombre_archivo):
        # Obtener solo el nombre sin extensión
        nombre_sin_ext = os.path.splitext(nombre_archivo)[0]
        
        # Buscar el último _ o - y tomar todo lo que está antes
        match = re.search(r'^(.+?)[-_]', nombre_sin_ext)
        if match:
            return match.group(1)
        else:
            # Si no hay sufijo, usar el nombre completo sin extensión
            return nombre_sin_ext
            
    def es_imagen(self, archivo):
        return Path(archivo).suffix.lower() in self.extensiones_imagen
        
    def procesar_imagenes(self):
        try:
            origen = self.carpeta_origen.get()
            destino = self.carpeta_destino.get()
            
            if not origen or not destino:
                messagebox.showerror("Error", "Debes seleccionar tanto la carpeta origen como la destino")
                return
                
            if not os.path.exists(origen):
                messagebox.showerror("Error", "La carpeta origen no existe")
                return
                
            if not os.path.exists(destino):
                messagebox.showerror("Error", "La carpeta destino no existe")
                return
                
            self.log_mensaje("=== INICIANDO PROCESAMIENTO ===")
            self.log_mensaje(f"Origen: {origen}")
            self.log_mensaje(f"Destino: {destino}")
            
            # Obtener todas las imágenes en la carpeta origen
            imagenes = []
            for archivo in os.listdir(origen):
                ruta_completa = os.path.join(origen, archivo)
                if os.path.isfile(ruta_completa) and self.es_imagen(archivo):
                    imagenes.append(archivo)
                    
            if not imagenes:
                self.log_mensaje("No se encontraron imágenes en la carpeta origen")
                messagebox.showinfo("Información", "No se encontraron imágenes en la carpeta origen")
                return
                
            self.log_mensaje(f"Se encontraron {len(imagenes)} imágenes para procesar")
            
            # Procesar cada imagen
            procesadas = 0
            errores = 0
            carpetas_creadas = set()
            
            for imagen in imagenes:
                try:
                    nombre_base = self.extraer_nombre_base(imagen)
                    carpeta_destino_final = os.path.join(destino, nombre_base)
                    
                    # Crear carpeta si no existe
                    if not os.path.exists(carpeta_destino_final):
                        os.makedirs(carpeta_destino_final)
                        if nombre_base not in carpetas_creadas:
                            self.log_mensaje(f"Carpeta creada: {nombre_base}")
                            carpetas_creadas.add(nombre_base)
                    
                    # Mover archivo
                    origen_archivo = os.path.join(origen, imagen)
                    destino_archivo = os.path.join(carpeta_destino_final, imagen)
                    
                    # Si el archivo ya existe en destino, generar un nombre único
                    if os.path.exists(destino_archivo):
                        nombre_sin_ext, ext = os.path.splitext(imagen)
                        contador = 1
                        while os.path.exists(destino_archivo):
                            nuevo_nombre = f"{nombre_sin_ext}_{contador}{ext}"
                            destino_archivo = os.path.join(carpeta_destino_final, nuevo_nombre)
                            contador += 1
                        self.log_mensaje(f"Archivo renombrado por duplicado: {imagen} -> {os.path.basename(destino_archivo)}")
                    
                    shutil.move(origen_archivo, destino_archivo)
                    self.log_mensaje(f"Movido: {imagen} -> {nombre_base}/")
                    procesadas += 1
                    
                except Exception as e:
                    self.log_mensaje(f"Error procesando {imagen}: {str(e)}")
                    errores += 1
                    
            # Resumen final
            self.log_mensaje("=== PROCESAMIENTO COMPLETADO ===")
            self.log_mensaje(f"Imágenes procesadas: {procesadas}")
            self.log_mensaje(f"Errores: {errores}")
            self.log_mensaje(f"Carpetas creadas: {len(carpetas_creadas)}")
            
            if errores == 0:
                messagebox.showinfo("Éxito", f"Proceso completado exitosamente!\n{procesadas} imágenes organizadas en {len(carpetas_creadas)} carpetas")
            else:
                messagebox.showwarning("Completado con errores", f"Proceso completado con {errores} errores.\n{procesadas} imágenes procesadas correctamente")
                
        except Exception as e:
            self.log_mensaje(f"Error general: {str(e)}")
            messagebox.showerror("Error", f"Error durante el procesamiento: {str(e)}")
        finally:
            self.procesando = False
            self.progress.stop()
            self.btn_procesar.config(text="Comenzar Organización", state="normal")
            
    def iniciar_procesamiento(self):
        if self.procesando:
            return
            
        self.procesando = True
        self.btn_procesar.config(text="Procesando...", state="disabled")
        self.progress.start()
        
        # Ejecutar en hilo separado para no bloquear la interfaz
        thread = threading.Thread(target=self.procesar_imagenes)
        thread.daemon = True
        thread.start()
        
    def ejecutar(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = OrganizadorImagenes()
    app.ejecutar()