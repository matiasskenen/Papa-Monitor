import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem as item
import os
import sys

# --- FUNCIONES DE ACCIÓN ---
def mostrar_estado(icon):
    # Acá podrías hacer un fetch a tu API de Flask para ver si el viejo está online
    print("Abriendo ventana de estado...")
    os.system('msg * "El monitor está ACTIVO y escaneando."')

def actualizar_programa(icon):
    print("Buscando actualizaciones...")
    # Acá podrías meter un 'git pull' o lo que uses para actualizar
    os.system('msg * "Buscando actualizaciones en el servidor..."')

def desinstalar_programa(icon):
    confirmar = input("¿Seguro que querés desinstalar? (s/n): ")
    if confirmar.lower() == 's':
        icon.stop()
        # Lógica para borrar archivos o el registro
        print("Desinstalando...")

def cerrar_programa(icon):
    print("Cerrando monitor...")
    icon.stop()
    sys.exit()

# --- CREACIÓN DEL ÍCONO ---
# Genera un ícono simple (un cuadrado azul) si no tenés un .ico a mano
def crear_imagen():
    width, height = 64, 64
    image = Image.new('RGB', (width, height), (0, 120, 215)) # Azul Windows
    dc = ImageDraw.Draw(image)
    dc.rectangle((width // 4, height // 4, width * 3 // 4, height * 3 // 4), fill=(255, 255, 255))
    return image

# --- MENÚ CON CLICK DERECHO ---
menu_tray = pystray.Menu(
    item('Ver Estado', mostrar_estado),
    item('Actualizar', actualizar_programa),
    item('Desinstalar', desinstalar_programa),
    pystray.Menu.SEPARATOR,
    item('Cerrar Programa', cerrar_programa)
)

icon = pystray.Icon("PapaMonitor", crear_imagen(), "Papa Monitor", menu_tray)

# Lanzar el ícono
if __name__ == "__main__":
    icon.run()