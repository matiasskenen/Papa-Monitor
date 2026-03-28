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
from tkinter import messagebox, scrolledtext
from PIL import Image, ImageTk
import pystray
from datetime import datetime

# ==========================================
# CONFIGURACIÓN
# ==========================================
API_URL = "https://papa-monitor.vercel.app/api/status"
VERSION_URL = "https://papa-monitor.vercel.app/version.txt"
CURRENT_VERSION = "1.0.0"
PROCESS_NAME = "FortniteClient-Win64-Shipping.exe"
APP_NAME = "PapaMonitor"
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
        
        # Ventana Principal
        self.root = tk.Tk()
        self.root.withdraw() 
        self.root.title(f" {APP_NAME} - Dashboard")
        self.root.geometry("500x600")
        self.root.configure(bg="#ffffff")
        
        # Arreglar el logo de la pluma
        try:
            self.img_logo = Image.open(resource_path("logo.png"))
            self.photo_logo = ImageTk.PhotoImage(self.img_logo)
            self.root.iconphoto(False, self.photo_logo)
        except: pass

        self.setup_ui()
        self.iniciar_tray()
        
        threading.Thread(target=self.monitor_loop, daemon=True).start()
        self.lanzar_asistente()
        self.root.mainloop()

    def log(self, mensaje):
        """ Escribe en la consola de la app """
        timestamp = datetime.now().strftime("%H:%M:%S")
        texto = f"[{timestamp}] {mensaje}\n"
        self.console.insert(tk.END, texto)
        self.console.see(tk.END)
        print(texto.strip())

    def esta_instalado(self):
        res = subprocess.run(['schtasks', '/query', '/tn', APP_NAME], capture_output=True, text=True, creationflags=0x08000000)
        return res.returncode == 0

    def gestionar_tarea(self, accion="crear"):
        if accion == "crear":
            app_path = os.path.abspath(sys.executable)
            comando = f'schtasks /create /f /tn "{APP_NAME}" /tr "\\"{app_path}\\"" /sc onlogon /rl highest'
            res = subprocess.run(comando, capture_output=True, text=True, shell=True, creationflags=0x08000000)
        else:
            res = subprocess.run(['schtasks', '/delete', '/tn', APP_NAME, '/f'], capture_output=True, text=True, creationflags=0x08000000)
        return res.returncode == 0, res.stderr.strip()

    def setup_ui(self):
        # Header Blue
        header = tk.Frame(self.root, bg="#0078d7", height=70)
        header.pack(fill="x")
        tk.Label(header, text="PAPA MONITOR SYSTEM", bg="#0078d7", fg="white", font=("Segoe UI", 12, "bold")).pack(pady=20)

        # Body
        self.body = tk.Frame(self.root, bg="#ffffff")
        self.body.pack(pady=10, padx=20, fill="both")

        # Consola tipo terminal
        tk.Label(self.root, text="CONSOLA DE ACTIVIDAD:", font=("Segoe UI", 8, "bold"), bg="#ffffff", fg="#333").pack(anchor="w", padx=25)
        self.console = scrolledtext.ScrolledText(self.root, height=10, bg="#1e1e1e", fg="#d4d4d4", font=("Consolas", 9), borderwidth=0)
        self.console.pack(padx=20, pady=5, fill="both", expand=True)

        # Footer
        footer = tk.Frame(self.root, bg="#f3f3f3")
        footer.pack(fill="x", side="bottom")
        
        self.btn_toggle = tk.Button(footer, text="CERRAR DASHBOARD", bg="#e1e1e1", relief="flat", command=self.ocultar_asistente, font=("Segoe UI", 9))
        self.btn_toggle.pack(fill="x", pady=0)

    def lanzar_asistente(self):
        self.dibujar_botones()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.log("Panel de control abierto.")

    def ocultar_asistente(self):
        self.root.withdraw()
        self.log("Panel minimizado al tray.")

    def dibujar_botones(self):
        for widget in self.body.winfo_children(): widget.destroy()
        
        if not self.esta_instalado():
            tk.Button(self.body, text="ACTIVAR INICIO AUTOMÁTICO", bg="#0078d7", fg="white", font=("Segoe UI", 10, "bold"), 
                      relief="flat", height=2, command=self.accion_instalar).pack(fill="x", pady=10)
        else:
            tk.Button(self.body, text="BUSCAR ACTUALIZACIONES", bg="#28a745", fg="white", font=("Segoe UI", 10, "bold"), 
                      relief="flat", height=2, command=self.accion_update).pack(fill="x", pady=5)
            
            tk.Button(self.body, text="DESINSTALAR Y CERRAR TODO", bg="#dc3545", fg="white", font=("Segoe UI", 10, "bold"), 
                      relief="flat", height=2, command=self.accion_desinstalar).pack(fill="x", pady=5)

    def accion_instalar(self):
        exito, msg = self.gestionar_tarea("crear")
        if exito:
            self.log("Tarea de Windows creada con éxito.")
            messagebox.showinfo("Éxito", "Monitor configurado.")
            self.dibujar_botones()
        else: self.log(f"Error al instalar: {msg}")

    def accion_desinstalar(self):
        if messagebox.askyesno("Confirmar", "Se borrará la tarea y el proceso. ¿Continuar?"):
            self.log("Desinstalando sistema...")
            self.gestionar_tarea("eliminar")
            self.salir_total()

    def accion_update(self):
        self.log("Buscando actualizaciones en el servidor...")
        try:
            r = requests.get(VERSION_URL, timeout=5)
            if r.text.strip() > CURRENT_VERSION:
                self.log("¡Nueva versión encontrada!")
                messagebox.showinfo("Update", "Nueva versión disponible.")
            else:
                self.log("Ya estás actualizado.")
        except: self.log("Error de conexión al buscar update.")

    def monitor_loop(self):
        self.log("Iniciando ciclo de monitoreo...")
        while self.running:
            try:
                status = any(p.info['name'] == PROCESS_NAME for p in psutil.process_iter(['name']))
                if status != self.is_online:
                    self.is_online = status
                    self.log(f"Estado cambiado: {'ONLINE' if status else 'OFFLINE'}")
                    requests.post(API_URL, json={"is_online": self.is_online}, timeout=10)
            except Exception as e:
                self.log(f"Error en monitor: {e}")
            time.sleep(30)

    def iniciar_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Abrir Dashboard", self.lanzar_asistente, default=True),
            pystray.MenuItem("Salir", self.salir_total)
        )
        self.icon = pystray.Icon(APP_NAME, self.img_logo, "PapaMonitor", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def salir_total(self):
        self.log("Cerrando aplicación...")
        self.running = False
        if hasattr(self, 'icon'): self.icon.stop()
        if lock_fp: lock_fp.close()
        try: os.remove(LOCK_FILE)
        except: pass
        os._exit(0)

if __name__ == "__main__":
    solicitar_admin()
    if not verificar_instancia(): sys.exit(0)
    app = PapaMonitorApp()