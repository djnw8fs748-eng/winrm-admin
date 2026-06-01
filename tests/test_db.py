import pytest
import json
import importlib


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import db
    importlib.reload(db)
    db.init_db()
    return db


def test_save_and_retrieve_run(tmp_db):
    tmp_db.save_run(
        vm_name="dc01", vm_ip="192.168.1.10",
        script_id="services/restart_service", script_name="Restart Service",
        parameters={"service_name": "Spooler"},
        status="success", stdout="Service restarted", stderr=""
    )
    runs = tmp_db.get_runs()
    assert len(runs) == 1
    assert runs[0]["vm_name"] == "dc01"
    assert runs[0]["status"] == "success"
    assert runs[0]["stdout"] == "Service restarted"


def test_get_runs_filters_by_vm(tmp_db):
    tmp_db.save_run("dc01", "192.168.1.10", "services/restart", "Restart", {}, "success", "ok", "")
    tmp_db.save_run("ws1", "192.168.1.20", "network/ping", "Ping", {}, "success", "ok", "")
    runs = tmp_db.get_runs(vm_name="dc01")
    assert len(runs) == 1
    assert runs[0]["vm_name"] == "dc01"


def test_get_runs_filters_by_category(tmp_db):
    tmp_db.save_run("dc01", "192.168.1.10", "services/restart", "Restart", {}, "success", "", "")
    tmp_db.save_run("dc01", "192.168.1.10", "network/ping", "Ping", {}, "success", "", "")
    runs = tmp_db.get_runs(category="services")
    assert len(runs) == 1
    assert "services" in runs[0]["script_id"]


def test_get_run_by_id(tmp_db):
    tmp_db.save_run("dc01", "192.168.1.10", "services/restart", "Restart", {}, "failed", "", "err")
    runs = tmp_db.get_runs()
    run_id = runs[0]["id"]
    run = tmp_db.get_run(run_id)
    assert run["id"] == run_id
    assert run["status"] == "failed"
    assert run["stderr"] == "err"


def test_get_run_returns_none_for_missing(tmp_db):
    result = tmp_db.get_run(9999)
    assert result is None


def test_parameters_stored_as_json(tmp_db):
    params = {"service_name": "Spooler", "timeout": "30"}
    tmp_db.save_run("dc01", "192.168.1.10", "services/restart", "Restart", params, "success", "", "")
    run = tmp_db.get_runs()[0]
    assert json.loads(run["parameters"]) == params
