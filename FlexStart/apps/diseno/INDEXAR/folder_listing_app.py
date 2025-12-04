import os
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from config import UI_CONFIG, EXCEL_CONFIG, PROCESSING_CONFIG, MESSAGES

class FolderListingApp:
    def __init__(self):
        # Configurar CustomTkinter
        ctk.set_appearance_mode(UI_CONFIG["theme"])
        ctk.set_default_color_theme(UI_CONFIG["color_theme"])
        
        # Crear ventana principal
        self.root = ctk.CTk()
        self.root.title(UI_CONFIG["window_title"])
        self.root.geometry(UI_CONFIG["window_size"])
        self.root.resizable(True, True)
        
        # Variables
        self.selected_directory = ctk.StringVar()
        self.output_filename = ctk.StringVar(value=EXCEL_CONFIG["default_filename"])
        
        self.setup_ui()
        
    def setup_ui(self):
        """Configurar la interfaz de usuario"""
        # Frame principal
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Listador de Carpetas", 
            font=ctk.CTkFont(size=UI_CONFIG["font_size_title"], weight="bold")
        )
        title_label.pack(pady=(20, 30))
        
        # Frame para selección de directorio
        dir_frame = ctk.CTkFrame(main_frame)
        dir_frame.pack(fill="x", padx=20, pady=10)
        
        dir_label = ctk.CTkLabel(dir_frame, text="Directorio a listar:", font=ctk.CTkFont(size=UI_CONFIG["font_size_normal"]))
        dir_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Frame para entrada y botón
        input_frame = ctk.CTkFrame(dir_frame)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.dir_entry = ctk.CTkEntry(
            input_frame, 
            textvariable=self.selected_directory,
            placeholder_text="Selecciona un directorio...",
            height=35
        )
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = ctk.CTkButton(
            input_frame,
            text="Examinar",
            command=self.browse_directory,
            width=100,
            height=35
        )
        browse_btn.pack(side="right")
        
        # Frame para nombre del archivo
        filename_frame = ctk.CTkFrame(main_frame)
        filename_frame.pack(fill="x", padx=20, pady=10)
        
        filename_label = ctk.CTkLabel(filename_frame, text="Nombre del archivo Excel:", font=ctk.CTkFont(size=UI_CONFIG["font_size_normal"]))
        filename_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.filename_entry = ctk.CTkEntry(
            filename_frame,
            textvariable=self.output_filename,
            placeholder_text=EXCEL_CONFIG["default_filename"],
            height=35
        )
        self.filename_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # Botón de procesamiento
        process_btn = ctk.CTkButton(
            main_frame,
            text="Generar Lista de Carpetas",
            command=self.process_folders,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        process_btn.pack(pady=20)
        
        # Área de información
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        info_label = ctk.CTkLabel(
            info_frame, 
            text="Información:",
            font=ctk.CTkFont(size=UI_CONFIG["font_size_normal"], weight="bold")
        )
        info_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        self.info_text = ctk.CTkTextbox(
            info_frame,
            height=120,
            font=ctk.CTkFont(size=UI_CONFIG["font_size_small"])
        )
        self.info_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
    def browse_directory(self):
        """Abrir diálogo para seleccionar directorio"""
        directory = filedialog.askdirectory(
            title=MESSAGES["select_directory"]
        )
        if directory:
            self.selected_directory.set(directory)
            self.update_info(f"Directorio seleccionado: {directory}")
            
    def update_info(self, message):
        """Actualizar área de información"""
        self.info_text.insert("end", f"{message}\n")
        self.info_text.see("end")
        
    def process_folders(self):
        """Procesar las carpetas y generar Excel"""
        directory = self.selected_directory.get()
        
        if not directory:
            messagebox.showerror(MESSAGES["error_title"], MESSAGES["no_directory_selected"])
            return
            
        if not os.path.exists(directory):
            messagebox.showerror(MESSAGES["error_title"], MESSAGES["directory_not_exists"])
            return
            
        try:
            # Obtener lista de carpetas
            folders = self.get_folders_from_directory(directory)
            
            if not folders:
                messagebox.showwarning(MESSAGES["warning_title"], MESSAGES["no_folders_found"])
                return
                
            # Crear DataFrame
            df = self.create_dataframe(folders)
            
            # Generar archivo Excel
            output_path = self.save_excel_file(directory, df)
            
            self.update_info(f"Proceso completado exitosamente!")
            self.update_info(f"Archivo guardado en: {output_path}")
            self.update_info(f"Total de carpetas listadas: {len(folders)}")
            
            messagebox.showinfo(
                MESSAGES["success_title"], 
                f"{MESSAGES['success_message']}\nUbicación: {output_path}\nTotal de carpetas: {len(folders)}"
            )
            
        except Exception as e:
            error_msg = f"{MESSAGES['process_error']}: {str(e)}"
            self.update_info(error_msg)
            messagebox.showerror(MESSAGES["error_title"], error_msg)
            
    def get_folders_from_directory(self, directory):
        """Obtener lista de carpetas del directorio"""
        folders = []
        
        try:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                    
        except PermissionError:
            raise Exception(MESSAGES["permission_error"])
        except Exception as e:
            raise Exception(f"{MESSAGES['read_error']}: {str(e)}")
            
        if PROCESSING_CONFIG["sort_folders"]:
            return sorted(folders)
        return folders
        
    def create_dataframe(self, folders):
        """Crear DataFrame con las carpetas"""
        # Crear lista de números SKU (simulando números de producto)
        sku_numbers = []
        for i, folder in enumerate(folders, start=1):
            if PROCESSING_CONFIG["extract_numbers_from_names"]:
                # Intentar extraer números del nombre de la carpeta
                numbers = ''.join(filter(str.isdigit, folder))
                if numbers:
                    sku_numbers.append(int(numbers))
                elif PROCESSING_CONFIG["use_sequential_numbers"]:
                    # Si no hay números, usar un número secuencial
                    sku_numbers.append(i)
                else:
                    sku_numbers.append(0)  # Valor por defecto
            else:
                sku_numbers.append(i)
                
        # Crear DataFrame solo con la columna SKU
        df = pd.DataFrame({
            EXCEL_CONFIG["sku_column_name"]: sku_numbers
        })
        
        return df
        
    def save_excel_file(self, directory, df):
        """Guardar DataFrame como archivo Excel"""
        filename = self.output_filename.get()
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
            
        output_path = os.path.join(directory, filename)
        
        # Crear writer de Excel
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=EXCEL_CONFIG["sheet_name"], index=False)
            
            # Obtener el workbook y worksheet
            workbook = writer.book
            worksheet = writer.sheets[EXCEL_CONFIG["sheet_name"]]
            
            # Formatear la columna SKU como números
            for row in range(2, len(df) + 2):  # Empezar desde la fila 2 (después del header)
                cell = worksheet.cell(row=row, column=1)
                cell.number_format = EXCEL_CONFIG["number_format"]  # Formato de número entero
                
        return output_path
        
    def run(self):
        """Ejecutar la aplicación"""
        self.root.mainloop()

if __name__ == "__main__":
    app = FolderListingApp()
    app.run() 