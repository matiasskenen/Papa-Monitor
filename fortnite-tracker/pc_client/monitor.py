import psutil, requests, time

API_URL = "https://papa-monitor.vercel.app/api/status" # <--- TU URL
PROCESS = "FortniteClient-Win64-Shipping.exe"

print("Monitor 100% Certero en marcha...")
while True:
    running = any(p.info['name'] == PROCESS for p in psutil.process_iter(['name']))
    try:
        r = requests.post(API_URL, json={"is_online": running}, timeout=10)
        print(f"Reporte: {'ONLINE' if running else 'OFFLINE'} | Server: {r.status_code}")
    except Exception as e:
        print(f"Error de red: {e}")
    time.sleep(60)