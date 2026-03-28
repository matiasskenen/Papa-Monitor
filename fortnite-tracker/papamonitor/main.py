"""Punto de entrada del monitor (tras elevación y lock)."""

from __future__ import annotations

import sys

from papamonitor.dashboard_ui import PapaMonitorApp
from papamonitor.instance_lock import verificar_instancia_unica
from papamonitor.windows_admin import solicitar_admin


def run() -> None:
    solicitar_admin()
    if not verificar_instancia_unica():
        sys.exit(0)
    PapaMonitorApp()


if __name__ == "__main__":
    run()
