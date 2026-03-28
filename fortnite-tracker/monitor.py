import psutil
import requests
import time
import os
import sys
import threading
import msvcrt
import subprocess
import ctypes
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import pystray
from datetime import datetime

# ==========================================
# CONFIGURACIÓN (NOMBRE EXACTO CMD)
# ==========================================
API_URL = "https://papa-monitor.vercel.app/api/status"
VERSION_URL = "https://papa-monitor.vercel.app/version.txt"
CURRENT_VERSION = "1.0.0"
PROCESS_NAME = "FortniteClient-Win64-Shipping.exe"
APP_NAME = "PapaMonitor" # Este nombre debe coincidir con schtasks
LOCK_FILE = os.path.join(os.getenv('TEMP'), 'papa_monitor_v4.lock')

def solicitar_admin():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

lock_fp = None
def verificar_instancia():
    global lock_fp
    try:
        lock_fp = open(LOCK_FILE, 'w')
        msvcrt.locking(lock_fp.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except: return False

class PapaMonitorApp:
    def __init__(self):
        self.running = True
        self.is_online = False
        self.ultima_comprobacion = "Nunca"
        
        self.root = tk.Tk()
        self.root.withdraw() 
        self.root.title(f"Setup - {APP_NAME}")
        self.root.geometry("450x500")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.ocultar_asistente)

        self.setup_ui()
        self.iniciar_tray()
        
        threading.Thread(target=self.monitor_loop, daemon=True).start()
        self.lanzar_asistente()
        self.root.mainloop()

    def esta_instalado(self):
        try:
            # Query silenciosa para ver si la tarea existe
            res = subprocess.run(['schtasks', '/query', '/tn', APP_NAME], 
                                 capture_output=True, text=True, creationflags=0x08000000)
            return res.returncode == 0
        except: return False

    def gestionar_tarea(self, accion="crear"):
        try:
            if accion == "crear":
                app_path = os.path.abspath(sys.executable)
                comando = f'schtasks /create /f /tn "{APP_NAME}" /tr "\\"{app_path}\\"" /sc onlogon /rl highest'
                res = subprocess.run(comando, capture_output=True, text=True, shell=True, creationflags=0x08000000)
            else:
                # Borrado forzado idéntico al que hiciste en el CMD
                res = subprocess.run(['schtasks', '/delete', '/tn', APP_NAME, '/f'], 
                                     capture_output=True, text=True, creationflags=0x08000000)
            return res.returncode == 0, res.stderr.strip()
        except Exception as e: return False, str(e)

    def setup_ui(self):
        header = tk.Frame(self.root, bg="#0078d7", height=80)
        header.pack(fill="x")
        tk.Label(header, text="Asistente de Instalación", bg="#0078d7", fg="white", font=("Segoe UI", 14, "bold")).pack(pady=20)

        self.body = tk.Frame(self.root, bg="#f0f0f0")
        self.body.pack(pady=20, padx=40, fill="both", expand=True)

        self.info_label = tk.Label(self.root, text=f"Último chequeo: {self.ultima_comprobacion}", 
                                   font=("Segoe UI", 8), bg="#f0f0f0", fg="#666")
        self.info_label.pack(side="bottom", pady=5)

        tk.Button(self.root, text="Cerrar y minimizar", bg="#28a745", fg="white", 
                  font=("Segoe UI", 10, "bold"), command=self.ocultar_asistente).pack(side="bottom", fill="x", pady=10)

    def lanzar_asistente(self):
        self.dibujar_contenido()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def ocultar_asistente(self):
        self.root.withdraw()

    def dibujar_contenido(self):
        for widget in self.body.winfo_children(): widget.destroy()

        instalado = self.esta_instalado()
        if not instalado:
            tk.Label(self.body, text="Estado: No instalado", font=("Segoe UI", 10, "italic"), bg="#f0f0f0").pack(pady=5)
            tk.Button(self.body, text="INSTALAR AUTORUN", width=25, bg="#0078d7", fg="white", 
                      font=("Segoe UI", 10, "bold"), command=self.accion_instalar).pack(pady=20)
        else:
            tk.Label(self.body, text="Estado: Instalado correctamente", font=("Segoe UI", 10, "bold"), fg="#0078d7", bg="#f0f0f0").pack(pady=5)
            tk.Button(self.body, text="BUSCAR ACTUALIZACIÓN", width=25, command=self.accion_update).pack(pady=5)
            tk.Button(self.body, text="DESINSTALAR TODO", width=25, fg="red", 
                      font=("Segoe UI", 10, "bold"), command=self.accion_desinstalar).pack(pady=20)

    def accion_instalar(self):
        exito, msg = self.gestionar_tarea("crear")
        if exito: 
            messagebox.showinfo("Éxito", "Monitor configurado para iniciar con Windows.")
            self.dibujar_contenido()
        else: 
            messagebox.showerror("Error", f"Fallo al crear tarea: {msg}")

    def accion_desinstalar(self):
        if messagebox.askyesno("Confirmar", "Se eliminará la tarea programada y el programa se cerrará por completo.\n¿Continuar?"):
            exito, msg = self.gestionar_tarea("eliminar")
            if exito:
                messagebox.showinfo("Desinstalación", "Tarea eliminada con éxito. Cerrando aplicación...")
                self.salir_total() # Esto mata el proceso y el ícono al instante
            else:
                messagebox.showerror("Error", f"No se pudo eliminar la tarea: {msg}")

    def accion_update(self):
        try:
            self.ultima_comprobacion = datetime.now().strftime("%H:%M:%S")
            self.info_label.config(text=f"Último chequeo: {self.ultima_comprobacion}")
            r = requests.get(VERSION_URL, timeout=5)
            if r.text.strip() > CURRENT_VERSION:
                messagebox.showinfo("Update", "Nueva versión disponible.")
            else:
                messagebox.showinfo("Update", "Estás en la última versión.")
        except: 
            messagebox.showerror("Error", "No se pudo conectar al servidor.")

    def monitor_loop(self):
        while self.running:
            try:
                status = any(p.info['name'] == PROCESS_NAME for p in psutil.process_iter(['name']))
                if status != self.is_online:
                    self.is_online = status
                    requests.post(API_URL, json={"is_online": self.is_online}, timeout=10)
            except: pass
            time.sleep(60)

    def iniciar_tray(self):
        try: image = Image.open(resource_path("logo.png"))
        except: image = Image.new('RGB', (64, 64), (40, 40, 40))

        menu = pystray.Menu(
            pystray.MenuItem("Abrir Asistente", self.lanzar_asistente, default=True),
            pystray.MenuItem("Buscar Actualización", self.accion_update),
            pystray.MenuItem("Salir", self.salir_total)
        )
        self.icon = pystray.Icon(APP_NAME, image, "PapaMonitor", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def salir_total(self):
        self.running = False
        if hasattr(self, 'icon') and self.icon: 
            self.icon.stop()
        if lock_fp: 
            lock_fp.close()
        try: 
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except: pass
        os._exit(0) # Mata el proceso monitor.exe inmediatamente

if __name__ == "__main__":
    solicitar_admin()
    if not verificar_instancia():
        sys.exit(0)

    app = PapaMonitorApp()