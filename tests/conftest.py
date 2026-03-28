import pytest


@pytest.fixture
def stop_event():
    import threading
    e = threading.Event()
    yield e
    e.set()
