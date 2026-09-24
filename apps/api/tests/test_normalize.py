import json
from pathlib import Path

import pytest

from api.core.normalize import normalize_arabic, normalize_digits, parse_int

# Shared with packages/i18n (TypeScript) so both implementations behave identically.
CASES = json.loads(
    (Path(__file__).parents[3] / "packages/i18n/test-cases/normalize.json").read_text("utf-8")
)


@pytest.mark.parametrize(("raw", "expected"), CASES["digits"])
def test_normalize_digits(raw: str, expected: str) -> None:
    assert normalize_digits(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), CASES["parse_int"])
def test_parse_int(raw: str, expected: int | None) -> None:
    assert parse_int(raw) == expected


@pytest.mark.parametrize(("raw", "expected"), CASES["arabic"])
def test_normalize_arabic(raw: str, expected: str) -> None:
    assert normalize_arabic(raw) == expected
