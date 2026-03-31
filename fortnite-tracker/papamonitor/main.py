"""Punto de entrada del monitor (tras elevación y lock)."""

from __future__ import annotations

import sys

from papamonitor import updater
from papamonitor.dashboard_ui import PapaMonitorApp
from papamonitor.instance_lock import verificar_instancia_unica
from papamonitor.windows_admin import solicitar_admin


def run() -> None:
    # ── Auto-install: si este exe fue lanzado desde %TEMP% como actualización,
    #    se copia a la ubicación correcta y se relanza desde ahí.
    if getattr(sys, "frozen", False):
        destino = updater.leer_y_borrar_marker()
        if destino:
            updater.aplicar_self_install(destino)
            # Si llegamos aquí, la copia falló → seguimos corriendo desde %TEMP%

    solicitar_admin()
    if not verificar_instancia_unica():
        sys.exit(0)
    PapaMonitorApp()


if __name__ == "__main__":
    run()
