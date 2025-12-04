#!/usr/bin/env python3
import shutil
import re
import tkinter as tk # Keep for StringVars etc.
import ttkbootstrap as ttk # Import ttkbootstrap
from ttkbootstrap.constants import * # Import constants like BOTH, W, READONLY
from tkinter import filedialog, messagebox # Keep standard dialogs
from pathlib import Path
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

class ImageInserterApp(ttk.Window): # Inherit from ttk.Window
    def __init__(self):
        super().__init__()
        setup_theme(self)
        self.title("Añadir Imágenes a Carpetas con Sufijos (ttkbootstrap)")
        self.geometry("800x230") # Slightly wider for better spacing with ttkbootstrap widgets
        self.resizable(False, False)

        # Variables
        self.root_folder = tk.StringVar()
        self.images_var = tk.StringVar() # To display selected image names
        self.images_paths = [] # List of Path objects for selected images

        # Main frame using ttk.Frame
        # ttk.Frame uses 'padding' argument directly, not padx/pady for its own padding.
        # Child widgets will use padx/pady in their grid/pack calls.
        frm = ttk.Frame(self, padding=15)
        frm.pack(fill=BOTH, expand=True)

        # Configure grid column weights for responsiveness of entries if window were resizable
        frm.columnconfigure(1, weight=1)


        # --- Row 0: Selección de carpeta raíz ---
        ttk.Label(frm, text="Carpeta raíz (contiene subcarpetas):").grid(row=0, column=0, sticky=W, padx=(0, 5), pady=5)
        # Entry width is character-based, might need adjustment or rely on grid expansion
        ttk.Entry(frm, textvariable=self.root_folder, width=50, state=READONLY).grid(row=0, column=1, sticky=EW, padx=5, pady=5)
        ttk.Button(frm, text="Seleccionar carpeta raíz...", command=self.select_root_folder, bootstyle="outline-secondary").grid(row=0, column=2, sticky=EW, padx=5, pady=5)

        # --- Row 1: Selección de imágenes nuevas ---
        ttk.Label(frm, text="Imágenes nuevas:").grid(row=1, column=0, sticky=W, padx=(0, 5), pady=(10,5))
        ttk.Entry(frm, textvariable=self.images_var, width=50, state=READONLY).grid(row=1, column=1, sticky=EW, padx=5, pady=(10,5))
        ttk.Button(frm, text="Seleccionar imágenes...", command=self.select_images, bootstyle="outline-secondary").grid(row=1, column=2, sticky=EW, padx=5, pady=(10,5))

        # --- Row 2: Botón de acción ---
        # Use a sub-frame for centering the button or just grid it with columnspan
        action_button_frame = ttk.Frame(frm) # Optional: for better control if more buttons were added
        action_button_frame.grid(row=2, column=0, columnspan=3, pady=20)

        ttk.Button(action_button_frame, text="Agregar Imágenes", command=self.process_images, bootstyle="success", width=25).pack()
        # Alternative without sub-frame (might need column configuration on `frm` for centering):
        # ttk.Button(frm, text="Agregar Imágenes", command=self.process_images, bootstyle="success", width=20).grid(row=2, column=1, pady=20, sticky="ew")


    def select_root_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.root_folder.set(path)

    def select_images(self):
        paths = filedialog.askopenfilenames(
            title="Seleccionar Imágenes Nuevas", # Added title for clarity
            filetypes=[('Imágenes', '*.png *.jpg *.jpeg *.webp *.bmp *.gif')] # Added gif
        )
        if paths:
            self.images_paths = list(map(Path, paths))
            names = [p.name for p in self.images_paths]
            # Limit displayed names if too many, for better UI
            if len(names) > 3:
                display = ", ".join(names[:3]) + f"... ({len(names) - 3} más)"
            else:
                display = ", ".join(names)
            self.images_var.set(display)

    def process_images(self):
        root_str = self.root_folder.get()
        if not root_str or not self.images_paths:
            messagebox.showwarning("Faltan datos", "Seleccione la carpeta raíz y al menos una imagen nueva.")
            return
        
        root_path = Path(root_str)
        errors = []
        success_count = 0

        # Disable button during processing
        # Assuming the button is the first widget in action_button_frame or accessed directly
        process_btn = self.winfo_children()[-1].winfo_children()[0] # This is a bit fragile; better to store a reference
        # Let's store a reference to the button in __init__ if we want to disable it.
        # For now, skipping button disable as it wasn't explicitly requested for this app's refactor.

        for new_image_path in self.images_paths:
            try:
                self._insert_image(root_path, new_image_path)
                success_count += 1
            except Exception as e:
                errors.append(f"Error con '{new_image_path.name}': {e}")

        if errors:
            error_summary = f"Procesadas {success_count} imágenes con éxito.\n"
            error_summary += "Se produjeron errores en algunas imágenes:\n" + "\n".join(errors)
            messagebox.showerror("Errores al procesar", error_summary)
        elif success_count > 0 : # Only show success if any image was processed
            messagebox.showinfo("Éxito", f"Todas las {success_count} imágenes seleccionadas han sido agregadas y los sufijos actualizados.")
        else: # No images processed (e.g., paths list was cleared somehow after selection)
             messagebox.showinfo("Información", "No se procesaron imágenes.")

        # Clear selection after processing for next batch
        self.images_paths = []
        self.images_var.set("")


    def _insert_image(self, root_folder: Path, new_image_path: Path):
        # Logic from here onwards is preserved as it's backend processing
        new_stem = new_image_path.stem
        new_ext = new_image_path.suffix.lower() # Normalize extension to lowercase for matching

        # Regex updated for flexibility: allows for no initial number, e.g. IMG.jpg -> IMG_2.jpg or IMG-1.jpg
        # And handles cases like IMG_01.jpg or IMG-01.jpg
        # Match pattern like "basename", "basename_1", "basename-1"
        # Group 1: root_name (e.g., "image")
        # Group 2: optional separator and number (e.g., "_1" or "-1")
        # Group 3: separator itself (e.g., "_" or "-")
        # Group 4: number string (e.g., "1")
        match_new_name = re.match(r"^(.*?)(([_-])(\d+))?$", new_stem)
        if not match_new_name: # Should not happen with this broad regex, but as a safeguard
            raise ValueError(f"Nombre de imagen '{new_stem}' no sigue un patrón reconocible.")

        root_name = match_new_name.group(1)
        current_sep_num_part = match_new_name.group(2) # e.g., "_1" or "-1" or None
        
        if not root_name: # Handle cases where image name might be just "_1.jpg" (unlikely but defensive)
            raise ValueError("El nombre base de la imagen no puede estar vacío.")

        # Determine the 'insertion_pos' based on the new image's suffix
        # If new image is "file_3.jpg", insertion_pos is 2 (0-indexed). New file becomes "file_2.jpg".
        # If new image is "file-3.jpg", insertion_pos is 3 (1-indexed for "-"). New file becomes "file-3.jpg".
        # The logic here defines how the NEW image's number determines its placement and renaming.
        # This part seems complex and specific to the original app's intent.
        # Let's re-evaluate based on the original code's apparent intention for m_new:
        # m_new = re.match(r"^(.*?)((?:_|-)(\d+))$", new_stem) was mandatory.
        # It implied the new image already has a suffix like "_N" or "-N".

        m_new_strict = re.match(r"^(.*?)((_|-)(\d+))$", new_stem)
        if not m_new_strict:
            raise ValueError(f"Formato de nombre de imagen nueva '{new_image_path.name}' inválido: debe contener sufijo '_n' o '-n' (ej: imagen_1.jpg, foto-3.webp).")
        
        # root_name is the part before _n or -n
        root_name_for_folder = m_new_strict.group(1)
        sep_new = m_new_strict.group(3) # '_' or '-'
        num_new = int(m_new_strict.group(4)) # number from new image

        # Original logic for insertion_pos:
        # insertion_pos = num - 1 if sep == '_' else num + 1
        # This defines the "slot" number.
        # If new image is "file_3.jpg", sep='_', num=3 -> insertion_pos = 2.
        # If new image is "file-3.jpg", sep='-', num=3 -> insertion_pos = 4. (This seems off, original had num+1)
        # Let's stick to original interpretation:
        # '_' suffix is 0-indexed for slots (file_1 is slot 0, file_2 is slot 1)
        # '-' suffix is 1-indexed for slots (file-1 is slot 1, file-2 is slot 2)
        # The new image NAME (e.g. file_X or file-X) determines where it *logically* goes.

        # Let's use the new image's name to determine its *intended* final suffix based on its number
        # This is the suffix the NEW image will have after insertion.
        # The original code directly used the new image's name as the destination:
        # dest = folder_path / new_image_path.name
        # So, the number in the new image's name is its *final* number.
        # And insertion_pos is the slot *before* which other files might need to shift.

        # Slot for the new image:
        # if new_image_name is "base_N.ext", its slot is N-1.
        # if new_image_name is "base-N.ext", its slot is N.
        target_slot_of_new_image = (num_new - 1) if sep_new == '_' else num_new

        folder_path = root_folder / root_name_for_folder
        if not folder_path.exists() or not folder_path.is_dir():
            raise FileNotFoundError(f"No existe la subcarpeta '{root_name_for_folder}' en '{root_folder}'.")

        files_to_rename = []
        for existing_file_path in folder_path.iterdir():
            if not existing_file_path.is_file():
                continue
            
            # Only process files with the same root name and extension (case-insensitive for extension)
            if existing_file_path.stem.startswith(root_name_for_folder) and existing_file_path.suffix.lower() == new_ext:
                # Check if it's the plain root name (e.g. "image.jpg")
                if existing_file_path.stem == root_name_for_folder:
                    # This is the "base" image, slot 0 (becomes _2 or -1 depending on convention)
                    current_slot = 0 
                else:
                    # Check for "root_name_N.ext" or "root_name-N.ext"
                    m_old = re.match(rf"^{re.escape(root_name_for_folder)}(_|-)(\d+)$", existing_file_path.stem)
                    if m_old:
                        sep_old = m_old.group(1)
                        num_old = int(m_old.group(2))
                        current_slot = (num_old - 1) if sep_old == '_' else num_old
                    else:
                        continue # Not a parsable suffixed file, skip

                # If this existing file is at or after the target slot of the new image, it needs to be shifted
                if current_slot >= target_slot_of_new_image:
                    files_to_rename.append({'path': existing_file_path, 'current_slot': current_slot})
        
        # Sort files to be renamed by their current slot in descending order to avoid overwriting
        files_to_rename.sort(key=lambda x: x['current_slot'], reverse=True)

        for file_info in files_to_rename:
            file_path = file_info['path']
            # New slot is one greater than its current slot
            shifted_slot = file_info['current_slot'] + 1 
            
            # Determine new suffix based on convention: slot 0 -> "_1", slot 1 -> "_2", slot 2 -> "-2", slot 3 -> "-3"
            # This differs from the original simpler "_2" or "-N-1".
            # Let's follow the original simple suffix logic for renaming existing files:
            # new_pos = pos_old + 1 (where pos_old was their interpretation of slot)
            # new_suffix = "_2" if new_pos == 1 else f"-{new_pos-1}"
            # To map `shifted_slot` to this logic:
            # If shifted_slot = 0 (e.g. original base image moving), it can't happen with >= target_slot logic, unless target_slot is 0.
            # If target_slot_of_new_image = 0 (e.g. new image is "basename_1.jpg"):
            #   - existing "basename.jpg" (current_slot=0) -> shifted_slot=1. New suffix for it: original used `pos_old=0` for base, `new_pos=1`, so `_2`.
            #   - existing "basename_2.jpg" (current_slot=1) -> shifted_slot=2. New suffix for it: original used `pos_old=1`, `new_pos=2`, so `-1` (2-1).
            # This implies pos_old was what I'm calling current_slot.
            
            # Simpler: the new name for the file being shifted. Its new number is its (current_slot + 1).
            # Let's use a unified numbering: slot 0 (_1), slot 1 (_2), slot 2 (_3), ...
            # Then convert this unified slot number back to _N or -N for the actual filename.
            # This is getting too complex by deviating. Sticking to original for shifted files:
            # The *new suffix* for the file being shifted (file_path) due to its pos_old (current_slot) incrementing.
            # new_suffix_for_shifted_file:
            # if current_slot + 1 == 0 (this would mean current_slot was -1, not possible)
            # if current_slot + 1 == 1 (i.e. current_slot was 0, the base image): it becomes _2
            # if current_slot + 1 > 1: it becomes -( (current_slot+1) -1 ) = -(current_slot)
            
            # Original logic re-applied for shifted files:
            # pos_old was the "effective" number based on their rule.
            # Let's recalculate pos_old for existing file before shifting:
            # if file_path.stem == root_name_for_folder: effective_num_old_for_suffix = 1 (_1 equivalent)
            # else: (it has _N or -N)
            #   m = re.match(rf"^{re.escape(root_name_for_folder)}(_|-)(\d+)$", file_path.stem)
            #   sep = m.group(1)
            #   num = int(m.group(2))
            #   effective_num_old_for_suffix = num if sep == '_' else num + 1 # This was the original interpretation of pos_old

            # The problem is "pos_old" in the original code used file_path, sep_old, num_old to derive it.
            # Let's use `current_slot` from my calculation.
            # The shifted file will occupy `current_slot + 1`.
            # What is the name for slot `s`?
            # Slot 0: name is root_name + _1 + ext
            # Slot 1: name is root_name + _2 + ext
            # ...
            # This is one convention. The original has a mixed convention.
            # Original renaming:
            # new_pos_for_shifted = current_slot + 1 + 1 (because their pos_old was 0 for _1, 1 for _2, 2 for -1, 3 for -2)
            # No, original was simpler:
            # pos_old = num_old - 1 if sep_old == '_' else num_old + 1
            # target_num_for_shifted = pos_old + 1
            # final_suffix_for_shifted = "_2" if target_num_for_shifted == 1 else f"-{target_num_for_shifted-1}"
            
            # Let's stick to the original renaming logic for the files being shifted:
            # What was the `pos_old` of the file at `file_path`?
            # This needs careful re-mapping to the original `pos_old` definition.

            # For the file `file_path` (which is `existing_file_path`):
            stem_to_parse = file_path.stem
            if stem_to_parse == root_name_for_folder: # It's the base "image.jpg"
                # Original code didn't seem to handle shifting "image.jpg" to "image_2.jpg" explicitly this way.
                # It assumed files to rename already had _N or -N.
                # If image.jpg (no suffix) exists, its "pos_old" effectively is 0 by their example (image_2 is pos 1).
                # Let's assume base "image.jpg" is equivalent to "image_1.jpg" for numbering. So num_old=1, sep_old='_'.
                original_pos_old_equivalent = 0 # (1-1)
            else:
                m_existing = re.match(rf"^{re.escape(root_name_for_folder)}(_|-)(\d+)$", stem_to_parse)
                if not m_existing: continue # Should not happen if already filtered
                sep_existing = m_existing.group(1)
                num_existing = int(m_existing.group(2))
                original_pos_old_equivalent = (num_existing - 1) if sep_existing == '_' else (num_existing + 1)

            # Now, this file is shifted one position up.
            target_pos_for_shifted_file = original_pos_old_equivalent + 1
            
            # Determine the new suffix string based on the original app's convention
            if target_pos_for_shifted_file == 1: # This means it should become `_2`
                new_suffix_str = "_2"
            else: # Becomes `-N` where N is target_pos-1
                new_suffix_str = f"-{target_pos_for_shifted_file - 1}"
            
            target_rename_path = folder_path / f"{root_name_for_folder}{new_suffix_str}{new_ext}"
            
            # Avoid renaming to itself if somehow the logic leads to it (defensive)
            if file_path == target_rename_path:
                continue
            # Handle potential overwrite if target_rename_path is the new_image_path.name (shouldn't happen if new image has unique suffix)
            if target_rename_path.name == new_image_path.name and target_rename_path.parent == folder_path:
                 print(f"Skipping rename of {file_path.name} to avoid conflict with new image name {new_image_path.name}") # Or raise error
                 continue


            print(f"Renaming: {file_path.name} (slot_eq: {original_pos_old_equivalent}) -> {target_rename_path.name} (target_pos: {target_pos_for_shifted_file})")
            file_path.rename(target_rename_path)


        # Copiar la nueva imagen a su nombre final (que ya está definido por new_image_path.name)
        destination_for_new_image = folder_path / new_image_path.name
        
        # Check if the destination for the new image is one of the paths a file was just renamed FROM.
        # This can happen if the new image is named like an existing file that was shifted.
        # Example: existing is "f_2.jpg". New image is "f_2.jpg".
        # "f_2.jpg" is shifted to "f-1.jpg". Then "f_2.jpg" is copied. This is okay.
        # Example: existing is "f_2.jpg", "f_3.jpg". New image is "f_2.jpg".
        # "f_3.jpg" -> "f-2.jpg"
        # "f_2.jpg" -> "f-1.jpg"
        # Copy new "f_2.jpg". Okay.

        # Prevent overwriting if the exact file name we want to copy to *still* exists
        # (e.g. if a rename failed or was skipped, and it's not the file being renamed FROM)
        if destination_for_new_image.exists():
            # This means a file with the *exact same name* as the new image
            # is already in the target folder and was NOT one of the files_to_rename
            # OR a rename failed and the original file is still there.
            # This is a conflict.
            raise FileExistsError(f"Un archivo llamado '{destination_for_new_image.name}' ya existe en la carpeta destino y no pudo ser renombrado o es un archivo no relacionado.")

        shutil.copy2(new_image_path, destination_for_new_image)
        print(f"Copiado: {new_image_path.name} a {destination_for_new_image}")


if __name__ == '__main__':
    app = ImageInserterApp()
    app.mainloop()