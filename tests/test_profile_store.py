import json
import os
import pytest
from mouse_lock.models import Profile, ActionStep
from mouse_lock.profile_store import ProfileStore


@pytest.fixture
def store(tmp_path):
    """ProfileStore pointing at a temp directory."""
    return ProfileStore(profiles_dir=str(tmp_path))


@pytest.fixture
def sample_profile():
    return Profile.create_new(
        name="Test",
        hotkey="ctrl+alt+1",
        steps=[ActionStep(action="move", params={"x": 100, "y": 200})],
    )


def test_load_empty(store):
    profiles = store.load()
    assert profiles == []


def test_add_and_load(store, sample_profile):
    store.add_profile(sample_profile)
    profiles = store.load()
    assert len(profiles) == 1
    assert profiles[0].name == "Test"


def test_save_creates_file(store, sample_profile, tmp_path):
    store.add_profile(sample_profile)
    assert (tmp_path / "profiles.json").exists()


def test_update_profile(store, sample_profile):
    store.add_profile(sample_profile)
    sample_profile.name = "Updated"
    store.update_profile(sample_profile)
    profiles = store.load()
    assert profiles[0].name == "Updated"


def test_delete_profile(store, sample_profile):
    store.add_profile(sample_profile)
    store.delete_profile(sample_profile.id)
    assert store.load() == []


def test_max_profiles(store):
    for i in range(5):
        p = Profile.create_new(name=f"P{i}", hotkey=None, steps=[])
        store.add_profile(p)
    with pytest.raises(ValueError, match="Max"):
        store.add_profile(Profile.create_new(name="P6", hotkey=None, steps=[]))


def test_corrupted_json(store, tmp_path):
    (tmp_path / "profiles.json").write_text("not valid json{{{")
    profiles = store.load()
    assert profiles == []


def test_get_by_id(store, sample_profile):
    store.add_profile(sample_profile)
    found = store.get_by_id(sample_profile.id)
    assert found is not None
    assert found.name == "Test"


def test_get_by_id_not_found(store):
    assert store.get_by_id("nonexistent") is None
