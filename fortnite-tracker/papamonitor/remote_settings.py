"""Obtiene configuración pública del servidor (patrones de proceso, intervalo de sondeo)."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from papamonitor import constants
from papamonitor.paths import exe_directory


def _load_sidecar_json() -> dict[str, Any]:
    path = os.path.join(exe_directory(), constants.SETTINGS_FILENAME)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _api_base() -> str:
    env = os.environ.get("PAPAMONITOR_API_BASE", "").strip().rstrip("/")
    if env:
        return env
    side = _load_sidecar_json().get("api_base")
    if isinstance(side, str) and side.strip():
        return side.strip().rstrip("/")
    return constants.DEFAULT_API_BASE


def fetch_public_config(timeout: float = 12.0) -> dict[str, Any]:
    base = _api_base()
    url = f"{base}/api/public-config"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _as_api_base(val) -> str:
    if isinstance(val, str) and val.strip():
        return val.strip().rstrip("/")
    return ""


def merge_client_config() -> dict[str, Any]:
    """
    api_base: usado para POST /api/status y GET version.txt
    process_substrings: lista de subcadenas (se comparan en minúsculas)
    poll_interval_seconds: float/int
    """
    remote = fetch_public_config()
    side = _load_sidecar_json()

    base = _as_api_base(side.get("api_base")) or _as_api_base(remote.get("api_base")) or _api_base()

    proc = remote.get("process_substrings") or side.get("process_substrings")
    if isinstance(proc, str):
        try:
            proc = json.loads(proc)
        except json.JSONDecodeError:
            proc = [p.strip() for p in proc.split(",") if p.strip()]
    if not isinstance(proc, list) or not proc:
        proc = list(constants.DEFAULT_PROCESS_SUBSTRINGS)

    poll = remote.get("poll_interval_seconds", side.get("poll_interval_seconds"))
    try:
        poll = int(poll) if poll is not None else constants.DEFAULT_POLL_INTERVAL_SECONDS
    except (TypeError, ValueError):
        poll = constants.DEFAULT_POLL_INTERVAL_SECONDS
    poll = max(10, min(poll, 300))

    return {
        "api_base": base,
        "process_substrings": [str(p).lower() for p in proc],
        "poll_interval_seconds": poll,
    }


def resolve_urls(api_base: str) -> tuple[str, str]:
    b = api_base.rstrip("/")
    return f"{b}/api/status", f"{b}/version.txt"


def monitor_exe_url(api_base: str) -> str:
    return f"{api_base.rstrip('/')}/monitor.exe"
