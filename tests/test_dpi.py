# tests/test_dpi.py
def test_init_dpi_awareness_does_not_crash():
    """DPI init must never raise, regardless of OS support."""
    from mouse_lock import init_dpi_awareness
    init_dpi_awareness()  # must not raise
