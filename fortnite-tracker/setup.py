import os, sys, subprocess, tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "PapaMonitor"
APP_PATH = os.path.join(os.environ['APPDATA'], APP_NAME)
SCRIPT_NAME = "monitor.py"

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Instalador Tracker")
        self.root.geometry("400x250")
        
        self.label = tk.Label(root, text="Configurando Tracker de Papá...", pady=20)
        self.label.pack()
        
        self.progress = ttk.Progressbar(root, length=300, mode='determinate')
        self.progress.pack(pady=10)
        
        self.btn_install = tk.Button(root, text="Instalar / Reparar", command=self.install)
        self.btn_install.pack(side="left", padx=40)
        
        self.btn_uninstall = tk.Button(root, text="Desinstalar", command=self.uninstall)
        self.btn_uninstall.pack(side="right", padx=40)

    def log(self, text, val):
        self.label.config(text=text)
        self.progress['value'] = val
        self.root.update()

    def install(self):
        # 1. Crear carpeta
        if not os.path.exists(APP_PATH): os.makedirs(APP_PATH)
        self.log("Instalando librerías necesarias...", 30)
        run_cmd("pip install psutil requests pystray Pillow pywebview")
        
        # 2. Mover el archivo (esto asume que el monitor.py está en la misma carpeta que el setup)
        self.log("Copiando archivos...", 60)
        # Aquí podrías bajarlo de tu Vercel directamente con requests
        
        # 3. Crear Tarea Programada de Windows (Schtasks)
        self.log("Creando tarea de auto-arranque...", 80)
        # Borra la anterior si existe para no duplicar
        run_cmd(f'schtasks /delete /tn "{APP_NAME}" /f')
        # Crea la nueva: Se ejecuta al iniciar sesión, sin ventana negra
        cmd = f'schtasks /create /tn "{APP_NAME}" /tr "pythonw.exe {os.path.join(APP_PATH, SCRIPT_NAME)}" /sc onlogon /rl highest /f'
        run_cmd(cmd)
        
        self.log("¡Instalación completa!", 100)
        messagebox.showinfo("Listo", "El monitor ya está corriendo en segundo plano.")
        self.root.destroy()

    def uninstall(self):
        self.log("Eliminando tarea programada...", 50)
        run_cmd(f'schtasks /delete /tn "{APP_NAME}" /f')
        self.log("Limpiando archivos...", 90)
        # Aquí podrías borrar la carpeta APP_PATH
        messagebox.showinfo("Desinstalado", "Se quitó el monitor del inicio de Windows.")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()