"""Descarga monitor.exe desde el sitio y reinicia reemplazando el ejecutable (solo PyInstaller)."""

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


def _descargar(url: str, destino: str, timeout: int = 180) -> tuple[bool, str]:
    part = destino + ".part"
    try:
        with requests.get(url, timeout=timeout, stream=True) as res:
            res.raise_for_status()
            with open(part, "wb") as f:
                for chunk in res.iter_content(256 * 1024):
                    if chunk:
                        f.write(chunk)
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


def _lanzar_bat_reemplazo(nuevo_exe: str, exe_final: str) -> tuple[bool, str]:
    bat = os.path.join(tempfile.gettempdir(), "PapaMonitor_apply_update.bat")
    nuevo = os.path.normpath(nuevo_exe)
    final = os.path.normpath(exe_final)
    lineas = [
        "@echo off",
        "timeout /t 4 /nobreak > nul",
        f'move /Y "{nuevo}" "{final}"',
        f'start "" "{final}"',
        "del /F /Q \"%~f0\"",
    ]
    try:
        with open(bat, "w", newline="\r\n", encoding="utf-8") as f:
            f.write("\r\n".join(lineas))
        subprocess.Popen(
            ["cmd.exe", "/c", bat],
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
        return True, ""
    except OSError as e:
        return False, str(e)


def aplicar_actualizacion_monitor(monitor_exe_url: str) -> tuple[bool, str]:
    """
    Descarga monitor.exe a %%TEMP%% y programa un .bat que, tras cerrar este proceso,
    mueve el archivo nuevo sobre sys.executable y vuelve a abrir el monitor.
    """
    if not es_ejecutable_compilado():
        return False, "Solo disponible en monitor.exe compilado (PyInstaller)."
    exe_actual = os.path.abspath(sys.executable)
    tmp_nuevo = os.path.join(tempfile.gettempdir(), "PapaMonitor_update_new.exe")
    try:
        if os.path.isfile(tmp_nuevo):
            try:
                os.remove(tmp_nuevo)
            except OSError:
                pass
    except OSError:
        pass
    ok, err = _descargar(monitor_exe_url, tmp_nuevo)
    if not ok:
        return False, err
    ok2, err2 = _lanzar_bat_reemplazo(tmp_nuevo, exe_actual)
    if not ok2:
        try:
            os.remove(tmp_nuevo)
        except OSError:
            pass
        return False, err2
    return True, ""
