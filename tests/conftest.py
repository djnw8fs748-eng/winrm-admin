import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def set_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10:server2019,ws1:192.168.1.20:win11")
    monkeypatch.setenv("WINRM_USERNAME", "Admin")
    monkeypatch.setenv("WINRM_PASSWORD", "pass")
    monkeypatch.setenv("WINRM_PORT", "5985")
    monkeypatch.setenv("WINRM_TRANSPORT", "ntlm")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))


@pytest.fixture
def app_client(set_env, tmp_path):
    with patch("winrm_client.test_connection", return_value=True), \
         patch("winrm_client.execute_script", return_value=("Service Running\n", "", 0)):
        import importlib
        import app as app_module
        import db
        import config as config_module
        importlib.reload(db)
        importlib.reload(config_module)
        importlib.reload(app_module)
        db.init_db()
        app_module.flask_app.config["TESTING"] = True
        with app_module.flask_app.test_client() as client:
            yield client
