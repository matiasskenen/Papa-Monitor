"""Detección robusta del proceso del juego (Fortnite).

Incluye varios nombres de ejecutable y excluye launchers/editores."""

from __future__ import annotations

import psutil


def is_fortnite_running(process_substrings: list[str], exclude_substrings: tuple[str, ...]) -> bool:
    needles = [p.lower().replace(".exe", "") for p in process_substrings if p]
    bad = tuple(x.lower() for x in exclude_substrings)

    for proc in psutil.process_iter(["name", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if not name:
                continue
            if any(b in name for b in bad):
                continue
            name_base = name.replace(".exe", "")
            if any(n and (n in name or n in name_base) for n in needles):
                return True
            try:
                exe = (proc.exe() or "").lower()
            except (psutil.Error, OSError, NotImplementedError):
                exe = ""
            if exe and any(n and n in exe for n in needles):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False
