import pytest

from api.core.phone import mask_phone, normalize_saudi_phone


@pytest.mark.parametrize(
    "raw",
    [
        "0501234567",
        "501234567",
        "+966501234567",
        "00966501234567",
        "966501234567",
        "050 123 4567",
        "050-123-4567",
        "٠٥٠١٢٣٤٥٦٧",
        " +966 50 123 4567 ",
    ],
)
def test_accepts_the_formats_people_type(raw: str) -> None:
    assert normalize_saudi_phone(raw) == "+966501234567"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "05012345",  # too short
        "05012345678",  # too long
        "0401234567",  # landline, not a mobile
        "+971501234567",  # not Saudi
        "not-a-number",
        "05o1234567",
    ],
)
def test_rejects_anything_that_is_not_a_saudi_mobile(raw: str) -> None:
    assert normalize_saudi_phone(raw) is None


def test_mask_hides_the_middle_digits() -> None:
    assert mask_phone("+966501234567") == "+9665****4567"
    assert "1234567" not in mask_phone("+966501234567")
