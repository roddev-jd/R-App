import shutil
import threading
import re
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

class ImageValidatorApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Validador de Imágenes")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)
        
        self.selected_directory = tk.StringVar()
        self.dimension_criteria = tk.StringVar(value="1200x1600")
        self.is_processing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Validador de Dimensiones de Imágenes",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(20, 30))
        
        directory_frame = ctk.CTkFrame(main_frame)
        directory_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            directory_frame,
            text="Directorio de búsqueda:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 5))
        
        dir_selection_frame = ctk.CTkFrame(directory_frame)
        dir_selection_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        self.directory_entry = ctk.CTkEntry(
            dir_selection_frame,
            textvariable=self.selected_directory,
            placeholder_text="Selecciona un directorio...",
            height=35,
            font=ctk.CTkFont(size=12)
        )
        self.directory_entry.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=10)
        
        self.browse_button = ctk.CTkButton(
            dir_selection_frame,
            text="Examinar",
            command=self.browse_directory,
            width=100,
            height=35
        )
        self.browse_button.pack(side="right", padx=(5, 10), pady=10)
        
        criteria_frame = ctk.CTkFrame(main_frame)
        criteria_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            criteria_frame,
            text="Criterio de dimensiones:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=(15, 10))
        
        radio_frame = ctk.CTkFrame(criteria_frame)
        radio_frame.pack(pady=(0, 15))
        
        self.radio1 = ctk.CTkRadioButton(
            radio_frame,
            text="1200 x 1600 px",
            variable=self.dimension_criteria,
            value="1200x1600",
            font=ctk.CTkFont(size=12)
        )
        self.radio1.pack(side="left", padx=20, pady=15)
        
        self.radio2 = ctk.CTkRadioButton(
            radio_frame,
            text="1200 x 1200 px",
            variable=self.dimension_criteria,
            value="1200x1200",
            font=ctk.CTkFont(size=12)
        )
        self.radio2.pack(side="left", padx=20, pady=15)
        
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.start_button = ctk.CTkButton(
            control_frame,
            text="Iniciar Proceso",
            command=self.start_validation,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.start_button.pack(pady=20)
        
        progress_frame = ctk.CTkFrame(main_frame)
        progress_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(
            progress_frame,
            text="Progreso:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.pack(fill="x", padx=15, pady=(0, 10))
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text="Listo para comenzar",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=(0, 15))
        
        events_frame = ctk.CTkFrame(main_frame)
        events_frame.pack(fill="both", expand=True, padx=20)
        
        ctk.CTkLabel(
            events_frame,
            text="Registro de eventos:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        self.events_text = ctk.CTkTextbox(
            events_frame,
            height=200,
            font=ctk.CTkFont(size=11)
        )
        self.events_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
    def browse_directory(self):
        directory = filedialog.askdirectory(title="Seleccionar directorio de búsqueda")
        if directory:
            self.selected_directory.set(directory)
            self.log_event(f"Directorio seleccionado: {directory}")
    
    def log_event(self, message):
        self.events_text.insert("end", f"{message}\n")
        self.events_text.see("end")
        self.root.update_idletasks()
    
    def start_validation(self):
        if not self.selected_directory.get():
            messagebox.showerror("Error", "Por favor selecciona un directorio de búsqueda")
            return
        
        if self.is_processing:
            return
        
        self.is_processing = True
        self.start_button.configure(state="disabled", text="Procesando...")
        self.events_text.delete("1.0", "end")
        self.progress_bar.set(0)
        
        thread = threading.Thread(target=self.process_images, daemon=True)
        thread.start()
    
    def process_images(self):
        try:
            base_path = Path(self.selected_directory.get())
            criteria = self.dimension_criteria.get()
            target_width, target_height = map(int, criteria.split('x'))
            
            self.log_event(f"Iniciando validación con criterio: {criteria}")
            self.log_event(f"Buscando imágenes en: {base_path}")
            
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
            all_images = []
            
            for ext in image_extensions:
                all_images.extend(base_path.rglob(f"*{ext}"))
                all_images.extend(base_path.rglob(f"*{ext.upper()}"))
            
            # Filter images with suffixes (_2, -1, -2, etc.)
            filtered_images = []
            suffix_pattern = re.compile(r'[_-]\d+$')
            
            for image_path in all_images:
                filename_without_ext = image_path.stem
                if suffix_pattern.search(filename_without_ext):
                    filtered_images.append(image_path)
                else:
                    self.log_event(f"Omitida (sin sufijo): {image_path.name}")
            
            all_images = filtered_images
            
            total_images = len(all_images)
            self.log_event(f"Encontradas {total_images} imágenes para procesar")
            
            if total_images == 0:
                self.log_event("No se encontraron imágenes en el directorio especificado")
                self.finish_processing()
                return
            
            edit_folder = base_path / "EDITAR"
            non_compliant_images = []
            processed_count = 0
            
            for image_path in all_images:
                try:
                    with Image.open(image_path) as img:
                        width, height = img.size
                        
                    if width != target_width or height != target_height:
                        non_compliant_images.append(image_path)
                        self.log_event(f"Imagen no conforme: {image_path.name} ({width}x{height})")
                    
                except Exception as e:
                    self.log_event(f"Error procesando {image_path.name}: {str(e)}")
                
                processed_count += 1
                progress = processed_count / total_images
                self.root.after(0, lambda p=progress: self.progress_bar.set(p))
                self.root.after(0, lambda: self.status_label.configure(text=f"Procesadas: {processed_count}/{total_images}"))
            
            self.log_event(f"Imágenes no conformes encontradas: {len(non_compliant_images)}")
            
            if non_compliant_images:
                self.log_event("Creando estructura de carpetas y moviendo imágenes...")
                self.move_non_compliant_images(non_compliant_images, edit_folder, base_path)
            
            self.log_event("Proceso completado exitosamente")
            
        except Exception as e:
            self.log_event(f"Error durante el proceso: {str(e)}")
        
        finally:
            self.finish_processing()
    
    def move_non_compliant_images(self, non_compliant_images, edit_folder, base_path):
        edit_folder.mkdir(exist_ok=True)
        
        folder_structure = {}
        
        for image_path in non_compliant_images:
            relative_path = image_path.relative_to(base_path)
            folder_path = relative_path.parent
            
            if folder_path not in folder_structure:
                folder_structure[folder_path] = []
            folder_structure[folder_path].append(image_path)
        
        for folder_path, images in folder_structure.items():
            target_folder = edit_folder / folder_path
            target_folder.mkdir(parents=True, exist_ok=True)
            
            for image_path in images:
                target_file = target_folder / image_path.name
                try:
                    shutil.move(str(image_path), str(target_file))
                    self.log_event(f"Movida: {image_path.name} -> EDITAR/{folder_path}/{image_path.name}")
                except Exception as e:
                    self.log_event(f"Error moviendo {image_path.name}: {str(e)}")
    
    def finish_processing(self):
        self.is_processing = False
        self.root.after(0, lambda: self.start_button.configure(state="normal", text="Iniciar Proceso"))
        self.root.after(0, lambda: self.status_label.configure(text="Proceso completado"))
        self.root.after(0, lambda: self.progress_bar.set(1.0))
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ImageValidatorApp()
    app.run()