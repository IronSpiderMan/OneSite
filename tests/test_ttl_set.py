"""TTLSet contract and deterministic concurrency regression tests."""

import importlib.util
import inspect
from pathlib import Path
import random
import sys
import threading
from types import SimpleNamespace

import pytest


SOURCE = (Path(__file__).resolve().parents[1] / "src/onesite/templates/backend/app/core/ttl_set.py")


@pytest.fixture
def runtime(monkeypatch):
    spec = importlib.util.spec_from_file_location("ttl_set_under_test", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: clock.now))
    return module, clock


def test_expiration_boundary_and_refresh(runtime):
    module, clock = runtime
    cache = module.TTLSet(10)
    cache.add("key")
    clock.now = 109.999
    assert cache.has("key") and "key" in cache
    cache.add("key", ttl=2)
    clock.now = 110
    assert len(cache) == 1
    clock.now = 111.998
    assert bool(cache)
    clock.now = 112
    assert not cache.has("key")
    assert len(cache) == 0 and not cache
    assert not cache.remove("key")


def test_default_changes_only_future_adds_and_singleton(runtime):
    module, clock = runtime
    cache = module.ttl_set
    cache.add("old")
    module.set_ttl(2)
    cache.add("new")
    clock.now += 2
    assert "old" in cache and "new" not in cache
    assert repr(cache) == "TTLSet(ttl=2, size=1)"
    assert cache.remove("old") and not cache.remove("old")
    cache.add("clear")
    cache.clear()
    assert not cache


@pytest.mark.parametrize("item", [None, 0, "", (1, 2), frozenset({3})])
def test_hashable_keys(runtime, item):
    module, _ = runtime
    cache = module.TTLSet()
    cache.add(item)
    assert item in cache
    assert cache.remove(item)


@pytest.mark.parametrize("operation", ["add", "has", "remove", "contains"])
def test_unhashable_keys_raise(runtime, operation):
    module, _ = runtime
    cache = module.TTLSet()
    with pytest.raises(TypeError):
        {"add": cache.add, "has": cache.has, "remove": cache.remove,
         "contains": cache.__contains__}[operation]([])


@pytest.mark.parametrize("operation", ["constructor", "setter", "add"])
@pytest.mark.parametrize("ttl", [0, -1, float("nan"), float("inf"), -float("inf")])
def test_ttl_requires_positive_finite_duration(runtime, operation, ttl):
    module, _ = runtime
    cache = module.TTLSet()
    with pytest.raises(ValueError):
        if operation == "constructor":
            module.TTLSet(ttl)
        elif operation == "setter":
            cache.set_default_ttl(ttl)
        else:
            cache.add("key", ttl=ttl)


def test_nan_default_must_not_create_immortal_entry(runtime):
    module, clock = runtime
    try:
        cache = module.TTLSet(float("nan"))
    except ValueError:
        return
    cache.add("key")
    clock.now += 1_000_000
    assert "key" not in cache
    assert len(cache) == 0


def test_randomized_operations_against_reference(runtime):
    module, clock = runtime
    cache = module.TTLSet(5)
    reference = {}
    default = 5
    rng = random.Random(20261015)
    for _ in range(10_000):
        clock.now += rng.choice([0, 0.125, 1, 5])
        reference = {k: expiry for k, expiry in reference.items() if expiry > clock.now}
        key = rng.randrange(20)
        operation = rng.choice(["add", "remove", "has", "clear", "default"])
        if operation == "add":
            ttl = rng.choice([None, 0.25, 2, 10])
            cache.add(key, ttl)
            reference[key] = clock.now + (default if ttl is None else ttl)
        elif operation == "remove":
            assert cache.remove(key) == (key in reference)
            reference.pop(key, None)
        elif operation == "has":
            assert cache.has(key) == (key in reference)
            assert (key in cache) == (key in reference)
        elif operation == "clear":
            cache.clear()
            reference.clear()
        else:
            default = rng.choice([0.5, 2, 20])
            cache.set_default_ttl(default)
        assert len(cache) == len(reference)
        assert bool(cache) == bool(reference)


@pytest.mark.parametrize("interference", ["clear", "renew", "evict"])
def test_expiration_cleanup_is_safe_during_concurrent_operations(runtime, interference):
    module, clock = runtime
    cache = module.TTLSet(1)
    cache.add("key")
    clock.now += 1
    paused = threading.Event()
    resume = threading.Event()
    errors = []
    code = module.TTLSet._evict_expired.__code__
    lines, first = inspect.getsourcelines(module.TTLSet._evict_expired)
    delete_line = first + next(i for i, line in enumerate(lines) if "del self._data[item]" in line)

    def trace(frame, event, arg):
        if frame.f_code is code and event == "line" and frame.f_lineno == delete_line:
            paused.set()
            if not resume.wait(5):
                raise TimeoutError("Concurrent operation did not release cleanup")
        return trace

    def worker():
        sys.settrace(trace)
        try:
            cache.has("key")
        except BaseException as exc:
            errors.append(exc)
        finally:
            sys.settrace(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    try:
        assert paused.wait(5), "Cleanup never reached deletion"
        if interference == "clear":
            cache.clear()
        elif interference == "renew":
            cache.add("key", ttl=60)
        else:
            assert not cache.has("key")
    finally:
        resume.set()
        thread.join(5)
    assert not thread.is_alive()
    assert not errors, f"Concurrent {interference} caused: {errors!r}"
    if interference == "renew":
        assert cache.has("key"), "Cleanup deleted an entry renewed by another thread"


@pytest.mark.parametrize("operation", ["add", "remove", "has", "contains", "len", "bool", "repr"])
def test_operations_reclaim_expired_entries(runtime, operation):
    module, clock = runtime
    cache = module.TTLSet(1)
    cache.add("expired")
    clock.now += 1
    {"add": lambda: cache.add("new"), "remove": lambda: cache.remove("missing"),
     "has": lambda: cache.has("missing"), "contains": lambda: "missing" in cache,
     "len": lambda: len(cache), "bool": lambda: bool(cache), "repr": lambda: repr(cache)}[operation]()
    assert "expired" not in cache._data


def test_instances_are_independent(runtime):
    module, _ = runtime
    first, second = module.TTLSet(), module.TTLSet()
    first.add("key")
    assert "key" not in second and "key" not in module.ttl_set
