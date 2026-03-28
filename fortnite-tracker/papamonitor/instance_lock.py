import msvcrt
import os

from papamonitor import constants

_lock_fp = None


def verificar_instancia_unica() -> bool:
    global _lock_fp
    try:
        _lock_fp = open(constants.LOCK_FILE, "w")
        msvcrt.locking(_lock_fp.fileno(), msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def cerrar_lock() -> None:
    global _lock_fp
    try:
        if _lock_fp:
            _lock_fp.close()
    except OSError:
        pass
    _lock_fp = None
    try:
        os.remove(constants.LOCK_FILE)
    except OSError:
        pass
