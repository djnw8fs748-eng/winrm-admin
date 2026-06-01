# WinRM Admin Tool — Design Spec
**Date:** 2026-06-01  
**Status:** Approved

---

## Overview

A Dockerised web application that sends PowerShell commands to remote Windows virtual machines via WinRM. It provides a browser-based UI with a preloaded library of administrative scripts, dynamic variable input forms, multi-VM targeting, and a persistent run history log.

---

## Architecture

Single Docker container running Flask + pywinrm. Docker Compose manages the container and mounts an `.env` file for credentials and VM configuration.

```
winrm-admin/
├── docker-compose.yml
├── .env                          ← VM hostnames, IPs, OS tags, credentials
├── Dockerfile
├── app/
│   ├── main.py                   ← Flask app entry point
│   ├── winrm_client.py           ← WinRM connection and execution logic
│   ├── db.py                     ← SQLite run history interface
│   ├── scripts/                  ← YAML script definitions
│   │   ├── services/
│   │   │   ├── restart_service.yml
│   │   │   ├── stop_service.yml
│   │   │   ├── start_service.yml
│   │   │   └── list_services.yml
│   │   ├── iis/
│   │   │   ├── recycle_apppool.yml
│   │   │   ├── stop_apppool.yml
│   │   │   ├── start_apppool.yml
│   │   │   └── list_apppools.yml
│   │   ├── processes/
│   │   │   ├── kill_process.yml
│   │   │   ├── kill_relaunch_process.yml
│   │   │   └── list_processes.yml
│   │   └── network/
│   │       ├── ping_host.yml
│   │       ├── check_port.yml
│   │       ├── flush_dns.yml
│   │       └── get_adapter_info.yml
│   ├── templates/                ← Jinja2 HTML templates
│   └── static/                   ← CSS and JS assets
└── data/
    └── history.db                ← SQLite database (mounted as Docker volume)
```

---

## VM Configuration

VMs are defined in `.env` as a comma-separated list with name, IP, and OS tag:

```env
VM_HOSTS=dc01:192.168.1.10:server2019,workstation1:192.168.1.20:win11

# Shared credentials (or override per-VM if needed)
WINRM_USERNAME=Administrator
WINRM_PASSWORD=yourpassword
WINRM_PORT=5985
WINRM_TRANSPORT=ntlm
```

At startup the app parses `VM_HOSTS` and refuses to start if required fields are missing, printing a clear error listing what is absent.

---

## Script Library

### YAML Format

Each script is a `.yml` file that declares its metadata, parameters, OS target, and PowerShell body:

```yaml
name: Restart Windows Service
description: Stops and restarts a named Windows service
category: services
os_target: all          # values: server2019 | win11 | all
parameters:
  - name: service_name
    label: Service Name
    type: text
    required: true
    placeholder: e.g. Spooler, W32Time
  - name: timeout_seconds
    label: Timeout (seconds)
    type: number
    required: false
    default: 30
script: |
  $svc = Get-Service -Name "{{ service_name }}" -ErrorAction Stop
  Restart-Service -Name "{{ service_name }}" -Force
  Start-Sleep -Seconds {{ timeout_seconds }}
  $svc.Refresh()
  Write-Output "Service status: $($svc.Status)"
```

Parameter values are validated server-side against their declared type before substitution. No raw user input is interpolated directly into PowerShell — all values go through a sanitisation step that escapes special characters.

### Preloaded Scripts

| Script | Category | OS Target |
|---|---|---|
| Restart Service | services | all |
| Stop Service | services | all |
| Start Service | services | all |
| List Running Services | services | all |
| Recycle IIS App Pool | iis | server2019 |
| Stop IIS App Pool | iis | server2019 |
| Start IIS App Pool | iis | server2019 |
| List IIS App Pools | iis | server2019 |
| Kill Process by Name | processes | all |
| Kill and Relaunch Process | processes | all |
| List Running Processes | processes | all |
| Ping Host | network | all |
| Check Port Open | network | all |
| Flush DNS | network | all |
| Get Network Adapter Info | network | all |
| Get Recent Event Log Errors | system | all |
| List Logged-on Users | system | all |
| Get Disk Space Summary | system | all |
| Restart Explorer | system | win11 |
| Clear Windows Update Cache | system | win11 |
| Get App Package Info (winget) | system | win11 |

---

## Web UI

All pages are server-rendered with Jinja2. No JavaScript framework required.

### `/` — Dashboard
- Dropdown to select target VM (displays name, IP, OS tag)
- Connection status indicator (green/red) tested with a lightweight WinRM ping on VM selection
- Quick-launch buttons for the most common scripts (restart service, kill process, ping)
- Links to script library and run history

### `/scripts` — Script Library
- Scripts grouped by category (Services, IIS, Processes, Network, System)
- Automatically filtered to the selected VM's OS tag
- Each entry shows name and description; click to open the run form

### `/scripts/<script-id>/run` — Run Form
- VM selector (pre-filled from dashboard selection)
- Dynamically rendered input fields generated from YAML parameter definitions
- Required fields enforced client-side (HTML5) and server-side before execution
- "Run" button submits the form, executes via WinRM, and displays output in a scrollable terminal-style box
- Result (success/failure) and full output auto-saved to run history on completion

### `/history` — Run History
- Table columns: timestamp, VM, script name, status (success/fail)
- Click any row to expand and view full stdout/stderr output
- Filterable by VM and script category
- No auto-purge by default

---

## Error Handling

### WinRM Connection Failures
- `pywinrm` exceptions are caught and surfaced as a clear UI error message (e.g. "Could not connect to `dc01` — check WinRM is enabled and credentials are correct")
- Connection is tested on VM selection so failures are surfaced before a script is run

### Script Execution Failures
- Non-zero PowerShell exit codes or stderr output mark the run as **failed** in history
- Full stdout and stderr are always captured, stored, and displayed — errors are never silently swallowed
- Error output is displayed in red in the terminal output box

### Input Validation
- Required fields are checked server-side before the script is executed
- Typed parameters are validated against their declared type
- All user-supplied values are sanitised before PowerShell substitution

### Startup
- Missing required `.env` fields cause the app to exit immediately with a descriptive error listing what is missing

---

## Data Model

SQLite database mounted as a Docker volume at `./data/history.db`.

```sql
CREATE TABLE runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp   DATETIME NOT NULL,
  vm_name     TEXT NOT NULL,
  vm_ip       TEXT NOT NULL,
  script_id   TEXT NOT NULL,
  script_name TEXT NOT NULL,
  parameters  TEXT NOT NULL,  -- JSON
  status      TEXT NOT NULL,  -- 'success' | 'failed'
  stdout      TEXT,
  stderr      TEXT
);
```

Docker Compose volume mount:

```yaml
volumes:
  - ./data/history.db:/app/history.db
```

---

## Docker Compose

```yaml
version: "3.9"
services:
  winrm-admin:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

---

## Out of Scope

- User authentication for the web UI (single-user/trusted-network assumption)
- Role-based access control
- Script editor UI (scripts are managed as files)
- Scheduled/recurring script execution
