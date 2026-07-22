import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import cast

spec = importlib.util.spec_from_file_location(
    "llmapt_runner_contract",
    Path(__file__).parents[2] / "runner" / "app.py",
)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_detect_memory_exceeded = cast(
    Callable[[bytes, int, int, bool], bool],
    module._detect_memory_exceeded,
)


def test_runner_detects_memory_limit_from_peak_usage() -> None:
    assert _detect_memory_exceeded(b"", 31_200, 32_768, False) is True


def test_runner_detects_allocator_failure_case_insensitively() -> None:
    assert _detect_memory_exceeded(b"Cannot allocate memory", 1_000, 32_768, False) is True
    assert _detect_memory_exceeded(b"std::bad_alloc", 1_000, 32_768, False) is True


def test_timeout_takes_precedence_over_memory_classification() -> None:
    assert _detect_memory_exceeded(b"std::bad_alloc", 32_768, 32_768, True) is False
