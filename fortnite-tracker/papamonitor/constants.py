"""Valores por defecto solo para arranque (sin secretos). Sobrescribir con variables de entorno o JSON local."""

import os

APP_NAME = "PapaMonitor"

# Primera URL para cargar /api/public-config y rutas relativas; override: PAPAMONITOR_API_BASE o papamonitor_settings.json
DEFAULT_API_BASE = os.environ.get("PAPAMONITOR_API_BASE", "https://papa-monitor.vercel.app").rstrip("/")

LOCK_FILE = os.path.join(os.getenv("TEMP") or ".", "papa_monitor_v5.lock")

SETTINGS_FILENAME = "papamonitor_settings.json"

# Fallback si falla la red al leer public-config (subcadenas en minúsculas para comparar)
DEFAULT_PROCESS_SUBSTRINGS = (
    "fortniteclient-win64-shipping",
    "fortniteclient-win64-shipping_be",
)

# Nombres que nunca cuentan como “juego en marcha”
PROCESS_NAME_EXCLUDE_SUBSTRINGS = (
    "epicgameslauncher",
    "unrealeditor",
    "fortnitelauncher",  # launcher solo, no el cliente del juego
)

DEFAULT_POLL_INTERVAL_SECONDS = 20
