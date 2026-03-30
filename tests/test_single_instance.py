from unittest.mock import patch

from swiftmacro.single_instance import (
    ERROR_ALREADY_EXISTS,
    acquire_single_instance,
)


def test_acquire_single_instance_detects_existing_process():
    with patch("swiftmacro.single_instance.os.name", "nt"), patch(
        "swiftmacro.single_instance.ctypes"
    ) as mock_ctypes:
        mock_ctypes.windll.kernel32.CreateMutexW.return_value = 123
        mock_ctypes.windll.kernel32.GetLastError.return_value = ERROR_ALREADY_EXISTS

        guard = acquire_single_instance("Local\\MouseLock.Test")

    assert guard.handle == 123
    assert guard.already_running is True


def test_acquire_single_instance_returns_fresh_guard_when_available():
    with patch("swiftmacro.single_instance.os.name", "nt"), patch(
        "swiftmacro.single_instance.ctypes"
    ) as mock_ctypes:
        mock_ctypes.windll.kernel32.CreateMutexW.return_value = 456
        mock_ctypes.windll.kernel32.GetLastError.return_value = 0

        guard = acquire_single_instance("Local\\MouseLock.Test")

    assert guard.handle == 456
    assert guard.already_running is False
