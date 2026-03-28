import psutil
import requests
import time

# Configura tu URL de Vercel acá
API_URL = "https://tu-proyecto.vercel.app/api/status"
PROCESS_NAME = "FortniteClient-Win64-Shipping.exe"

def check_process():
    # Busca si el proceso de Fortnite está en la lista de ejecución
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == PROCESS_NAME:
            return True
    return False

print("Monitoreo iniciado...")
while True:
    is_online = check_process()
    try:
        requests.post(API_URL, json={"is_online": is_online}, timeout=10)
    except Exception as e:
        print(f"Error de red: {e}")
    
    time.sleep(30) # Checkea cada 30 segundos