import psutil
import requests
import time

API_URL = "https://papa-monitor.vercel.app/api/status"
PROCESS_NAME = "FortniteClient-Win64-Shipping.exe"

def is_running():
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] == PROCESS_NAME:
                return True
        except: continue
    return False

print("Monitor 100% Certero Iniciado...")
while True:
    online = is_running()
    try:
        r = requests.post(API_URL, json={"is_online": online}, timeout=10)
        print(f"Reporte enviado: {'ONLINE' if online else 'OFFLINE'} | Server: {r.status_code}")
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(60) # Chequeo cada 1 minuto