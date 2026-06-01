"""
Integration tests — real WinRM pipeline against localhost.

Required env vars (set by GH Actions workflow or exported locally):
  VM_HOSTS=localhost:127.0.0.1:server2019,win11vm:127.0.0.1:win11
  WINRM_USERNAME=winrmtest
  WINRM_PASSWORD=WinRMTest123!
  WINRM_PORT=5985
  WINRM_TRANSPORT=ntlm

Run locally (Windows only, WinRM configured):
  pytest tests/integration/ -v
"""


def test_dashboard_loads(client):
    resp = client.get("/?vm=localhost")
    assert resp.status_code == 200
    assert b"localhost" in resp.data


def test_script_library_loads_for_server2019(client):
    resp = client.get("/scripts?vm=localhost")
    assert resp.status_code == 200
    assert b"List Running Services" in resp.data


def test_list_processes_real_ps(client):
    resp = client.post(
        "/scripts/processes/list_processes/run",
        data={"vm": "localhost", "name_filter": "*"},
    )
    assert resp.status_code == 200
    data = resp.data.lower()
    # At minimum some process must appear; svchost always runs on Windows Server
    assert b"svchost" in data or b"python" in data or b"success" in data


def test_ping_localhost(client):
    resp = client.post(
        "/scripts/network/ping_host/run",
        data={"vm": "localhost", "target": "127.0.0.1", "count": "2"},
    )
    assert resp.status_code == 200
    assert b"127.0.0.1" in resp.data


def test_check_winrm_port_open(client):
    # WinRM is running on port 5985 — should report TcpTestSucceeded: True
    resp = client.post(
        "/scripts/network/check_port/run",
        data={"vm": "localhost", "target": "127.0.0.1", "port": "5985"},
    )
    assert resp.status_code == 200
    assert b"True" in resp.data


def test_disk_space_returns_drives(client):
    resp = client.post(
        "/scripts/system/disk_space/run",
        data={"vm": "localhost"},
    )
    assert resp.status_code == 200
    # C: drive is always present on Windows Server
    assert b"C:" in resp.data


def test_list_services_includes_winrm(client):
    resp = client.post(
        "/scripts/services/list_services/run",
        data={"vm": "localhost"},
    )
    assert resp.status_code == 200
    # WinRM service must be running (we just configured it)
    assert b"WinRM" in resp.data or b"winrm" in resp.data.lower()


def test_flush_dns_succeeds(client):
    resp = client.post(
        "/scripts/network/flush_dns/run",
        data={"vm": "localhost"},
    )
    assert resp.status_code == 200
    # "DNS" appears in ipconfig /flushdns output on all Windows locales
    assert b"dns" in resp.data.lower()


def test_failed_execution_marked_in_db(client):
    """Restart a nonexistent service — PS throws, run is saved as failed."""
    resp = client.post(
        "/scripts/services/restart_service/run",
        data={"vm": "localhost", "service_name": "NonExistentServiceXYZ999"},
    )
    assert resp.status_code == 200
    data = resp.data.lower()
    # Either the failed badge or the error output must appear
    assert b"failed" in data or b"error" in data or b"cannot find" in data


def test_failed_run_appears_in_history(client):
    """The failed restart_service run must be visible in /history."""
    hist = client.get("/history")
    assert hist.status_code == 200
    assert b"Restart Service" in hist.data


def test_flush_dns_run_appears_in_history(client):
    """The flush_dns run from test_flush_dns_succeeds must be in /history."""
    hist = client.get("/history")
    assert hist.status_code == 200
    assert b"Flush DNS" in hist.data


def test_history_filter_shows_no_runs_for_win11vm(client):
    """win11vm was never used in any POST — filtered history must be empty."""
    hist = client.get("/history?vm=win11vm")
    assert hist.status_code == 200
    assert b"No runs recorded" in hist.data


def test_os_filter_excludes_iis_for_win11(client):
    resp = client.get("/scripts?vm=win11vm")
    assert resp.status_code == 200
    assert b"Recycle IIS App Pool" not in resp.data
    assert b"List IIS App Pools" not in resp.data


def test_os_filter_includes_iis_for_server2019(client):
    resp = client.get("/scripts?vm=localhost")
    assert resp.status_code == 200
    assert b"Recycle IIS App Pool" in resp.data


def test_injection_chars_handled_safely(client):
    """Injection attempt in name_filter must not crash the app."""
    resp = client.post(
        "/scripts/processes/list_processes/run",
        data={"vm": "localhost", "name_filter": "'; rm -rf /"},
    )
    # App must return 200 — sanitizer wraps the value in single quotes safely
    assert resp.status_code == 200
