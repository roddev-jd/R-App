import os
import requests
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext # Importar scrolledtext
import threading
import queue # Importar queue para comunicación entre hilos
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import random
from PIL import Image
import io

# Deshabilitar advertencias de SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- INICIO DE CAMBIOS PARA EL VISOR DE PROGRESO ---

# 1. Crear una cola (Queue) para comunicar el hilo de descarga con la GUI
log_queue = queue.Queue()

# --- FIN DE CAMBIOS PARA EL VISOR DE PROGRESO ---

# Variable global para almacenar la ruta de la carpeta seleccionada
carpeta_seleccionada = ""

# Lista de User-Agents para rotar y evitar detección
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
]

def hacer_request_con_reintentos(url, headers, max_intentos=3):
    """Realiza requests con reintentos y backoff exponencial"""
    for intento in range(max_intentos):
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=15)
            if response.status_code == 429:  # Too Many Requests
                delay = (2 ** intento) + random.uniform(0, 1)  # Backoff exponencial
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if intento == max_intentos - 1:  # Último intento
                raise e
            time.sleep(2 ** intento)  # Delay antes del siguiente intento
    return None

def validar_imagen(contenido_imagen):
    """Valida que la imagen descargada no esté corrupta"""
    try:
        imagen = Image.open(io.BytesIO(contenido_imagen))
        imagen.verify()  # Verifica la integridad
        return True
    except Exception:
        return False

def seleccionar_carpeta():
    """Abre un diálogo para que el usuario seleccione una carpeta."""
    global carpeta_seleccionada
    ruta = filedialog.askdirectory()
    if ruta:
        carpeta_seleccionada = ruta
        etiqueta_ruta.config(text=f"Guardar en: {carpeta_seleccionada}")
        print(f"Carpeta de destino seleccionada: {carpeta_seleccionada}")

def descargar_imagenes(url, carpeta_destino, nombre_carpeta, q):
    """
    Descarga imágenes y envía el progreso a través de una cola (q).
    """
    try:
        if not carpeta_destino:
            q.put("❌ Error: No se ha seleccionado una carpeta de destino.\n")
            return
        
        if not nombre_carpeta:
            q.put("❌ Error: No se ha especificado un nombre para la carpeta.\n")
            return
        
        # Crear la carpeta con el nombre especificado
        carpeta_final = os.path.join(carpeta_destino, nombre_carpeta)
        os.makedirs(carpeta_final, exist_ok=True)
        q.put(f"📁 Carpeta creada: {carpeta_final}\n")

        q.put(f"ℹ️ Conectando a: {url}...\n")
        headers = {
            'User-Agent': random.choice(user_agents)
        }
        
        # Usar función de reintentos para la página principal
        respuesta = hacer_request_con_reintentos(url, headers)

        soup = BeautifulSoup(respuesta.text, 'html.parser')
        etiquetas_img = soup.find_all('img')

        if not etiquetas_img:
            q.put("ℹ️ No se encontraron imágenes para descargar.\n")
            return

        q.put(f"✅ Se encontraron {len(etiquetas_img)} imágenes. Iniciando descarga con protección anti-rate-limit...\n")
        
        exitos = 0
        for i, img in enumerate(etiquetas_img):
            src = img.get('src')
            if src:
                url_imagen = urljoin(url, src)
                try:
                    q.put(f"   ({i+1}/{len(etiquetas_img)}) Descargando {os.path.basename(url_imagen)}...\n")
                    
                    # Delay entre descargas para evitar rate limiting
                    if i > 0:  # No hacer delay en la primera imagen
                        delay = random.uniform(1, 3)  # Delay aleatorio entre 1-3 segundos
                        time.sleep(delay)
                    
                    # Rotar User-Agent para cada imagen
                    headers['User-Agent'] = random.choice(user_agents)
                    
                    # Usar función de reintentos para descargar imagen
                    respuesta_imagen = hacer_request_con_reintentos(url_imagen, headers, max_intentos=2)
                    if respuesta_imagen is None:
                        q.put(f"   ❌ Error: No se pudo descargar {os.path.basename(url_imagen)} después de varios intentos\n")
                        continue
                    
                    contenido_imagen = respuesta_imagen.content
                    
                    # Validar que la imagen no esté corrupta
                    if not validar_imagen(contenido_imagen):
                        q.put(f"   ⚠️ Imagen corrupta detectada: {os.path.basename(url_imagen)}, omitiendo...\n")
                        continue
                    
                    nombre_base = os.path.basename(url_imagen).split('?')[0]
                    if not nombre_base or len(nombre_base) > 100:
                        extension = os.path.splitext(url_imagen)[1].split('?')[0]
                        nombre_base = f"imagen_{i+1}{extension or '.jpg'}"
                    
                    nombre_imagen = os.path.join(carpeta_final, nombre_base)
                    
                    with open(nombre_imagen, 'wb') as f:
                        f.write(contenido_imagen)
                    
                    # Verificar que el archivo se guardó correctamente
                    if os.path.exists(nombre_imagen) and os.path.getsize(nombre_imagen) > 0:
                        exitos += 1
                        q.put(f"   ✅ Guardado: {os.path.basename(nombre_imagen)}\n")
                    else:
                        q.put(f"   ❌ Error al guardar {os.path.basename(nombre_imagen)}\n")
                        
                except requests.exceptions.Timeout:
                    q.put(f"   ⏱️ Timeout al descargar {os.path.basename(url_imagen)}\n")
                except requests.exceptions.RequestException as e:
                    if "429" in str(e):
                        q.put(f"   🚫 Rate limit detectado para {os.path.basename(url_imagen)}, esperando...\n")
                        time.sleep(5)  # Espera adicional para rate limiting
                    else:
                        q.put(f"   ❌ Error de conexión: {os.path.basename(url_imagen)}: {e}\n")
                except Exception as e:
                    q.put(f"   ❌ Error inesperado: {os.path.basename(url_imagen)}: {e}\n")
        
        if exitos > 0:
            q.put(f"\n🎉 ¡Descarga Finalizada! Se guardaron {exitos} de {len(etiquetas_img)} imágenes exitosamente.\n")
        else:
            q.put(f"\n⚠️ Descarga terminada pero no se pudo guardar ninguna imagen. Verifica la conexión y la URL.\n")

    except requests.exceptions.RequestException as e:
        if "429" in str(e):
            q.put(f"🚫 Error 429: El servidor está limitando las peticiones. Intenta más tarde.\n")
        elif "403" in str(e):
            q.put(f"🚫 Error 403: Acceso prohibido. El sitio puede estar bloqueando el scraping.\n")
        elif "404" in str(e):
            q.put(f"🔍 Error 404: Página no encontrada. Verifica la URL.\n")
        else:
            q.put(f"❌ Error de conexión: {e}\n")
    except Exception as e:
        q.put(f"❌ Error inesperado: {e}\n")
    finally:
        # Enviamos un mensaje especial para reactivar los botones
        q.put("DOWNLOAD_COMPLETE")
        q.put(f"\n📊 Estadísticas finales: {exitos if 'exitos' in locals() else 0} imágenes descargadas correctamente.\n")

def iniciar_descarga_thread():
    """Valida la entrada y ejecuta la descarga en un hilo separado."""
    url = entrada_url.get()
    nombre_carpeta = entrada_nombre_carpeta.get().strip()
    
    if not url.startswith(('http://', 'https://')):
        messagebox.showerror("Entrada Inválida", "Por favor, introduce una URL válida.")
        return
    
    if not nombre_carpeta:
        messagebox.showerror("Entrada Inválida", "Por favor, introduce un nombre para la carpeta.")
        return

    if not carpeta_seleccionada:
        messagebox.showerror("Entrada Inválida", "Por favor, selecciona una carpeta de destino primero.")
        return

    # Limpiar el visor de logs antes de empezar
    log_viewer.config(state=tk.NORMAL)
    log_viewer.delete('1.0', tk.END)
    log_viewer.config(state=tk.DISABLED)

    # Desactivar botones para evitar descargas múltiples
    boton_descargar.config(state=tk.DISABLED)
    boton_seleccionar.config(state=tk.DISABLED)

    # Inicia la descarga en un hilo, pasando la cola de logs como argumento
    thread = threading.Thread(target=descargar_imagenes, args=(url, carpeta_seleccionada, nombre_carpeta, log_queue))
    thread.start()

def procesar_log_queue():
    """
    Revisa la cola en busca de nuevos mensajes y los añade al visor de texto.
    """
    try:
        while True:
            mensaje = log_queue.get_nowait()
            if mensaje == "DOWNLOAD_COMPLETE":
                # Reactivar botones cuando la descarga termina
                boton_descargar.config(state=tk.NORMAL)
                boton_seleccionar.config(state=tk.NORMAL)
            else:
                # Insertar mensaje en el visor
                log_viewer.config(state=tk.NORMAL)
                log_viewer.insert(tk.END, mensaje)
                log_viewer.see(tk.END) # Auto-scroll hacia el final
                log_viewer.config(state=tk.DISABLED)
    except queue.Empty:
        pass  # Si la cola está vacía, no hace nada
    
    # Se llama a sí misma cada 100ms para seguir revisando la cola
    ventana.after(100, procesar_log_queue)

# --- Creación de la Interfaz Gráfica (GUI) con Tkinter ---
ventana = tk.Tk()
ventana.title("Descargador de Imágenes Web")
ventana.geometry("700x550") # Aumentamos el tamaño de la ventana

# --- Widgets de entrada (URL y Carpeta) ---
frame_controles = tk.Frame(ventana)
frame_controles.pack(pady=10, padx=10, fill="x")

tk.Label(frame_controles, text="1. Pega la URL del sitio web:", font=("Arial", 12)).pack()
entrada_url = tk.Entry(frame_controles, width=80, font=("Arial", 10))
entrada_url.pack(pady=(5, 15), ipady=4)

tk.Label(frame_controles, text="2. Nombre de la carpeta a crear:", font=("Arial", 12)).pack()
entrada_nombre_carpeta = tk.Entry(frame_controles, width=80, font=("Arial", 10))
entrada_nombre_carpeta.pack(pady=(5, 15), ipady=4)

tk.Label(frame_controles, text="3. Selecciona dónde guardar las imágenes:", font=("Arial", 12)).pack()
boton_seleccionar = tk.Button(frame_controles, text="Seleccionar Carpeta", command=seleccionar_carpeta, font=("Arial", 10))
boton_seleccionar.pack(pady=5)
etiqueta_ruta = tk.Label(frame_controles, text="Destino: (Ninguna carpeta seleccionada)", font=("Arial", 9), fg="grey")
etiqueta_ruta.pack()

# --- Botón de descarga ---
boton_descargar = tk.Button(ventana, text="4. Iniciar Descarga", command=iniciar_descarga_thread, font=("Arial", 12, "bold"), bg="#4CAF50", fg="white")
boton_descargar.pack(pady=15, ipady=5, ipadx=10)

# --- Visor de Progreso (Log Viewer) ---
tk.Label(ventana, text="Progreso de la Descarga:", font=("Arial", 12)).pack()
log_viewer = scrolledtext.ScrolledText(ventana, height=12, width=80, state=tk.DISABLED, wrap=tk.WORD, font=("Consolas", 9))
log_viewer.pack(pady=10, padx=10, expand=True, fill="both")


# Iniciar el proceso que revisa la cola de logs
procesar_log_queue()

# Iniciar el bucle principal de la aplicación
ventana.mainloop()