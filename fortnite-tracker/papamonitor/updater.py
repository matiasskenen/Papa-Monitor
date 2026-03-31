"""
Updater v3 — Estrategia "self-install"

Flujo:
1. Descarga monitor.exe nuevo a %TEMP%\PapaMonitor_update_new.exe
2. Escribe un marker con la ruta final donde debe instalarse
3. Bat: espera que el proceso anterior muera, luego lanza directamente
   el exe DESDE %TEMP% (sin reemplazar nada)
4. El nuevo exe detecta que es una actualización (via marker) y se copia
   a sí mismo a la ruta correcta, luego se relanza desde ahí.

Ventajas vs estrategia de reemplazo:
- No hay file-in-use: el bat nunca toca el exe en uso
- La DLL carga desde %TEMP% normalmente (igual que antes)
- Después de copiarse a la ruta final, se relanza cleanly
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import requests

CREATE_NO_WINDOW = 0x08000000
MARKER_FILENAME  = "PapaMonitor_install_marker.txt"
NUEVO_EXE_NAME   = "PapaMonitor_update_new.exe"


def es_ejecutable_compilado() -> bool:
    return bool(getattr(sys, "frozen", False))


def obtener_version_remota(version_url: str, timeout: float = 12.0) -> str | None:
    try:
        r = requests.get(version_url, timeout=timeout)
        r.raise_for_status()
        v = (r.text or "").strip()
        return v or None
    except Exception:
        return None


def _descargar(url: str, destino: str, timeout: int = 180, progress_callback=None) -> tuple[bool, str]:
    part = destino + ".part"
    try:
        with requests.get(url, timeout=timeout, stream=True) as res:
            res.raise_for_status()
            total_size = int(res.headers.get('content-length', 0))
            downloaded = 0
            with open(part, "wb") as f:
                for chunk in res.iter_content(64 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            progress_callback(percent)
        os.replace(part, destino)
        return True, ""
    except Exception as e:
        try:
            if os.path.isfile(part):
                os.remove(part)
        except OSError:
            pass
        return False, str(e)


def _escribir_bat_self_install(nuevo_exe: str) -> tuple[bool, str]:
    """
    Bat que espera a que el proceso anterior muera, luego lanza el nuevo
    exe DESDE su ubicación en %TEMP%. El nuevo exe se instala a sí mismo.
    """
    bat_path = os.path.join(tempfile.gettempdir(), "PapaMonitor_apply_update.bat")
    nuevo    = os.path.normpath(nuevo_exe)

    lineas = [
        "@echo off",
        "setlocal",
        # Esperar que el proceso original muera
        "timeout /t 10 /nobreak > nul",
        # Lanzar el nuevo exe DESDE %TEMP% (sin reemplazar el exe original)
        f'start "" "{nuevo}"',
        # Limpiar el bat
        'del /F /Q "%~f0"',
    ]

    try:
        with open(bat_path, "w", newline="\r\n", encoding="utf-8") as f:
            f.write("\r\n".join(lineas))
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, ""
    except OSError as e:
        return False, str(e)


def _escribir_marker(ruta_final: str) -> None:
    """Guarda la ruta de instalación para que el nuevo exe sepa a dónde copiarse."""
    marker = os.path.join(tempfile.gettempdir(), MARKER_FILENAME)
    with open(marker, "w", encoding="utf-8") as f:
        f.write(ruta_final)


def leer_y_borrar_marker() -> str | None:
    """
    Llamar al inicio del proceso.
    Si existe el marker, significa que somos la actualización descargada.
    Devuelve la ruta destino o None si no hay marker.
    """
    marker = os.path.join(tempfile.gettempdir(), MARKER_FILENAME)
    if not os.path.isfile(marker):
        return None
    try:
        ruta = open(marker, encoding="utf-8").read().strip()
        os.remove(marker)
        return ruta or None
    except OSError:
        return None


def aplicar_self_install(ruta_destino: str) -> None:
    """
    Llamar cuando leer_y_borrar_marker() devuelve una ruta.
    Copia este exe a ruta_destino y re-lanza desde ahí.
    """
    import shutil
    import time

    exe_actual = os.path.abspath(sys.executable)
    destino    = os.path.normpath(ruta_destino)

    if exe_actual == destino:
        return  # ya estamos en la ruta correcta

    # Reintentos de copia por si el exe destino aún está bloqueado brevemente
    for intento in range(15):
        try:
            shutil.copy2(exe_actual, destino)
            break
        except OSError:
            time.sleep(1)
    else:
        # Si no se pudo copiar, seguimos corriendo desde %TEMP% (mejor que nada)
        return

    # Relanzar desde la ruta final
    subprocess.Popen(
        [destino],
        creationflags=subprocess.DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
    os._exit(0)


def aplicar_actualizacion_monitor(monitor_exe_url: str, progress_callback=None) -> tuple[bool, str]:
    """
    Descarga el nuevo exe a %TEMP%, escribe el marker con la ruta final,
    y programa el bat que lanzará el nuevo exe desde %TEMP%.
    """
    if not es_ejecutable_compilado():
        return False, "Solo disponible en monitor.exe compilado (PyInstaller)."

    exe_actual = os.path.abspath(sys.executable)
    tmp_nuevo  = os.path.join(tempfile.gettempdir(), NUEVO_EXE_NAME)

    # Limpiar descarga anterior
    try:
        if os.path.isfile(tmp_nuevo):
            os.remove(tmp_nuevo)
    except OSError:
        pass

    ok, err = _descargar(monitor_exe_url, tmp_nuevo, progress_callback=progress_callback)
    if not ok:
        return False, f"Descarga fallida: {err}"

    # Verificar tamaño mínimo (>5MB para un exe real)
    try:
        size = os.path.getsize(tmp_nuevo)
        if size < 5_000_000:
            os.remove(tmp_nuevo)
            return False, f"Exe descargado demasiado pequeño ({size // 1024}KB). URL incorrecta o error de servidor."
    except OSError:
        pass

    # Escribir marker con la ruta donde debe instalarse
    try:
        _escribir_marker(exe_actual)
    except OSError as e:
        return False, f"No se pudo escribir el marker: {e}"

    # Crear y lanzar el bat
    ok2, err2 = _escribir_bat_self_install(tmp_nuevo)
    if not ok2:
        try:
            os.remove(tmp_nuevo)
        except OSError:
            pass
        return False, f"No se pudo crear el script de actualización: {err2}"

    return True, ""


def simular_actualizacion_disponible() -> tuple[bool, str]:
    return True, "Test mode: update flow verificado (sin descarga real)"
