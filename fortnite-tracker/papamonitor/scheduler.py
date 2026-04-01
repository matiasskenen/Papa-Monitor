"""Tareas programadas de Windows (schtasks)."""

from __future__ import annotations

import subprocess
import sys

from papamonitor import constants

CREATE_NO_WINDOW = 0x08000000


def tarea_existe() -> bool:
    res = subprocess.run(
        ["schtasks", "/query", "/tn", constants.APP_NAME],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    return res.returncode == 0


def crear_tarea_inicio() -> tuple[bool, str]:
    app_path = sys.executable
    if not getattr(sys, "frozen", False):
        app_path = sys.executable  # python.exe durante desarrollo
    app_path = app_path.strip()
    tr_arg = f'"{app_path}" --start-minimized' if " " in app_path else f"{app_path} --start-minimized"
    res = subprocess.run(
        ["schtasks", "/create", "/f", "/tn", constants.APP_NAME, "/tr", tr_arg, "/sc", "onlogon", "/rl", "highest"],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    err = (res.stderr or res.stdout or "").strip()
    return res.returncode == 0, err


def eliminar_tarea() -> tuple[bool, str]:
    res = subprocess.run(
        ["schtasks", "/delete", "/tn", constants.APP_NAME, "/f"],
        capture_output=True,
        text=True,
        creationflags=CREATE_NO_WINDOW,
    )
    err = (res.stderr or res.stdout or "").strip()
    return res.returncode == 0, err
