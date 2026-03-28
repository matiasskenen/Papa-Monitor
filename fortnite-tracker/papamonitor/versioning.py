from papamonitor.paths import resource_path


def _version_tuple(s: str):
    parts = []
    for chunk in s.strip().lower().lstrip("v").split("."):
        num = "".join(c for c in chunk if c.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)


def remote_version_is_newer(remote: str, current: str) -> bool:
    return _version_tuple(remote) > _version_tuple(current)


def read_bundled_version() -> str:
    try:
        with open(resource_path("version.txt"), encoding="utf-8") as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"
