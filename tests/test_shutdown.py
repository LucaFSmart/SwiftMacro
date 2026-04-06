"""Tests for ShutdownCoordinator."""
import logging

from swiftmacro.shutdown import ShutdownCoordinator


def test_trigger_calls_registered_callback():
    coord = ShutdownCoordinator()
    calls = []
    coord.set_callback(lambda: calls.append(1))
    coord.trigger()
    assert calls == [1]


def test_trigger_without_callback_logs_warning(caplog):
    coord = ShutdownCoordinator()
    with caplog.at_level(logging.WARNING, logger="swiftmacro.shutdown"):
        coord.trigger()
    assert any("before a callback" in r.message for r in caplog.records)


def test_trigger_swallows_callback_exception(caplog):
    coord = ShutdownCoordinator()

    def boom():
        raise RuntimeError("nope")

    coord.set_callback(boom)
    with caplog.at_level(logging.ERROR, logger="swiftmacro.shutdown"):
        coord.trigger()  # must not raise
    assert any("nope" in r.message for r in caplog.records)


def test_set_callback_replaces_previous():
    coord = ShutdownCoordinator()
    calls = []
    coord.set_callback(lambda: calls.append("a"))
    coord.set_callback(lambda: calls.append("b"))
    coord.trigger()
    assert calls == ["b"]
