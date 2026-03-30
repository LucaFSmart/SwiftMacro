from PIL import Image
from swiftmacro.icon import create_tray_icon
from swiftmacro.constants import ICON_SIZE


def test_create_tray_icon_returns_image():
    img = create_tray_icon()
    assert isinstance(img, Image.Image)


def test_create_tray_icon_correct_size():
    img = create_tray_icon()
    assert img.size == (ICON_SIZE, ICON_SIZE)


def test_create_tray_icon_is_rgba():
    img = create_tray_icon()
    assert img.mode == "RGBA"
