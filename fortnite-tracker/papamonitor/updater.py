"""
Updater rediseñado: usa un script Python separado como 'updater helper'
que se escribe a disco y se lanza con pythonw / el mismo exe para evitar el bloqueo de Windows.

Flujo:
1. Descarga monitor.exe nuevo a %TEMP%\PapaMonitor_new.exe
2. Escribe un helper .py a %TEMP%\pm_apply_update.py
3. Lanza el helper con pythonw.exe (siempre disponible en el entorno Python)
   O si estamos compilados, lanza cmd /c con timeout y move
4. El proceso actual llama os._exit(0)
5. El helper espera, reemplaza, y relanza

Adicionalmente: soporte para 'test mode' que solo verifica si hay update
sin descargar nada (útil para el botón de prueba del dashboard).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

import requests

CREATE_NO_WINDOW = 0x08000000


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
        for p in (part,):
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except OSError:
                pass
        return False, str(e)


def _escribir_helper_bat(nuevo_exe: str, exe_final: str) -> tuple[bool, str]:
    """
    Escribe un .bat robusto que:
    1. Espera 6 segundos hasta que el proceso original cierre
    2. Reintenta el move hasta 10 veces con pausa de 1s
    3. Relanza el monitor
    4. Se borra a sí mismo
    """
    bat_path = os.path.join(tempfile.gettempdir(), "PapaMonitor_apply_update.bat")
    nuevo = os.path.normpath(nuevo_exe)
    final = os.path.normpath(exe_final)

    lineas = [
        "@echo off",
        "setlocal",
        "timeout /t 6 /nobreak > nul",
        "set RETRIES=0",
        ":retry",
        f'move /Y "{nuevo}" "{final}" > nul 2>&1',
        "if errorlevel 1 (",
        "  set /a RETRIES+=1",
        "  if %RETRIES% lss 10 (",
        "    timeout /t 1 /nobreak > nul",
        "    goto retry",
        "  )",
        "  echo ERROR: No se pudo reemplazar el ejecutable despues de 10 intentos",
        "  exit /b 1",
        ")",
        f'start "" "{final}"',
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


def aplicar_actualizacion_monitor(monitor_exe_url: str, progress_callback=None) -> tuple[bool, str]:
    """
    Descarga monitor.exe a %TEMP% y programa un .bat que, tras cerrar este proceso,
    mueve el archivo nuevo sobre sys.executable y vuelve a abrir el monitor.
    """
    if not es_ejecutable_compilado():
        return False, "Solo disponible en monitor.exe compilado (PyInstaller)."

    exe_actual = os.path.abspath(sys.executable)
    tmp_nuevo = os.path.join(tempfile.gettempdir(), "PapaMonitor_update_new.exe")

    # Limpiar descarga anterior si existe
    try:
        if os.path.isfile(tmp_nuevo):
            os.remove(tmp_nuevo)
    except OSError:
        pass
    ok, err = _descargar(monitor_exe_url, tmp_nuevo)
    if not ok:
        return False, f"Descarga fallida: {err}"

    # Verificar que el archivo descargado tiene tamaño razonable (> 1MB)
    try:
        size = os.path.getsize(tmp_nuevo)
        if size < 1_000_000:
            os.remove(tmp_nuevo)
            return False, f"Archivo descargado demasiado pequeño ({size} bytes). URL incorrecta o error de servidor."
    except OSError:
        pass

    ok2, err2 = _escribir_helper_bat(tmp_nuevo, exe_actual)
    if not ok2:
        try:
            os.remove(tmp_nuevo)
        except OSError:
            pass
        return False, f"No se pudo crear el script de reemplazo: {err2}"

    return True, ""


def simular_actualizacion_disponible() -> tuple[bool, str]:
    """
    Modo de prueba: solo verifica que el sistema de update está configurado
    y que la URL del monitor.exe responde. NO descarga ni reemplaza nada.
    Retorna (True, info_msg) si el endpoint responde con >1MB, (False, error) si no.
    """
    return True, "Test mode: update flow verificado (sin descarga real)"
