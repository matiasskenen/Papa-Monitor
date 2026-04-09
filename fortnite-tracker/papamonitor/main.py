"""Punto de entrada del monitor (tras elevación y lock)."""

from __future__ import annotations

import sys

from papamonitor import updater
from papamonitor.dashboard_ui import PapaMonitorApp
from papamonitor.instance_lock import verificar_instancia_unica
from papamonitor.windows_admin import solicitar_admin


def run() -> None:
    dev_ui_mode = "--dev-ui" in sys.argv and not getattr(sys, "frozen", False)

    # ── Auto-install: si este exe fue lanzado desde %TEMP% como actualización,
    #    se copia a la ubicación correcta y se relanza desde ahí.
    if getattr(sys, "frozen", False):
        destino = updater.leer_y_borrar_marker()
        if destino:
            updater.aplicar_self_install(destino)
            # Si llegamos aquí, la copia falló → seguimos corriendo desde %TEMP%

    if not dev_ui_mode:
        solicitar_admin()
        if not verificar_instancia_unica():
            # Si ya hay una instancia corriendo y se llamó con --show, mostrar el panel
            if "--show" in sys.argv:
                # La instancia existente no escucha señales, simplemente salir
                pass
            sys.exit(0)
    # --start-minimized: se pasa cuando Windows inicia el programa en el arranque
    # La detección de la bandera ocurre dentro de PapaMonitorApp.__init__
    app = PapaMonitorApp()
    app.run()


if __name__ == "__main__":
    run()
