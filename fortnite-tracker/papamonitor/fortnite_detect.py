from __future__ import annotations

import psutil


def is_fortnite_running(process_substrings: list[str], exclude_substrings: tuple[str, ...]) -> bool:
    """
    Detecta si el proceso de Fortnite existe Y consume más de 4GB de RAM (RSS).
    """
    needles = [p.lower().replace(".exe", "") for p in process_substrings if p]
    bad = tuple(x.lower() for x in exclude_substrings)
    # 4GB en Bytes (4 * 1024 * 1024 * 1024)
    THRESHOLD_BYTES = 4 * 1024**3

    # Agregamos 'memory_info' a la iteración para optimizar performance
    for proc in psutil.process_iter(["name", "pid", "memory_info"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if not name:
                continue
            if any(b in name for b in bad):
                continue
            
            name_base = name.replace(".exe", "")
            match_found = False

            # Validación por nombre
            if any(n and (n in name or n in name_base) for n in needles):
                match_found = True
            
            # Validación por ruta de ejecutable (si el nombre falló)
            if not match_found:
                try:
                    exe = (proc.exe() or "").lower()
                    if exe and any(n and n in exe for n in needles):
                        match_found = True
                except (psutil.Error, OSError, NotImplementedError):
                    pass

            # Si hubo match, chequeamos que el consumo de RAM supere el umbral
            if match_found:
                mem_info = proc.info.get("memory_info")
                if mem_info and mem_info.rss > THRESHOLD_BYTES:
                    return True

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    return False