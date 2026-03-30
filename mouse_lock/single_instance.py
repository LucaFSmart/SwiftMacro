"""Windows single-instance guard."""
from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass

ERROR_ALREADY_EXISTS = 183


@dataclass
class SingleInstanceGuard:
    handle: int | None
    already_running: bool

    def release(self) -> None:
        if self.handle is None:
            return
        try:
            ctypes.windll.kernel32.CloseHandle(self.handle)
        except Exception:
            pass
        finally:
            self.handle = None


def acquire_single_instance(name: str) -> SingleInstanceGuard:
    """Acquire a named Windows mutex and report whether another instance already exists."""
    if os.name != "nt":
        return SingleInstanceGuard(handle=None, already_running=False)

    handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    already_running = ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS
    return SingleInstanceGuard(handle=handle, already_running=already_running)
