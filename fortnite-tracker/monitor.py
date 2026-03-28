import psutil
import requests
import time
import os
import sys
import threading
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

# ==========================================
# CONFIGURACIÓN (Ajustá esto con tu URL)
# ==========================================
API_URL = "https://papa-monitor.vercel.app/api/status"
VERSION_URL = "https://papa-monitor.vercel.app/version.txt"
CURRENT_VERSION = "1.0.0"
PROCESS_NAME = "chrome.exe"
APP_NAME = "PapaMonitor"

def resource_path(relative_path):
    """ Función para encontrar archivos internos cuando es un .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FortniteMonitor:
    def __init__(self):
        self.running = True
        self.icon = None

    def check_for_updates(self):
        """ Revisa si en Vercel hay una versión más nueva """
        try:
            r = requests.get(VERSION_URL, timeout=5)
            if r.status_code == 200:
                remote_version = r.text.strip()
                if remote_version > CURRENT_VERSION:
                    print(f"Nueva versión disponible: {remote_version}")
                    # Acá podrías disparar un aviso o descarga
        except:
            pass

    def create_icon_image(self):
        """ Carga el logo.png o crea un círculo de emergencia si falla """
        try:
            # Intenta cargar el logo que pusimos en el comando --add-data
            return Image.open(resource_path("logo.png"))
        except:
            # Si no hay imagen, dibuja un círculo azul
            img = Image.new('RGB', (64, 64), (20, 20, 20))
            d = ImageDraw.Draw(img)
            d.ellipse((16, 16, 48, 48), fill=(0, 120, 215))
            return img

    def monitor_logic(self):
        """ Bucle principal que detecta el proceso y avisa a la API """
        print("Monitoreo iniciado...")
        while self.running:
            # Se fija si el proceso está en la lista de Windows
            is_online = any(p.info['name'] == PROCESS_NAME for p in psutil.process_iter(['name']))
            
            try:
                # Envía el estado a tu Vercel
                requests.post(API_URL, json={"is_online": is_online}, timeout=10)
            except Exception as e:
                print(f"Error de conexión: {e}")
            
            # Espera 1 minuto antes de volver a chequear
            time.sleep(60)

    def on_quit(self, icon):
        """ Cierra el programa por completo """
        self.running = False
        icon.stop()
        os._exit(0)

    def run(self):
        """ Configura el Tray Icon y arranca los hilos """
        self.check_for_updates()

        # Menú del ícono al lado del reloj
        menu = Menu(
            MenuItem(f"Monitor v{CURRENT_VERSION}", lambda: None, enabled=False),
            MenuItem("Cerrar Programa", self.on_quit)
        )

        self.icon = Icon(APP_NAME, self.create_icon_image(), "Tracker de Papá", menu)

        # Lanzamos el monitoreo en un hilo separado para no trabar el ícono
        thread = threading.Thread(target=self.monitor_logic, daemon=True)
        thread.start()

        # Ejecutamos el ícono en el hilo principal
        self.icon.run()

if __name__ == "__main__":
    # Evita que se abran múltiples instancias
    monitor = FortniteMonitor()
    monitor.run()