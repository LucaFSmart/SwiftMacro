"""Tests for ProfileManager — focuses on the hotkey-sync contract."""
import pytest
from unittest.mock import MagicMock

from swiftmacro.models import ActionStep, Profile
from swiftmacro.profile_manager import ProfileManager
from swiftmacro.profile_store import ProfileStore


@pytest.fixture
def store(tmp_path):
    return ProfileStore(profiles_dir=str(tmp_path), legacy_dir=str(tmp_path / "legacy"))


@pytest.fixture
def hotkey_mgr():
    return MagicMock()


@pytest.fixture
def manager(store, hotkey_mgr):
    return ProfileManager(store, hotkey_mgr)


def _profile(name="P", hotkey=None) -> Profile:
    return Profile.create_new(
        name=name,
        hotkey=hotkey,
        steps=[ActionStep(action="wait", params={"ms": 10})],
    )


def test_add_triggers_hotkey_refresh(manager, hotkey_mgr):
    manager.add(_profile())
    hotkey_mgr.refresh_profile_hotkeys.assert_called_once()


def test_update_triggers_hotkey_refresh(manager, hotkey_mgr):
    p = _profile()
    manager.add(p)
    hotkey_mgr.refresh_profile_hotkeys.reset_mock()
    p.name = "Renamed"
    manager.update(p)
    hotkey_mgr.refresh_profile_hotkeys.assert_called_once()


def test_delete_triggers_hotkey_refresh(manager, hotkey_mgr):
    p = _profile()
    manager.add(p)
    hotkey_mgr.refresh_profile_hotkeys.reset_mock()
    manager.delete(p.id)
    hotkey_mgr.refresh_profile_hotkeys.assert_called_once()


def test_duplicate_triggers_hotkey_refresh(manager, hotkey_mgr):
    p = _profile()
    manager.add(p)
    hotkey_mgr.refresh_profile_hotkeys.reset_mock()
    manager.duplicate(p.id)
    hotkey_mgr.refresh_profile_hotkeys.assert_called_once()


def test_import_triggers_hotkey_refresh(manager, hotkey_mgr, tmp_path):
    import json
    import_path = tmp_path / "import.json"
    import_path.write_text(
        json.dumps([{
            "id": "imp", "name": "Imp", "hotkey": None,
            "steps": [{"action": "wait", "params": {"ms": 10}}],
        }]),
        encoding="utf-8",
    )
    manager.import_file(str(import_path))
    hotkey_mgr.refresh_profile_hotkeys.assert_called_once()


def test_export_does_not_touch_hotkeys(manager, hotkey_mgr, tmp_path):
    p = _profile()
    manager.add(p)
    hotkey_mgr.refresh_profile_hotkeys.reset_mock()
    manager.export_file(str(tmp_path / "out.json"), [p.id])
    hotkey_mgr.refresh_profile_hotkeys.assert_not_called()


def test_list_and_get_proxy_to_store(manager):
    p = _profile()
    manager.add(p)
    assert len(manager.list()) == 1
    assert manager.get(p.id).name == "P"
    assert manager.get("nope") is None


def test_hotkey_refresh_failure_does_not_break_mutation(store, caplog):
    """If refresh_profile_hotkeys raises, the profile mutation still succeeds."""
    import logging
    bad_mgr = MagicMock()
    bad_mgr.refresh_profile_hotkeys.side_effect = RuntimeError("hotkey daemon dead")
    manager = ProfileManager(store, bad_mgr)
    with caplog.at_level(logging.WARNING, logger="swiftmacro.profile_manager"):
        manager.add(_profile())
    assert len(store.load()) == 1
    assert any("hotkey daemon dead" in r.message.lower() or "hotkey refresh" in r.message.lower()
               for r in caplog.records)


def test_works_without_hotkey_manager(store):
    """ProfileManager must be usable in tests/headless contexts without a hotkey mgr."""
    manager = ProfileManager(store, hotkey_mgr=None)
    p = _profile()
    manager.add(p)
    assert len(manager.list()) == 1
    manager.delete(p.id)
    assert manager.list() == []


def test_record_run_increments_count_and_timestamp(manager):
    p = _profile()
    manager.add(p)
    assert manager.get(p.id).run_count == 0
    assert manager.get(p.id).last_run_at is None
    manager.record_run(p.id)
    after = manager.get(p.id)
    assert after.run_count == 1
    assert after.last_run_at is not None
    manager.record_run(p.id)
    assert manager.get(p.id).run_count == 2


def test_record_run_unknown_id_is_noop(manager):
    manager.record_run("does-not-exist")  # must not raise
