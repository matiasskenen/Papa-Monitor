import psutil
import requests
import time
import os
import sys
import threading
import msvcrt  # Para bloquear instancia en Windows
from pystray import Icon, Menu, MenuItem
import pystray
from PIL import Image, ImageDraw

# ==========================================
# CONFIGURACIÓN
# ==========================================
API_URL = "https://papa-monitor.vercel.app/api/status"
VERSION_URL = "https://papa-monitor.vercel.app/version.txt"
CURRENT_VERSION = "1.0.0"
PROCESS_NAME = "chrome.exe"
APP_NAME = "PapaMonitor"

def resource_path(relative_path):
    """ Encuentra archivos internos para el .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def instancia_unica():
    """ Evita que el programa se abra más de una vez """
    lock_file = os.path.join(os.getenv('TEMP'), 'papa_monitor.lock')
    try:
        # Intentamos crear/abrir el archivo y bloquearlo
        fp = open(lock_file, 'w')
        msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
        return fp # Retornamos el puntero para mantener el bloqueo vivo
    except IOError:
        return None

class FortniteMonitor:
    def __init__(self):
        self.running = True
        self.icon = None
        self.is_online = False

    def check_for_updates(self):
        """ Revisa versión en Vercel """
        try:
            r = requests.get(VERSION_URL, timeout=5)
            if r.status_code == 200:
                remote_version = r.text.strip()
                if remote_version > CURRENT_VERSION:
                    print(f"Update disponible: {remote_version}")
        except:
            pass

    def create_icon_image(self):
        """ Carga logo o genera uno de emergencia """
        try:
            return Image.open(resource_path("logo.png"))
        except:
            img = Image.new('RGB', (64, 64), (20, 20, 20))
            d = ImageDraw.Draw(img)
            d.ellipse((16, 16, 48, 48), fill=(0, 120, 215))
            return img

    def monitor_logic(self):
        """ Bucle de detección y envío a API """
        print("Monitor de fondo iniciado...")
        while self.running:
            # Detección del proceso
            current_status = any(p.info['name'] == PROCESS_NAME for p in psutil.process_iter(['name']))
            
            # Solo mandamos POST si cambia el estado o si sigue online (heartbeat)
            if current_status != self.is_online or current_status:
                self.is_online = current_status
                try:
                    requests.post(API_URL, json={"is_online": self.is_online}, timeout=10)
                except:
                    pass
            
            time.sleep(60)

    def on_quit(self, icon):
        self.running = False
        icon.stop()
        os._exit(0)

    def run(self):
        self.check_for_updates()

        # Menú interactivo
        menu = Menu(
            MenuItem(f"PapaMonitor v{CURRENT_VERSION}", lambda: None, enabled=False),
            MenuItem("Ver Estado", lambda: os.system(f'msg * "Online: {self.is_online}"')),
            MenuItem("Reparar / Actualizar", lambda: os.system('msg * "Buscando actualizaciones..."')),
            pystray.Menu.SEPARATOR,
            MenuItem("Cerrar Programa", self.on_quit)
        )

        self.icon = Icon(APP_NAME, self.create_icon_image(), "Tracker de Papá", menu)

        # Hilo de escaneo
        thread = threading.Thread(target=self.monitor_logic, daemon=True)
        thread.start()

        # Ejecución del Tray
        self.icon.run()

if __name__ == "__main__":
    lock = instancia_unica()
    if not lock:
        os.system('msg * "El monitor ya está abierto al lado del reloj."')
        sys.exit(0)
        
    monitor = FortniteMonitor()
    monitor.run()