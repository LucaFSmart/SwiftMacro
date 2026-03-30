import json
import os
import pytest
from swiftmacro.models import Profile, ActionStep
from swiftmacro.profile_store import ProfileImportResult, ProfileStore


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


def test_load_returns_copies(store, sample_profile):
    store.add_profile(sample_profile)
    loaded = store.load()
    loaded[0].name = "Changed In Memory"
    assert store.load()[0].name == "Test"


def test_get_by_id_returns_copy(store, sample_profile):
    store.add_profile(sample_profile)
    found = store.get_by_id(sample_profile.id)
    assert found is not None
    found.name = "Changed In Memory"
    assert store.get_by_id(sample_profile.id).name == "Test"


def test_duplicate_profile_creates_copy_without_hotkey(store, sample_profile):
    store.add_profile(sample_profile)
    duplicate = store.duplicate_profile(sample_profile.id)

    assert duplicate.id != sample_profile.id
    assert duplicate.name == "Test (Copy)"
    assert duplicate.hotkey is None
    assert len(store.load()) == 2


def test_export_profiles_writes_selected_profile(tmp_path, sample_profile):
    store = ProfileStore(profiles_dir=str(tmp_path / "profiles"))
    store.add_profile(sample_profile)
    export_path = tmp_path / "export.json"

    count = store.export_profiles(str(export_path), [sample_profile.id])

    exported = json.loads(export_path.read_text(encoding="utf-8"))
    assert count == 1
    assert len(exported) == 1
    assert exported[0]["name"] == "Test"


def test_import_profiles_adds_profiles_and_clears_conflicting_hotkeys(tmp_path):
    store = ProfileStore(profiles_dir=str(tmp_path / "profiles"))
    existing = Profile.create_new(
        name="Existing",
        hotkey="ctrl+alt+1",
        steps=[ActionStep(action="move", params={"x": 1, "y": 2})],
    )
    store.add_profile(existing)
    import_path = tmp_path / "import.json"
    import_path.write_text(
        json.dumps(
            [
                {
                    "id": "a",
                    "name": "Imported A",
                    "hotkey": "ctrl+alt+1",
                    "steps": [{"action": "move", "params": {"x": 10, "y": 20}}],
                },
                {
                    "id": "b",
                    "name": "Imported B",
                    "hotkey": "ctrl+alt+2",
                    "steps": [{"action": "wait", "params": {"ms": 50}}],
                },
            ]
        ),
        encoding="utf-8",
    )

    result = store.import_profiles(str(import_path))
    loaded = store.load()

    assert isinstance(result, ProfileImportResult)
    assert len(result.imported_ids) == 2
    assert result.cleared_hotkeys == 1
    assert result.skipped_invalid == 0
    assert len(loaded) == 3
    assert loaded[1].hotkey is None
    assert loaded[2].hotkey == "ctrl+alt+2"


def test_import_profiles_skips_invalid_profiles(tmp_path):
    store = ProfileStore(profiles_dir=str(tmp_path / "profiles"))
    import_path = tmp_path / "import_invalid.json"
    import_path.write_text(
        json.dumps(
            [
                {
                    "id": "bad",
                    "name": "Broken",
                    "hotkey": None,
                    "steps": [{"action": "wait", "params": {"ms": -10}}],
                }
            ]
        ),
        encoding="utf-8",
    )

    result = store.import_profiles(str(import_path))

    assert result.imported_ids == []
    assert result.skipped_invalid == 1
    assert store.load() == []
