import threading
import pytest


@pytest.fixture
def stop_event():
    e = threading.Event()
    yield e
    e.set()
