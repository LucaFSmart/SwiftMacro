"""Concurrency and edge-case tests added in Phase 3 of the refactor.

These exercise behaviour that wasn't covered by the per-module unit tests:

* Parallel writers against :class:`ProfileStore` (the lock contract).
* :meth:`ActionRunner.stop` while a chain is mid-execution.
* Profile names with unicode / special characters round-tripping through
  :class:`ProfileStore` and :class:`ProfileManager`.
* Very long step chains exercising the per-step polling and progress hooks.
"""
from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from swiftmacro.action_runner import ActionRunner
from swiftmacro.constants import MAX_STEPS
from swiftmacro.models import ActionStep, Profile
from swiftmacro.profile_manager import ProfileManager
from swiftmacro.profile_store import ProfileStore
from swiftmacro.state import make_state


# --- ProfileStore concurrency ------------------------------------------------
@pytest.fixture
def store(tmp_path):
    return ProfileStore(
        profiles_dir=str(tmp_path),
        legacy_dir=str(tmp_path / "legacy_nonexistent"),
    )


def _make_profile(name: str) -> Profile:
    return Profile.create_new(
        name=name,
        hotkey=None,
        steps=[ActionStep(action="wait", params={"ms": 1})],
    )


def test_parallel_adds_do_not_lose_profiles(store):
    """Concurrent add_profile calls must serialise cleanly via the lock."""
    barrier = threading.Barrier(8)
    errors: list[Exception] = []

    def worker(idx: int) -> None:
        try:
            barrier.wait()
            store.add_profile(_make_profile(f"Concurrent {idx}"))
        except Exception as exc:  # pragma: no cover - test diagnostic
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert not errors, f"workers raised: {errors}"
    profiles = store.load()
    assert len(profiles) == 8
    names = sorted(p.name for p in profiles)
    assert names == sorted(f"Concurrent {i}" for i in range(8))


def test_parallel_update_and_delete_does_not_corrupt_store(store):
    """Mixed update/delete workload must leave the store in a consistent state."""
    profiles = [_make_profile(f"P{i}") for i in range(6)]
    for p in profiles:
        store.add_profile(p)

    def updater(p: Profile) -> None:
        for _ in range(20):
            p.name = f"{p.name}*"
            try:
                store.update_profile(p)
            except KeyError:
                return  # got deleted by the other thread — that's fine

    def deleter(target_id: str) -> None:
        time.sleep(0.005)
        store.delete_profile(target_id)

    workers: list[threading.Thread] = []
    for p in profiles[:3]:
        workers.append(threading.Thread(target=updater, args=(p,)))
    for p in profiles[3:]:
        workers.append(threading.Thread(target=deleter, args=(p.id,)))

    for t in workers:
        t.start()
    for t in workers:
        t.join(timeout=5)

    # The disk file should still be parseable and ≤ original count.
    surviving = store.load()
    assert 0 <= len(surviving) <= 6


# --- ActionRunner.stop edge cases -------------------------------------------
def test_stop_during_long_chain_releases_runner_busy():
    """Stopping mid-chain must clear runner_busy and join the worker thread."""
    state = make_state()
    runner = ActionRunner(state)
    long_chain = [ActionStep(action="wait", params={"ms": 5000}) for _ in range(5)]
    profile = Profile(id="long", name="Long", hotkey=None, steps=long_chain)

    runner.run_profile(profile)
    time.sleep(0.05)
    assert state.get_runner_busy() is True

    runner.stop()
    assert state.get_runner_busy() is False
    assert not runner.is_running()


def test_stop_called_twice_in_a_row_is_safe():
    state = make_state()
    runner = ActionRunner(state)
    profile = Profile(
        id="x", name="X", hotkey=None,
        steps=[ActionStep(action="wait", params={"ms": 5000})],
    )
    runner.run_profile(profile)
    time.sleep(0.05)
    runner.stop()
    # Second stop is a no-op and must not raise.
    runner.stop()
    assert not runner.is_running()


def test_concurrent_stop_calls_do_not_raise():
    """Multiple stop() callers from different threads must serialise safely."""
    state = make_state()
    runner = ActionRunner(state)
    profile = Profile(
        id="y", name="Y", hotkey=None,
        steps=[ActionStep(action="wait", params={"ms": 5000})],
    )
    runner.run_profile(profile)
    time.sleep(0.05)

    errors: list[Exception] = []

    def stopper() -> None:
        try:
            runner.stop()
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=stopper) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3)

    assert not errors
    assert not runner.is_running()


# --- Special-character profile names ----------------------------------------
@pytest.mark.parametrize("name", [
    "Profile mit Umlaut äöü",
    "中文配置",
    "emoji rocket",
    "name/with/slashes",
    "name\twith\ttabs",
    "name with \"quotes\" and 'apostrophes'",
    "   leading/trailing spaces   ",
    "a" * 200,
])
def test_special_character_profile_names_roundtrip(store, name):
    profile = Profile.create_new(
        name=name,
        hotkey=None,
        steps=[ActionStep(action="wait", params={"ms": 5})],
    )
    store.add_profile(profile)
    loaded = store.load()
    assert any(p.name == name for p in loaded), f"name not preserved: {name!r}"


def test_profile_manager_handles_special_character_names(store):
    manager = ProfileManager(store, hotkey_mgr=None)
    profile = Profile.create_new(
        name="Spécial — name 🚀",
        hotkey=None,
        steps=[ActionStep(action="wait", params={"ms": 5})],
    )
    manager.add(profile)
    fetched = manager.get(profile.id)
    assert fetched is not None
    assert fetched.name == "Spécial — name 🚀"


# --- Long step chains -------------------------------------------------------
def test_max_length_step_chain_runs_to_completion():
    """A chain at MAX_STEPS length must complete and report progress for the last step."""
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 1}) for _ in range(MAX_STEPS)]
    profile = Profile(id="max", name="Max", hotkey=None, steps=steps)

    progress_calls: list[tuple[int, int]] = []
    original = state.set_chain_progress

    def spy(current: int, total: int) -> None:
        progress_calls.append((current, total))
        original(current, total)

    state.set_chain_progress = spy
    runner.run_profile(profile)
    # Chain has 100 × 1 ms wait → padding gives plenty of headroom.
    deadline = time.time() + 5.0
    while runner.is_running() and time.time() < deadline:
        time.sleep(0.05)

    assert not runner.is_running(), "long chain failed to finish in time"
    assert (1, MAX_STEPS) in progress_calls
    assert (MAX_STEPS, MAX_STEPS) in progress_calls
    assert "Done" in state.get_status_message()


def test_long_chain_can_be_stopped_partway():
    state = make_state()
    runner = ActionRunner(state)
    steps = [ActionStep(action="wait", params={"ms": 100}) for _ in range(MAX_STEPS)]
    profile = Profile(id="stoppable", name="Stoppable", hotkey=None, steps=steps)

    runner.run_profile(profile)
    time.sleep(0.05)
    assert runner.is_running()
    runner.stop()
    assert not runner.is_running()

    current, total = state.get_chain_progress()
    # We stopped almost immediately — progress must be far below MAX_STEPS.
    assert total in (0, MAX_STEPS)
    assert current < MAX_STEPS
