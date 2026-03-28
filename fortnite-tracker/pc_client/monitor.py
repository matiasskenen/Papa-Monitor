import psutil
import requests
import time

# USÁ TU URL REAL DE VERCEL
API_URL = "https://papa-monitor.vercel.app/api/status"
PROCESS_NAME = "chrome.exe"

def check_process():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == PROCESS_NAME:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

print(f"Buscando {PROCESS_NAME}...")
while True:
    is_online = check_process()
    try:
        response = requests.post(API_URL, json={"is_online": is_online}, timeout=10)
        print(f"Enviado: {'Online' if is_online else 'Offline'} | Server: {response.status_code}")
    except Exception as e:
        print(f"Error de red: {e}")
    
    time.sleep(30)