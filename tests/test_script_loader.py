import pytest
from pathlib import Path
from script_loader import load_all_scripts, get_script, render_script

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


def test_load_all_scripts_returns_all_when_no_os_filter():
    scripts = load_all_scripts(scripts_dir=FIXTURES, os_tag=None)
    names = [s["name"] for cat in scripts.values() for s in cat]
    assert "Test Service Script" in names
    assert "Test IIS Script" in names
    assert "Test Win11 Script" in names


def test_load_all_scripts_filters_to_server2019():
    scripts = load_all_scripts(scripts_dir=FIXTURES, os_tag="server2019")
    names = [s["name"] for cat in scripts.values() for s in cat]
    assert "Test Service Script" in names
    assert "Test IIS Script" in names
    assert "Test Win11 Script" not in names


def test_load_all_scripts_filters_to_win11():
    scripts = load_all_scripts(scripts_dir=FIXTURES, os_tag="win11")
    names = [s["name"] for cat in scripts.values() for s in cat]
    assert "Test Service Script" in names
    assert "Test Win11 Script" in names
    assert "Test IIS Script" not in names


def test_get_script_returns_script_with_id_and_category():
    script = get_script("services", "test_service", scripts_dir=FIXTURES)
    assert script is not None
    assert script["id"] == "test_service"
    assert script["category"] == "services"
    assert "parameters" in script


def test_get_script_returns_none_for_missing():
    result = get_script("services", "nonexistent", scripts_dir=FIXTURES)
    assert result is None


def test_render_script_substitutes_params():
    body = "Get-Service -Name {{ service_name }}\nStart-Sleep -Seconds {{ timeout }}"
    result = render_script(body, {"service_name": "'Spooler'", "timeout": "30"})
    assert "Get-Service -Name 'Spooler'" in result
    assert "Start-Sleep -Seconds 30" in result
