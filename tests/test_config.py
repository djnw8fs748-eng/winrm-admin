import os
import pytest
from unittest.mock import patch


def test_load_config_parses_vms(monkeypatch):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10:server2019,ws1:192.168.1.20:win11")
    monkeypatch.setenv("WINRM_USERNAME", "Admin")
    monkeypatch.setenv("WINRM_PASSWORD", "pass")
    monkeypatch.setenv("WINRM_PORT", "5985")
    monkeypatch.setenv("WINRM_TRANSPORT", "ntlm")

    from config import load_config
    cfg = load_config()

    assert len(cfg.vms) == 2
    assert cfg.vms[0].name == "dc01"
    assert cfg.vms[0].ip == "192.168.1.10"
    assert cfg.vms[0].os_tag == "server2019"
    assert cfg.vms[1].name == "ws1"
    assert cfg.vms[1].os_tag == "win11"
    assert cfg.username == "Admin"
    assert cfg.port == 5985


def test_load_config_defaults_port_and_transport(monkeypatch):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10:server2019")
    monkeypatch.setenv("WINRM_USERNAME", "Admin")
    monkeypatch.setenv("WINRM_PASSWORD", "pass")
    monkeypatch.delenv("WINRM_PORT", raising=False)
    monkeypatch.delenv("WINRM_TRANSPORT", raising=False)

    from config import load_config
    cfg = load_config()

    assert cfg.port == 5985
    assert cfg.transport == "ntlm"


def test_load_config_exits_on_missing_vm_hosts(monkeypatch):
    monkeypatch.delenv("VM_HOSTS", raising=False)
    monkeypatch.setenv("WINRM_USERNAME", "Admin")
    monkeypatch.setenv("WINRM_PASSWORD", "pass")

    with pytest.raises(SystemExit) as exc_info:
        from config import load_config
        load_config()
    assert exc_info.value.code == 1


def test_load_config_exits_on_missing_credentials(monkeypatch):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10:server2019")
    monkeypatch.delenv("WINRM_USERNAME", raising=False)
    monkeypatch.delenv("WINRM_PASSWORD", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        from config import load_config
        load_config()
    assert exc_info.value.code == 1


def test_load_config_exits_on_malformed_vm_entry(monkeypatch):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10")  # missing os_tag
    monkeypatch.setenv("WINRM_USERNAME", "Admin")
    monkeypatch.setenv("WINRM_PASSWORD", "pass")

    with pytest.raises(SystemExit) as exc_info:
        from config import load_config
        load_config()
    assert exc_info.value.code == 1


def test_load_config_exits_on_invalid_port(monkeypatch):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10:server2019")
    monkeypatch.setenv("WINRM_USERNAME", "Admin")
    monkeypatch.setenv("WINRM_PASSWORD", "pass")
    monkeypatch.setenv("WINRM_PORT", "notanint")

    with pytest.raises(SystemExit) as exc_info:
        import importlib, config as config_module
        importlib.reload(config_module)
        config_module.load_config()
    assert exc_info.value.code == 1
