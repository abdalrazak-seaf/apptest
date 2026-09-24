"""Structured logging must never collide with LogRecord's own attributes.

Passing a reserved key in `extra` raises KeyError at call time, which turns a log line into
a 500. This has bitten us twice, so the check is automated.
"""

import ast
import logging
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "api"

# Attribute names logging.LogRecord sets itself.
RESERVED = set(vars(logging.LogRecord("n", 0, "p", 0, "m", None, None)))


def extra_keys_in(path: Path) -> list[tuple[int, str]]:
    """Every literal key passed as `extra={...}` in a module, with its line number."""
    found: list[tuple[int, str]] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "extra" or not isinstance(keyword.value, ast.Dict):
                continue
            for key in keyword.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    found.append((key.lineno, key.value))
    return found


@pytest.mark.parametrize("path", sorted(SOURCE_ROOT.rglob("*.py")), ids=lambda p: str(p.name))
def test_no_log_extra_shadows_a_reserved_field(path: Path) -> None:
    clashes = [(line, key) for line, key in extra_keys_in(path) if key in RESERVED]
    assert not clashes, f"{path}: reserved logging keys {clashes}"


def test_the_check_would_catch_a_reserved_key(tmp_path: Path) -> None:
    module = tmp_path / "sample.py"
    module.write_text('logger.info("x", extra={"message": "boom", "ok": 1})\n')
    assert "message" in [key for _, key in extra_keys_in(module)]
