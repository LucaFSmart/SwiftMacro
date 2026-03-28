# tests/test_icon.py
from PIL import Image


def test_create_tray_icon_returns_image():
    from mouse_lock import create_tray_icon
    img = create_tray_icon()
    assert isinstance(img, Image.Image)


def test_create_tray_icon_correct_size():
    from mouse_lock import create_tray_icon, ICON_SIZE
    img = create_tray_icon()
    assert img.size == (ICON_SIZE, ICON_SIZE)


def test_create_tray_icon_is_rgba():
    from mouse_lock import create_tray_icon
    img = create_tray_icon()
    assert img.mode == "RGBA"
