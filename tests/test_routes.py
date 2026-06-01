import pytest
from unittest.mock import patch
from pathlib import Path


def test_dashboard_returns_200(app_client):
    response = app_client.get("/")
    assert response.status_code == 200
    assert b"dc01" in response.data


def test_dashboard_with_vm_param(app_client):
    response = app_client.get("/?vm=dc01")
    assert response.status_code == 200


def test_scripts_page_returns_200(app_client):
    response = app_client.get("/scripts?vm=dc01")
    assert response.status_code == 200


def test_run_form_get_returns_200(app_client):
    with patch("app.get_script") as mock_get:
        mock_get.return_value = {
            "id": "restart_service",
            "name": "Restart Service",
            "description": "Restarts a service",
            "category": "services",
            "os_target": "all",
            "parameters": [
                {"name": "service_name", "label": "Service Name", "type": "text", "required": True}
            ],
            "script": "Restart-Service -Name {{ service_name }}",
        }
        response = app_client.get("/scripts/services/restart_service/run?vm=dc01")
        assert response.status_code == 200
        assert b"Service Name" in response.data


def test_run_form_post_executes_and_saves(app_client):
    with patch("app.get_script") as mock_get, \
         patch("winrm_client.execute_script", return_value=("Service restarted\n", "", 0)):
        mock_get.return_value = {
            "id": "restart_service",
            "name": "Restart Service",
            "description": "Restarts a service",
            "category": "services",
            "os_target": "all",
            "parameters": [
                {"name": "service_name", "label": "Service Name", "type": "text", "required": True}
            ],
            "script": "Restart-Service -Name {{ service_name }}",
        }
        response = app_client.post(
            "/scripts/services/restart_service/run",
            data={"vm": "dc01", "service_name": "Spooler"},
        )
        assert response.status_code == 200
        assert b"Service restarted" in response.data


def test_run_form_post_missing_required_shows_error(app_client):
    with patch("app.get_script") as mock_get:
        mock_get.return_value = {
            "id": "restart_service",
            "name": "Restart Service",
            "description": "desc",
            "category": "services",
            "os_target": "all",
            "parameters": [
                {"name": "service_name", "label": "Service Name", "type": "text", "required": True}
            ],
            "script": "Restart-Service -Name {{ service_name }}",
        }
        response = app_client.post(
            "/scripts/services/restart_service/run",
            data={"vm": "dc01", "service_name": ""},
        )
        assert response.status_code == 200
        assert b"required" in response.data.lower()


def test_history_page_returns_200(app_client):
    response = app_client.get("/history")
    assert response.status_code == 200


def test_run_form_404_for_missing_script(app_client):
    with patch("app.get_script", return_value=None):
        response = app_client.get("/scripts/services/nonexistent/run?vm=dc01")
        assert response.status_code == 404


def test_vm_status_api_returns_json(app_client):
    with patch("winrm_client.test_connection", return_value=True):
        response = app_client.get("/api/vm/dc01/status")
        assert response.status_code == 200
        data = response.get_json()
        assert data["connected"] is True
