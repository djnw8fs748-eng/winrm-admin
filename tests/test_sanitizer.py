import pytest
from sanitizer import sanitize_params, ValidationError


PARAMS_DEF = [
    {"name": "service_name", "label": "Service Name", "type": "text", "required": True},
    {"name": "timeout", "label": "Timeout", "type": "number", "required": False, "default": 30},
]


def test_sanitize_valid_text_wraps_in_single_quotes():
    result = sanitize_params(PARAMS_DEF, {"service_name": "Spooler", "timeout": "10"})
    assert result["service_name"] == "'Spooler'"


def test_sanitize_text_escapes_internal_single_quotes():
    result = sanitize_params(PARAMS_DEF, {"service_name": "O'Brien", "timeout": "10"})
    assert result["service_name"] == "'O''Brien'"


def test_sanitize_valid_number_passes_through():
    result = sanitize_params(PARAMS_DEF, {"service_name": "svc", "timeout": "45"})
    assert result["timeout"] == "45"


def test_sanitize_invalid_number_raises():
    with pytest.raises(ValidationError, match="Timeout"):
        sanitize_params(PARAMS_DEF, {"service_name": "svc", "timeout": "notanumber"})


def test_sanitize_missing_required_raises():
    with pytest.raises(ValidationError, match="Service Name"):
        sanitize_params(PARAMS_DEF, {"service_name": "", "timeout": "10"})


def test_sanitize_missing_optional_uses_default():
    result = sanitize_params(PARAMS_DEF, {"service_name": "svc", "timeout": ""})
    assert result["timeout"] == "30"


def test_sanitize_ps_injection_chars_escaped():
    result = sanitize_params(
        [{"name": "val", "label": "Val", "type": "text", "required": True}],
        {"val": "foo'bar"},
    )
    assert result["val"] == "'foo''bar'"
