# CI Integration Tests — Design Spec
**Date:** 2026-06-01  
**Status:** Approved

---

## Overview

Two GitHub Actions jobs that provide end-to-end confidence in the winrm-admin app at different layers:

1. **`docker-build`** — proves the Linux Docker image builds, all deps install, and all routes serve HTTP 200
2. **`integration`** — proves the full Python pipeline works against real PowerShell via WinRM on a Windows runner

Both jobs run on every push and pull request. They are independent — neither depends on the other.

---

## Job 1: docker-build (ubuntu-latest)

### Steps

1. Checkout
2. `docker build -t winrm-admin:test .`
3. `docker run -d` with dummy env vars (`VM_HOSTS=test:127.0.0.1:server2019`, fake credentials)
4. `sleep 5` for startup
5. `curl -sf` each route — any non-200 fails the job
6. `docker exec` script count check — asserts all 20 scripts loaded
7. `docker logs` on failure (always)
8. `docker stop && docker rm` cleanup (always)

### Routes tested

| Endpoint | Expected |
|---|---|
| `GET /` | 200 |
| `GET /scripts` | 200 |
| `GET /history` | 200 |
| `GET /api/vm/test/status` | 200, `{"connected": false}` |

### Script count check

```bash
docker exec winrm-admin-test python -c "
from script_loader import load_all_scripts
t = sum(len(v) for v in load_all_scripts().values())
assert t == 20, f'Expected 20 scripts, got {t}'
print(f'OK: {t} scripts loaded')
"
```

---

## Job 2: integration (windows-latest)

### WinRM Setup (PowerShell steps)

```powershell
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Service\Auth\Basic -Value $true
Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value $true
$password = ConvertTo-SecureString "WinRMTest123!" -AsPlainText -Force
New-LocalUser -Name "winrmtest" -Password $password
Add-LocalGroupMember -Group "Administrators" -Member "winrmtest"
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
Restart-Service WinRM
```

### Environment

```
VM_HOSTS=localhost:127.0.0.1:server2019
WINRM_USERNAME=winrmtest
WINRM_PASSWORD=WinRMTest123!
WINRM_PORT=5985
WINRM_TRANSPORT=ntlm
```

A second VM entry is added for win11 OS-filter tests:
```
VM_HOSTS=localhost:127.0.0.1:server2019,win11vm:127.0.0.1:win11
```

### Test Files

```
tests/integration/
  __init__.py
  conftest.py       ← session-scoped Flask client, real WinRM, real DB
  test_full_pipeline.py
```

### conftest.py design

- Session-scoped `integration_app` fixture — reloads `db`, `config`, `app` modules with real env vars, inits DB in `tmp_path_factory` temp dir
- Session-scoped `client` fixture — Flask test client over `integration_app`
- No mocking of `winrm_client`

### Test Coverage

| Test | Script | What it verifies |
|---|---|---|
| `test_dashboard_loads` | `GET /?vm=localhost` | 200, VM name in response |
| `test_list_processes_real_ps` | `list_processes` (name_filter=*) | stdout contains process names, status=success |
| `test_ping_localhost` | `ping_host` (target=127.0.0.1, count=2) | `127.0.0.1` in output |
| `test_check_winrm_port_open` | `check_port` (target=127.0.0.1, port=5985) | `True` in output |
| `test_disk_space_returns_drives` | `disk_space` | `C` in output |
| `test_list_services_includes_winrm` | `list_services` | `WinRM` in output |
| `test_flush_dns_succeeds` | `flush_dns` | status=success, saved to DB |
| `test_failed_execution_marked_in_db` | `restart_service` (nonexistent service) | status=failed, error in output, saved to history |
| `test_run_appears_in_history` | `flush_dns` then `GET /history` | run visible in history table |
| `test_history_filter_by_vm` | 2 scripts on different VMs | filter returns correct subset |
| `test_os_filter_excludes_iis_for_win11` | `GET /scripts?vm=win11vm` | IIS scripts absent |
| `test_os_filter_includes_iis_for_server2019` | `GET /scripts?vm=localhost` | IIS scripts present |
| `test_injection_chars_handled_safely` | `list_processes` with `name_filter="'; rm -rf /"` | 200 response, no crash |

IIS scripts and win11-specific scripts are **not executed** (bare runner has no IIS/win11 OS) — only their appearance in the filtered script library is verified.

---

## New Files

| File | Purpose |
|---|---|
| `.github/workflows/ci.yml` | Both CI jobs |
| `tests/integration/__init__.py` | Package marker |
| `tests/integration/conftest.py` | Session-scoped fixtures |
| `tests/integration/test_full_pipeline.py` | 13 integration tests |

---

## Out of Scope

- IIS script execution (requires IIS feature install)
- win11-specific script execution (runner is Windows Server 2022)
- Performance or load testing
- Deployment steps
