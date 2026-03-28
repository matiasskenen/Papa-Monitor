"""Ícono de bandeja del sistema."""

from __future__ import annotations

import threading
from typing import Callable

import pystray
from PIL import Image

from papamonitor import constants


def iniciar_tray(
    image: Image.Image,
    on_open_dashboard: Callable[[], None],
    on_quit: Callable[[], None],
) -> pystray.Icon:
    menu = pystray.Menu(
        pystray.MenuItem("Abrir panel", on_open_dashboard, default=True),
        pystray.MenuItem("Cerrar monitor", on_quit),
    )
    icon = pystray.Icon(constants.APP_NAME, image, f"{constants.APP_NAME} activo", menu)
    threading.Thread(target=icon.run, daemon=True).start()
    return icon
