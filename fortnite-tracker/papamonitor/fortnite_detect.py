from __future__ import annotations

import psutil


def is_fortnite_running(process_substrings: list[str], exclude_substrings: tuple[str, ...]) -> bool:
    """
    Detecta si el proceso de Fortnite existe Y consume más de 3GB de RAM (RSS).
    """
    needles = [p.lower().replace(".exe", "") for p in process_substrings if p]
    bad = tuple(x.lower() for x in exclude_substrings)
    
    # 3GB en Bytes (3 * 1024 * 1024 * 1024)
    THRESHOLD_BYTES = 3 * 1024**3

    for proc in psutil.process_iter(["name", "pid", "memory_info"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if not name:
                continue
            if any(b in name for b in bad):
                continue
            
            name_base = name.replace(".exe", "")
            match_found = False

            # 1. Validación por nombre
            if any(n and (n in name or n in name_base) for n in needles):
                match_found = True
            
            # 2. Validación por ruta de ejecutable (si el nombre falló)
            if not match_found:
                try:
                    exe = (proc.exe() or "").lower()
                    if exe and any(n and n in exe for n in needles):
                        match_found = True
                except (psutil.Error, OSError, NotImplementedError):
                    pass

            # 3. Solo si hubo coincidencia de nombre, chequeamos RAM
            if match_found:
                mem_info = proc.info.get("memory_info")
                # Solo retorna True si supera los 3GB
                if mem_info and mem_info.rss > THRESHOLD_BYTES:
                    return True

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
            
    return False