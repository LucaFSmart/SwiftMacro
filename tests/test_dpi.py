def test_init_dpi_awareness_does_not_crash():
    """DPI init must never raise, regardless of OS support."""
    from swiftmacro.dpi import init_dpi_awareness
    init_dpi_awareness()
