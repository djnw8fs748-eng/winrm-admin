# WinRM Admin Tool — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Dockerised Flask web app that runs preloaded PowerShell scripts on remote Windows VMs via WinRM, with a browser UI, dynamic parameter forms, and persistent run history.

**Architecture:** Single Flask container using pywinrm for WinRM connections. Scripts are YAML files that define parameters and PS body. SQLite stores run history. All pages are server-rendered with Jinja2.

**Tech Stack:** Python 3.11, Flask 3.0, pywinrm 0.4, PyYAML 6.0, Jinja2 3.1, SQLite, Docker, pytest, pytest-flask

---

## File Map

| File | Responsibility |
|---|---|
| `app.py` | Flask app creation, all routes |
| `config.py` | Parse and validate `.env`, expose VM list and credentials |
| `sanitizer.py` | Validate parameter types, escape text values for PS injection safety |
| `script_loader.py` | Load YAML scripts, filter by OS tag, render PS template |
| `db.py` | SQLite init, save run, query history |
| `winrm_client.py` | WinRM session, execute PS script, test connection |
| `scripts/<category>/*.yml` | Preloaded script definitions |
| `templates/*.html` | Jinja2 HTML templates |
| `static/style.css` | App styling |
| `tests/conftest.py` | Pytest fixtures (Flask test client, temp DB) |
| `tests/test_config.py` | Config parsing and validation |
| `tests/test_sanitizer.py` | Input validation and escaping |
| `tests/test_script_loader.py` | YAML loading, OS filtering, rendering |
| `tests/test_db.py` | Run history CRUD |
| `tests/test_routes.py` | Route responses via Flask test client |

**YAML convention:** Text parameter values are injected by the sanitizer already wrapped in PS single quotes (e.g. `'Spooler'`). YAML script bodies must NOT add quotes around `{{ variable }}` for text params. Number params are injected as raw validated numbers.

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `data/.gitkeep`
- Create: `tests/__init__.py`
- Create: `scripts/.gitkeep`

- [ ] **Step 1: Create requirements.txt**

```
Flask==3.0.3
pywinrm==0.4.3
PyYAML==6.0.1
Jinja2==3.1.4
pytest==8.2.0
pytest-flask==1.3.0
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
```

- [ ] **Step 3: Create docker-compose.yml**

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

- [ ] **Step 4: Create .env.example**

```env
VM_HOSTS=dc01:192.168.1.10:server2019,workstation1:192.168.1.20:win11
WINRM_USERNAME=Administrator
WINRM_PASSWORD=changeme
WINRM_PORT=5985
WINRM_TRANSPORT=ntlm
```

- [ ] **Step 5: Create .gitignore**

```
.env
data/history.db
__pycache__/
*.pyc
.pytest_cache/
.venv/
```

- [ ] **Step 6: Create empty placeholder files**

```bash
mkdir -p data scripts tests
touch data/.gitkeep scripts/.gitkeep tests/__init__.py
```

- [ ] **Step 7: Install dependencies locally for development**

```bash
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 8: Commit**

```bash
git init
git add requirements.txt Dockerfile docker-compose.yml .env.example .gitignore data/.gitkeep scripts/.gitkeep tests/__init__.py
git commit -m "feat: project scaffold"
```

---

## Task 2: Config Module

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
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

    with pytest.raises(SystemExit):
        from config import load_config
        load_config()


def test_load_config_exits_on_missing_credentials(monkeypatch):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10:server2019")
    monkeypatch.delenv("WINRM_USERNAME", raising=False)
    monkeypatch.delenv("WINRM_PASSWORD", raising=False)

    with pytest.raises(SystemExit):
        from config import load_config
        load_config()


def test_load_config_exits_on_malformed_vm_entry(monkeypatch):
    monkeypatch.setenv("VM_HOSTS", "dc01:192.168.1.10")  # missing os_tag
    monkeypatch.setenv("WINRM_USERNAME", "Admin")
    monkeypatch.setenv("WINRM_PASSWORD", "pass")

    with pytest.raises(SystemExit):
        from config import load_config
        load_config()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write config.py**

```python
import os
import sys
from dataclasses import dataclass


@dataclass
class VM:
    name: str
    ip: str
    os_tag: str  # 'server2019' | 'win11'


@dataclass
class Config:
    vms: list
    username: str
    password: str
    port: int
    transport: str


def load_config() -> Config:
    missing = []
    vm_hosts = os.getenv("VM_HOSTS")
    username = os.getenv("WINRM_USERNAME")
    password = os.getenv("WINRM_PASSWORD")
    port = int(os.getenv("WINRM_PORT", "5985"))
    transport = os.getenv("WINRM_TRANSPORT", "ntlm")

    if not vm_hosts:
        missing.append("VM_HOSTS")
    if not username:
        missing.append("WINRM_USERNAME")
    if not password:
        missing.append("WINRM_PASSWORD")

    if missing:
        print(f"ERROR: Missing required .env fields: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    vms = []
    for entry in vm_hosts.split(","):
        parts = entry.strip().split(":")
        if len(parts) != 3:
            print(
                f"ERROR: Invalid VM_HOSTS entry '{entry}'. Format: name:ip:os_tag",
                file=sys.stderr,
            )
            sys.exit(1)
        vms.append(VM(name=parts[0], ip=parts[1], os_tag=parts[2]))

    return Config(vms=vms, username=username, password=password, port=port, transport=transport)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config module with VM parsing and startup validation"
```

---

## Task 3: Sanitizer Module

**Files:**
- Create: `sanitizer.py`
- Create: `tests/test_sanitizer.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sanitizer.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_sanitizer.py -v
```

Expected: `ModuleNotFoundError: No module named 'sanitizer'`

- [ ] **Step 3: Write sanitizer.py**

```python
class ValidationError(Exception):
    pass


def sanitize_params(parameters: list, form_data: dict) -> dict:
    """
    Validate form values against parameter definitions and escape for PowerShell.

    Text values are wrapped in single quotes with internal single quotes doubled,
    producing a safe PS single-quoted string literal.
    Number values are validated and passed through as strings.
    """
    result = {}
    for param in parameters:
        name = param["name"]
        raw = form_data.get(name, "").strip()

        if not raw:
            if param.get("required", False):
                raise ValidationError(f"'{param['label']}' is required")
            raw = str(param.get("default", ""))

        param_type = param.get("type", "text")

        if param_type == "number":
            try:
                float(raw)
            except ValueError:
                raise ValidationError(f"'{param['label']}' must be a number, got: {raw!r}")
            result[name] = raw
        else:
            escaped = raw.replace("'", "''")
            result[name] = f"'{escaped}'"

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_sanitizer.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add sanitizer.py tests/test_sanitizer.py
git commit -m "feat: input sanitizer with PS injection protection"
```

---

## Task 4: Script Loader Module

**Files:**
- Create: `script_loader.py`
- Create: `tests/test_script_loader.py`
- Create: `tests/fixtures/scripts/services/test_service.yml`

- [ ] **Step 1: Create fixture YAML for tests**

Create `tests/fixtures/scripts/services/test_service.yml`:

```yaml
name: Test Service Script
description: A script for testing
category: services
os_target: all
parameters:
  - name: service_name
    label: Service Name
    type: text
    required: true
    placeholder: e.g. Spooler
  - name: timeout
    label: Timeout
    type: number
    required: false
    default: 30
script: |
  Get-Service -Name {{ service_name }}
  Start-Sleep -Seconds {{ timeout }}
```

Create `tests/fixtures/scripts/iis/test_iis.yml`:

```yaml
name: Test IIS Script
description: IIS only script
category: iis
os_target: server2019
parameters: []
script: |
  Write-Output "IIS only"
```

Create `tests/fixtures/scripts/system/test_win11.yml`:

```yaml
name: Test Win11 Script
description: Win11 only script
category: system
os_target: win11
parameters: []
script: |
  Write-Output "Win11 only"
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_script_loader.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_script_loader.py -v
```

Expected: `ModuleNotFoundError: No module named 'script_loader'`

- [ ] **Step 4: Write script_loader.py**

```python
from pathlib import Path
from jinja2 import Environment, BaseLoader
import yaml

DEFAULT_SCRIPTS_DIR = Path(__file__).parent / "scripts"


def load_all_scripts(os_tag=None, scripts_dir=None):
    """Load all scripts grouped by category, filtered by os_tag."""
    base = Path(scripts_dir) if scripts_dir else DEFAULT_SCRIPTS_DIR
    result = {}
    for category_dir in sorted(base.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        scripts = []
        for yml_file in sorted(category_dir.glob("*.yml")):
            script = _load_yaml(yml_file)
            if script and _matches_os(script.get("os_target", "all"), os_tag):
                script["id"] = yml_file.stem
                script["category"] = category
                scripts.append(script)
        if scripts:
            result[category] = scripts
    return result


def get_script(category, script_name, scripts_dir=None):
    """Load a single script by category and filename stem."""
    base = Path(scripts_dir) if scripts_dir else DEFAULT_SCRIPTS_DIR
    path = base / category / f"{script_name}.yml"
    if not path.exists():
        return None
    script = _load_yaml(path)
    if script:
        script["id"] = script_name
        script["category"] = category
    return script


def render_script(script_body, params):
    """Render the PS script Jinja2 template with sanitized parameter values."""
    env = Environment(loader=BaseLoader())
    template = env.from_string(script_body)
    return template.render(**params)


def _load_yaml(path):
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def _matches_os(os_target, os_tag):
    if os_target == "all" or os_tag is None:
        return True
    return os_target == os_tag
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_script_loader.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add script_loader.py tests/test_script_loader.py tests/fixtures/
git commit -m "feat: script loader with YAML parsing and OS tag filtering"
```

---

## Task 5: Database Module

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_db.py`:

```python
import pytest
import os
import json
import tempfile
from db import init_db, save_run, get_runs, get_run


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    # Force reimport to pick up env var
    import importlib, db
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Write db.py**

```python
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "data/history.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   DATETIME NOT NULL,
                vm_name     TEXT NOT NULL,
                vm_ip       TEXT NOT NULL,
                script_id   TEXT NOT NULL,
                script_name TEXT NOT NULL,
                parameters  TEXT NOT NULL,
                status      TEXT NOT NULL,
                stdout      TEXT,
                stderr      TEXT
            )
        """)
        conn.commit()


def save_run(vm_name, vm_ip, script_id, script_name, parameters, status, stdout, stderr):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """INSERT INTO runs
               (timestamp, vm_name, vm_ip, script_id, script_name, parameters, status, stdout, stderr)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.utcnow().isoformat(), vm_name, vm_ip,
                script_id, script_name, json.dumps(parameters),
                status, stdout, stderr,
            ),
        )
        conn.commit()


def get_runs(vm_name=None, category=None, limit=100):
    query = "SELECT * FROM runs"
    conditions = []
    params = []
    if vm_name:
        conditions.append("vm_name = ?")
        params.append(vm_name)
    if category:
        conditions.append("script_id LIKE ?")
        params.append(f"{category}/%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_run(run_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: SQLite run history module"
```

---

## Task 6: WinRM Client Module

**Files:**
- Create: `winrm_client.py`
- Create: `tests/test_winrm_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_winrm_client.py`:

```python
import pytest
from unittest.mock import MagicMock, patch


def _make_result(stdout=b"ok\n", stderr=b"", status_code=0):
    r = MagicMock()
    r.std_out = stdout
    r.std_err = stderr
    r.status_code = status_code
    return r


def test_execute_script_returns_decoded_stdout():
    with patch("winrm_client.winrm.Session") as MockSession:
        session = MockSession.return_value
        session.run_ps.return_value = _make_result(stdout=b"Service Running\n")

        from winrm_client import execute_script
        stdout, stderr, code = execute_script("192.168.1.10", "Admin", "pass", 5985, "ntlm", "Get-Service")

        assert stdout == "Service Running\n"
        assert stderr == ""
        assert code == 0


def test_execute_script_returns_stderr_on_failure():
    with patch("winrm_client.winrm.Session") as MockSession:
        session = MockSession.return_value
        session.run_ps.return_value = _make_result(stdout=b"", stderr=b"Cannot find service\n", status_code=1)

        from winrm_client import execute_script
        stdout, stderr, code = execute_script("192.168.1.10", "Admin", "pass", 5985, "ntlm", "Bad-Command")

        assert stderr == "Cannot find service\n"
        assert code == 1


def test_test_connection_returns_true_on_success():
    with patch("winrm_client.execute_script") as mock_exec:
        mock_exec.return_value = ("ok\n", "", 0)

        from winrm_client import test_connection
        assert test_connection("192.168.1.10", "Admin", "pass", 5985, "ntlm") is True


def test_test_connection_returns_false_on_exception():
    with patch("winrm_client.execute_script") as mock_exec:
        mock_exec.side_effect = Exception("Connection refused")

        from winrm_client import test_connection
        assert test_connection("192.168.1.10", "Admin", "pass", 5985, "ntlm") is False


def test_test_connection_returns_false_on_nonzero_exit():
    with patch("winrm_client.execute_script") as mock_exec:
        mock_exec.return_value = ("", "error", 1)

        from winrm_client import test_connection
        assert test_connection("192.168.1.10", "Admin", "pass", 5985, "ntlm") is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_winrm_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'winrm_client'`

- [ ] **Step 3: Write winrm_client.py**

```python
import winrm


def execute_script(vm_ip: str, username: str, password: str, port: int, transport: str, script: str):
    """Execute a PowerShell script on a remote Windows host via WinRM.

    Returns (stdout, stderr, status_code).
    """
    session = winrm.Session(
        f"http://{vm_ip}:{port}/wsman",
        auth=(username, password),
        transport=transport,
    )
    result = session.run_ps(script)
    stdout = result.std_out.decode("utf-8", errors="replace")
    stderr = result.std_err.decode("utf-8", errors="replace")
    return stdout, stderr, result.status_code


def test_connection(vm_ip: str, username: str, password: str, port: int, transport: str) -> bool:
    """Return True if the VM is reachable and credentials are valid."""
    try:
        _, _, code = execute_script(vm_ip, username, password, port, transport, "Write-Output 'ok'")
        return code == 0
    except Exception:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_winrm_client.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add winrm_client.py tests/test_winrm_client.py
git commit -m "feat: WinRM client module"
```

---

## Task 7: Flask App and Routes

**Files:**
- Create: `app.py`
- Create: `tests/conftest.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write conftest.py with fixtures**

Create `tests/conftest.py`:

```python
import pytest
import os
from pathlib import Path
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
        importlib.reload(db)
        importlib.reload(app_module)
        db.init_db()
        app_module.flask_app.config["TESTING"] = True
        with app_module.flask_app.test_client() as client:
            yield client
```

- [ ] **Step 2: Write the failing route tests**

Create `tests/test_routes.py`:

```python
import pytest
from unittest.mock import patch
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "scripts"


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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_routes.py -v
```

Expected: `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 4: Write app.py**

```python
import os
from flask import Flask, render_template, request, jsonify
from config import load_config
from script_loader import load_all_scripts, get_script, render_script
from sanitizer import sanitize_params, ValidationError
from db import init_db, save_run, get_runs, get_run
import winrm_client

flask_app = Flask(__name__)
config = load_config()
init_db()


def _find_vm(name):
    return next((v for v in config.vms if v.name == name), None)


@flask_app.route("/")
def dashboard():
    vm_name = request.args.get("vm", config.vms[0].name if config.vms else None)
    selected_vm = _find_vm(vm_name)
    connected = False
    if selected_vm:
        connected = winrm_client.test_connection(
            selected_vm.ip, config.username, config.password, config.port, config.transport
        )
    return render_template(
        "dashboard.html", vms=config.vms, selected_vm=selected_vm, connected=connected
    )


@flask_app.route("/scripts")
def scripts():
    vm_name = request.args.get("vm")
    selected_vm = _find_vm(vm_name)
    os_tag = selected_vm.os_tag if selected_vm else None
    grouped = load_all_scripts(os_tag=os_tag)
    return render_template(
        "scripts.html", vms=config.vms, selected_vm=selected_vm, grouped=grouped
    )


@flask_app.route("/scripts/<category>/<script_name>/run", methods=["GET", "POST"])
def run_script(category, script_name):
    script = get_script(category, script_name)
    if script is None:
        return "Script not found", 404

    vm_name = request.args.get("vm") or request.form.get("vm")
    selected_vm = _find_vm(vm_name)
    output = None
    error_msg = None
    status = None

    if request.method == "POST" and selected_vm:
        try:
            params = sanitize_params(script.get("parameters", []), request.form)
            ps_script = render_script(script["script"], params)
            stdout, stderr, code = winrm_client.execute_script(
                selected_vm.ip, config.username, config.password, config.port, config.transport, ps_script
            )
            status = "success" if code == 0 else "failed"
            save_run(
                vm_name=selected_vm.name,
                vm_ip=selected_vm.ip,
                script_id=f"{category}/{script_name}",
                script_name=script["name"],
                parameters=request.form.to_dict(),
                status=status,
                stdout=stdout,
                stderr=stderr,
            )
            output = stdout
            if stderr:
                error_msg = stderr
        except ValidationError as e:
            error_msg = str(e)
        except Exception as e:
            error_msg = f"Execution failed: {e}"
            status = "failed"

    return render_template(
        "run_form.html",
        vms=config.vms,
        selected_vm=selected_vm,
        script=script,
        category=category,
        script_name=script_name,
        output=output,
        error_msg=error_msg,
        status=status,
    )


@flask_app.route("/history")
def history():
    vm_filter = request.args.get("vm")
    category_filter = request.args.get("category")
    runs = get_runs(vm_name=vm_filter, category=category_filter)
    categories = ["services", "iis", "processes", "network", "system"]
    return render_template(
        "history.html",
        vms=config.vms,
        selected_vm=_find_vm(vm_filter),
        runs=runs,
        vm_filter=vm_filter,
        category_filter=category_filter,
        categories=categories,
    )


@flask_app.route("/api/vm/<vm_name>/status")
def vm_status(vm_name):
    vm = _find_vm(vm_name)
    if vm is None:
        return jsonify({"connected": False, "error": "VM not found"}), 404
    connected = winrm_client.test_connection(
        vm.ip, config.username, config.password, config.port, config.transport
    )
    return jsonify({"connected": connected})


if __name__ == "__main__":
    flask_app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
```

- [ ] **Step 5: Run all tests**

```bash
pytest -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/conftest.py tests/test_routes.py
git commit -m "feat: Flask routes for dashboard, script library, run form, and history"
```

---

## Task 8: HTML Templates and CSS

**Files:**
- Create: `templates/base.html`
- Create: `templates/dashboard.html`
- Create: `templates/scripts.html`
- Create: `templates/run_form.html`
- Create: `templates/history.html`
- Create: `static/style.css`

- [ ] **Step 1: Create templates directory**

```bash
mkdir -p templates static
```

- [ ] **Step 2: Create templates/base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}WinRM Admin{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav class="navbar">
        <span class="nav-brand">WinRM Admin</span>
        <div class="nav-links">
            <a href="{{ url_for('dashboard') }}{% if selected_vm %}?vm={{ selected_vm.name }}{% endif %}">Dashboard</a>
            <a href="{{ url_for('scripts') }}{% if selected_vm %}?vm={{ selected_vm.name }}{% endif %}">Scripts</a>
            <a href="{{ url_for('history') }}">History</a>
        </div>
        {% if vms %}
        <form class="vm-selector" method="get" action="{{ request.path }}">
            <select name="vm" onchange="this.form.submit()">
                <option value="">Select VM...</option>
                {% for vm in vms %}
                <option value="{{ vm.name }}"
                    {% if selected_vm and selected_vm.name == vm.name %}selected{% endif %}>
                    {{ vm.name }} — {{ vm.ip }} ({{ vm.os_tag }})
                </option>
                {% endfor %}
            </select>
        </form>
        {% endif %}
    </nav>
    <main class="main-content">
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

- [ ] **Step 3: Create templates/dashboard.html**

```html
{% extends "base.html" %}
{% block title %}Dashboard — WinRM Admin{% endblock %}
{% block content %}
<div class="page-header">
    <h1>Dashboard</h1>
</div>

{% if selected_vm %}
<div class="vm-status-card">
    <div class="vm-info">
        <h2>{{ selected_vm.name }}</h2>
        <span class="vm-detail">{{ selected_vm.ip }} &bull; {{ selected_vm.os_tag }}</span>
    </div>
    <div class="status-badge {% if connected %}status-ok{% else %}status-err{% endif %}">
        {% if connected %}Connected{% else %}Unreachable{% endif %}
    </div>
</div>

<div class="quick-actions">
    <h3>Quick Actions</h3>
    <div class="action-grid">
        <a class="action-btn" href="{{ url_for('run_script', category='services', script_name='restart_service') }}?vm={{ selected_vm.name }}">
            Restart Service
        </a>
        <a class="action-btn" href="{{ url_for('run_script', category='processes', script_name='kill_process') }}?vm={{ selected_vm.name }}">
            Kill Process
        </a>
        <a class="action-btn" href="{{ url_for('run_script', category='network', script_name='ping_host') }}?vm={{ selected_vm.name }}">
            Ping Host
        </a>
        <a class="action-btn" href="{{ url_for('run_script', category='processes', script_name='list_processes') }}?vm={{ selected_vm.name }}">
            List Processes
        </a>
    </div>
</div>
{% else %}
<div class="empty-state">
    <p>Select a VM from the dropdown above to get started.</p>
</div>
{% endif %}

<div class="nav-cards">
    <a class="nav-card" href="{{ url_for('scripts') }}{% if selected_vm %}?vm={{ selected_vm.name }}{% endif %}">
        <h3>Script Library</h3>
        <p>Browse and run preloaded administrative scripts</p>
    </a>
    <a class="nav-card" href="{{ url_for('history') }}">
        <h3>Run History</h3>
        <p>View past script executions and their output</p>
    </a>
</div>
{% endblock %}
```

- [ ] **Step 4: Create templates/scripts.html**

```html
{% extends "base.html" %}
{% block title %}Scripts — WinRM Admin{% endblock %}
{% block content %}
<div class="page-header">
    <h1>Script Library</h1>
    {% if selected_vm %}
    <span class="filter-label">Showing scripts for {{ selected_vm.os_tag }}</span>
    {% endif %}
</div>

{% if not grouped %}
<div class="empty-state">
    <p>No scripts available{% if selected_vm %} for {{ selected_vm.os_tag }}{% endif %}. Select a VM to filter by OS.</p>
</div>
{% endif %}

{% for category, scripts in grouped.items() %}
<section class="script-category">
    <h2 class="category-header">{{ category | title }}</h2>
    <div class="script-list">
        {% for script in scripts %}
        <div class="script-card">
            <div class="script-info">
                <h3>{{ script.name }}</h3>
                <p>{{ script.description }}</p>
                <span class="os-badge">{{ script.os_target }}</span>
            </div>
            <a class="run-btn"
               href="{{ url_for('run_script', category=script.category, script_name=script.id) }}{% if selected_vm %}?vm={{ selected_vm.name }}{% endif %}">
                Run
            </a>
        </div>
        {% endfor %}
    </div>
</section>
{% endfor %}
{% endblock %}
```

- [ ] **Step 5: Create templates/run_form.html**

```html
{% extends "base.html" %}
{% block title %}{{ script.name }} — WinRM Admin{% endblock %}
{% block content %}
<div class="page-header">
    <a class="back-link" href="{{ url_for('scripts') }}{% if selected_vm %}?vm={{ selected_vm.name }}{% endif %}">&larr; Scripts</a>
    <h1>{{ script.name }}</h1>
    <p class="script-desc">{{ script.description }}</p>
    <span class="os-badge">{{ script.os_target }}</span>
</div>

<form class="run-form" method="post"
      action="{{ url_for('run_script', category=category, script_name=script_name) }}{% if selected_vm %}?vm={{ selected_vm.name }}{% endif %}">
    <input type="hidden" name="vm" value="{{ selected_vm.name if selected_vm else '' }}">

    <div class="form-section">
        <h2>Parameters</h2>
        {% if script.parameters %}
        {% for param in script.parameters %}
        <div class="form-group">
            <label for="{{ param.name }}">
                {{ param.label }}{% if param.required %} <span class="required-mark">*</span>{% endif %}
            </label>
            <input
                type="{{ param.type if param.type in ['text', 'number'] else 'text' }}"
                id="{{ param.name }}"
                name="{{ param.name }}"
                placeholder="{{ param.placeholder | default('') }}"
                value="{{ param.default | default('') }}"
                {% if param.required %}required{% endif %}
            >
        </div>
        {% endfor %}
        {% else %}
        <p class="no-params">This script has no parameters.</p>
        {% endif %}
    </div>

    <button type="submit" class="submit-btn" {% if not selected_vm %}disabled title="Select a VM first"{% endif %}>
        Run Script
    </button>
</form>

{% if error_msg %}
<div class="output-block output-error">
    <div class="output-header">
        <span class="output-label">Error</span>
        <span class="status-badge status-err">Failed</span>
    </div>
    <pre>{{ error_msg }}</pre>
</div>
{% endif %}

{% if output %}
<div class="output-block {% if status == 'success' %}output-success{% else %}output-error{% endif %}">
    <div class="output-header">
        <span class="output-label">Output</span>
        <span class="status-badge {% if status == 'success' %}status-ok{% else %}status-err{% endif %}">
            {{ status | title }}
        </span>
    </div>
    <pre>{{ output }}</pre>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 6: Create templates/history.html**

```html
{% extends "base.html" %}
{% block title %}History — WinRM Admin{% endblock %}
{% block content %}
<div class="page-header">
    <h1>Run History</h1>
</div>

<form class="filter-bar" method="get" action="{{ url_for('history') }}">
    <select name="vm">
        <option value="">All VMs</option>
        {% for vm in vms %}
        <option value="{{ vm.name }}" {% if vm_filter == vm.name %}selected{% endif %}>{{ vm.name }}</option>
        {% endfor %}
    </select>
    <select name="category">
        <option value="">All Categories</option>
        {% for cat in categories %}
        <option value="{{ cat }}" {% if category_filter == cat %}selected{% endif %}>{{ cat | title }}</option>
        {% endfor %}
    </select>
    <button type="submit">Filter</button>
    <a href="{{ url_for('history') }}" class="clear-link">Clear</a>
</form>

{% if runs %}
<table class="history-table">
    <thead>
        <tr>
            <th>Timestamp</th>
            <th>VM</th>
            <th>Script</th>
            <th>Status</th>
            <th>Details</th>
        </tr>
    </thead>
    <tbody>
        {% for run in runs %}
        <tr class="history-row {% if run.status == 'failed' %}row-failed{% endif %}">
            <td>{{ run.timestamp }}</td>
            <td>{{ run.vm_name }}</td>
            <td>{{ run.script_name }}</td>
            <td>
                <span class="status-badge {% if run.status == 'success' %}status-ok{% else %}status-err{% endif %}">
                    {{ run.status }}
                </span>
            </td>
            <td>
                <details>
                    <summary>View</summary>
                    <div class="run-detail">
                        <strong>Script ID:</strong> {{ run.script_id }}<br>
                        <strong>Parameters:</strong> {{ run.parameters }}<br>
                        {% if run.stdout %}
                        <strong>Output:</strong>
                        <pre>{{ run.stdout }}</pre>
                        {% endif %}
                        {% if run.stderr %}
                        <strong>Errors:</strong>
                        <pre class="stderr-output">{{ run.stderr }}</pre>
                        {% endif %}
                    </div>
                </details>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">
    <p>No runs recorded yet{% if vm_filter or category_filter %} for this filter{% endif %}.</p>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 7: Create static/style.css**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: 'Segoe UI', system-ui, sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    min-height: 100vh;
}

/* Nav */
.navbar {
    display: flex;
    align-items: center;
    gap: 2rem;
    padding: 0.75rem 2rem;
    background: #16213e;
    border-bottom: 1px solid #0f3460;
}
.nav-brand { font-size: 1.1rem; font-weight: 700; color: #4fc3f7; letter-spacing: 0.05em; }
.nav-links { display: flex; gap: 1.5rem; }
.nav-links a { color: #b0bec5; text-decoration: none; font-size: 0.9rem; }
.nav-links a:hover { color: #4fc3f7; }
.vm-selector { margin-left: auto; }
.vm-selector select {
    background: #0f3460; border: 1px solid #4fc3f7; color: #e0e0e0;
    padding: 0.35rem 0.75rem; border-radius: 4px; font-size: 0.85rem; cursor: pointer;
}

/* Main */
.main-content { max-width: 960px; margin: 2rem auto; padding: 0 1.5rem; }
.page-header { margin-bottom: 2rem; }
.page-header h1 { font-size: 1.6rem; color: #4fc3f7; margin-bottom: 0.25rem; }
.script-desc { color: #90a4ae; margin: 0.5rem 0; }
.filter-label { font-size: 0.85rem; color: #78909c; }
.back-link { color: #4fc3f7; text-decoration: none; font-size: 0.85rem; display: block; margin-bottom: 0.5rem; }

/* VM Status */
.vm-status-card {
    display: flex; align-items: center; justify-content: space-between;
    background: #16213e; border: 1px solid #0f3460; border-radius: 8px;
    padding: 1.25rem 1.5rem; margin-bottom: 2rem;
}
.vm-info h2 { font-size: 1.2rem; margin-bottom: 0.25rem; }
.vm-detail { font-size: 0.85rem; color: #78909c; }

/* Status badges */
.status-badge { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600; }
.status-ok { background: #1b5e20; color: #a5d6a7; }
.status-err { background: #b71c1c; color: #ffcdd2; }

/* Quick actions */
.quick-actions { margin-bottom: 2rem; }
.quick-actions h3 { margin-bottom: 1rem; color: #b0bec5; }
.action-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 0.75rem; }
.action-btn {
    display: block; text-align: center; padding: 0.75rem;
    background: #0f3460; border: 1px solid #4fc3f7; border-radius: 6px;
    color: #4fc3f7; text-decoration: none; font-size: 0.875rem;
    transition: background 0.15s;
}
.action-btn:hover { background: #1a5276; }

/* Nav cards */
.nav-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.nav-card {
    display: block; background: #16213e; border: 1px solid #0f3460;
    border-radius: 8px; padding: 1.25rem; text-decoration: none; color: inherit;
    transition: border-color 0.15s;
}
.nav-card:hover { border-color: #4fc3f7; }
.nav-card h3 { color: #4fc3f7; margin-bottom: 0.5rem; }
.nav-card p { font-size: 0.875rem; color: #78909c; }

/* Script list */
.script-category { margin-bottom: 2rem; }
.category-header { font-size: 1rem; color: #78909c; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.75rem; }
.script-list { display: flex; flex-direction: column; gap: 0.5rem; }
.script-card {
    display: flex; align-items: center; justify-content: space-between;
    background: #16213e; border: 1px solid #0f3460; border-radius: 6px; padding: 1rem 1.25rem;
}
.script-info h3 { font-size: 0.95rem; margin-bottom: 0.25rem; }
.script-info p { font-size: 0.8rem; color: #78909c; }
.os-badge { font-size: 0.7rem; background: #0f3460; color: #4fc3f7; padding: 0.1rem 0.4rem; border-radius: 3px; }
.run-btn {
    padding: 0.4rem 1rem; background: #0f3460; border: 1px solid #4fc3f7;
    border-radius: 4px; color: #4fc3f7; text-decoration: none; font-size: 0.85rem; white-space: nowrap;
}
.run-btn:hover { background: #1a5276; }

/* Run form */
.run-form { background: #16213e; border: 1px solid #0f3460; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }
.form-section h2 { font-size: 1rem; color: #b0bec5; margin-bottom: 1rem; }
.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-size: 0.875rem; color: #90a4ae; margin-bottom: 0.4rem; }
.required-mark { color: #ef5350; }
.form-group input {
    width: 100%; padding: 0.5rem 0.75rem;
    background: #0f3460; border: 1px solid #37474f; border-radius: 4px;
    color: #e0e0e0; font-size: 0.9rem;
}
.form-group input:focus { outline: none; border-color: #4fc3f7; }
.no-params { color: #546e7a; font-size: 0.875rem; }
.submit-btn {
    margin-top: 1rem; padding: 0.6rem 1.5rem;
    background: #4fc3f7; color: #1a1a2e; border: none; border-radius: 4px;
    font-size: 0.9rem; font-weight: 600; cursor: pointer;
}
.submit-btn:hover { background: #81d4fa; }
.submit-btn:disabled { background: #37474f; color: #546e7a; cursor: not-allowed; }

/* Output */
.output-block { border-radius: 6px; margin-bottom: 1rem; overflow: hidden; }
.output-success { border: 1px solid #2e7d32; }
.output-error { border: 1px solid #c62828; }
.output-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 1rem; background: rgba(0,0,0,0.3);
}
.output-label { font-size: 0.8rem; color: #90a4ae; text-transform: uppercase; letter-spacing: 0.05em; }
.output-block pre {
    padding: 1rem; font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 0.825rem; line-height: 1.5; overflow-x: auto; white-space: pre-wrap; word-break: break-word;
}

/* History */
.filter-bar { display: flex; gap: 0.75rem; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; }
.filter-bar select {
    background: #0f3460; border: 1px solid #37474f; color: #e0e0e0;
    padding: 0.35rem 0.75rem; border-radius: 4px; font-size: 0.85rem;
}
.filter-bar button {
    padding: 0.35rem 0.9rem; background: #4fc3f7; color: #1a1a2e;
    border: none; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 600;
}
.clear-link { color: #78909c; font-size: 0.85rem; text-decoration: none; }
.history-table { width: 100%; border-collapse: collapse; }
.history-table th {
    text-align: left; padding: 0.6rem 1rem; font-size: 0.8rem;
    color: #78909c; text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 1px solid #0f3460;
}
.history-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #0f3460; font-size: 0.875rem; }
.history-row:hover td { background: #16213e; }
.row-failed td { background: rgba(183, 28, 28, 0.05); }
.run-detail { margin-top: 0.75rem; font-size: 0.8rem; line-height: 1.8; color: #90a4ae; }
.run-detail pre { background: #0f3460; padding: 0.5rem; border-radius: 4px; margin-top: 0.25rem; white-space: pre-wrap; }
.stderr-output { color: #ffcdd2; }
details summary { cursor: pointer; color: #4fc3f7; font-size: 0.85rem; }

/* Empty state */
.empty-state { text-align: center; padding: 3rem; color: #546e7a; }
```

- [ ] **Step 8: Run a quick smoke test (requires .env)**

```bash
# Only run this if you have a .env file configured
# python app.py
# Then open http://localhost:5000 in a browser
echo "Templates and CSS written. Smoke test after docker build in Task 11."
```

- [ ] **Step 9: Commit**

```bash
git add templates/ static/
git commit -m "feat: Jinja2 templates and CSS styling"
```

---

## Task 9: YAML Scripts — Services and System

**Files:** (all Create)
- `scripts/services/restart_service.yml`
- `scripts/services/stop_service.yml`
- `scripts/services/start_service.yml`
- `scripts/services/list_services.yml`
- `scripts/system/event_log_errors.yml`
- `scripts/system/logged_on_users.yml`
- `scripts/system/disk_space.yml`
- `scripts/system/restart_explorer.yml`
- `scripts/system/clear_wu_cache.yml`

- [ ] **Step 1: Create scripts/services/ directory and scripts**

```bash
mkdir -p scripts/services scripts/system
```

Create `scripts/services/restart_service.yml`:
```yaml
name: Restart Service
description: Stops and restarts a named Windows service and reports its final state.
category: services
os_target: all
parameters:
  - name: service_name
    label: Service Name
    type: text
    required: true
    placeholder: e.g. Spooler, W32Time, wuauserv
script: |
  $svc = Get-Service -Name {{ service_name }} -ErrorAction Stop
  Restart-Service -Name {{ service_name }} -Force
  Start-Sleep -Seconds 2
  $svc.Refresh()
  Write-Output "Status: $($svc.Status)"
```

Create `scripts/services/stop_service.yml`:
```yaml
name: Stop Service
description: Stops a named Windows service and confirms it has stopped.
category: services
os_target: all
parameters:
  - name: service_name
    label: Service Name
    type: text
    required: true
    placeholder: e.g. Spooler
script: |
  Stop-Service -Name {{ service_name }} -Force -ErrorAction Stop
  $svc = Get-Service -Name {{ service_name }}
  Write-Output "Status: $($svc.Status)"
```

Create `scripts/services/start_service.yml`:
```yaml
name: Start Service
description: Starts a named Windows service and confirms it is running.
category: services
os_target: all
parameters:
  - name: service_name
    label: Service Name
    type: text
    required: true
    placeholder: e.g. Spooler
script: |
  Start-Service -Name {{ service_name }} -ErrorAction Stop
  $svc = Get-Service -Name {{ service_name }}
  Write-Output "Status: $($svc.Status)"
```

Create `scripts/services/list_services.yml`:
```yaml
name: List Running Services
description: Lists all currently running Windows services sorted by name.
category: services
os_target: all
parameters: []
script: |
  Get-Service | Where-Object { $_.Status -eq 'Running' } |
    Sort-Object DisplayName |
    Select-Object Name, DisplayName, Status |
    Format-Table -AutoSize |
    Out-String
```

- [ ] **Step 2: Create system scripts**

Create `scripts/system/event_log_errors.yml`:
```yaml
name: Get Recent Event Log Errors
description: Retrieves the most recent error and critical events from the System event log.
category: system
os_target: all
parameters:
  - name: count
    label: Number of Events
    type: number
    required: false
    default: 20
script: |
  Get-EventLog -LogName System -EntryType Error,Warning -Newest {{ count }} |
    Select-Object TimeGenerated, EntryType, Source, Message |
    Format-List |
    Out-String
```

Create `scripts/system/logged_on_users.yml`:
```yaml
name: List Logged-On Users
description: Shows all users currently logged on to the machine.
category: system
os_target: all
parameters: []
script: |
  query user 2>&1
```

Create `scripts/system/disk_space.yml`:
```yaml
name: Get Disk Space
description: Reports free and total disk space for all local fixed drives.
category: system
os_target: all
parameters: []
script: |
  Get-PSDrive -PSProvider FileSystem |
    Select-Object Name,
      @{N='Used(GB)';E={[math]::Round($_.Used/1GB,2)}},
      @{N='Free(GB)';E={[math]::Round($_.Free/1GB,2)}},
      @{N='Total(GB)';E={[math]::Round(($_.Used+$_.Free)/1GB,2)}} |
    Format-Table -AutoSize |
    Out-String
```

Create `scripts/system/restart_explorer.yml`:
```yaml
name: Restart Explorer
description: Kills and relaunches Windows Explorer (fixes unresponsive taskbar/desktop on Windows 11).
category: system
os_target: win11
parameters: []
script: |
  Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
  Start-Process explorer
  Write-Output "Explorer restarted."
```

Create `scripts/system/clear_wu_cache.yml`:
```yaml
name: Clear Windows Update Cache
description: Stops Windows Update services, clears the download cache, and restarts the services.
category: system
os_target: win11
parameters: []
script: |
  Stop-Service -Name wuauserv, bits, cryptsvc -Force
  Remove-Item -Path "$env:SystemRoot\SoftwareDistribution\*" -Recurse -Force -ErrorAction SilentlyContinue
  Start-Service -Name cryptsvc, bits, wuauserv
  Write-Output "Windows Update cache cleared and services restarted."
```

- [ ] **Step 3: Commit**

```bash
git add scripts/services/ scripts/system/
git commit -m "feat: preloaded service and system YAML scripts"
```

---

## Task 10: YAML Scripts — IIS, Processes, and Network

**Files:** (all Create)
- `scripts/iis/recycle_apppool.yml`
- `scripts/iis/stop_apppool.yml`
- `scripts/iis/start_apppool.yml`
- `scripts/iis/list_apppools.yml`
- `scripts/processes/kill_process.yml`
- `scripts/processes/kill_relaunch_process.yml`
- `scripts/processes/list_processes.yml`
- `scripts/network/ping_host.yml`
- `scripts/network/check_port.yml`
- `scripts/network/flush_dns.yml`
- `scripts/network/get_adapter_info.yml`

- [ ] **Step 1: Create IIS scripts**

```bash
mkdir -p scripts/iis
```

Create `scripts/iis/recycle_apppool.yml`:
```yaml
name: Recycle IIS App Pool
description: Recycles a named IIS application pool to clear its worker process.
category: iis
os_target: server2019
parameters:
  - name: pool_name
    label: App Pool Name
    type: text
    required: true
    placeholder: e.g. DefaultAppPool
script: |
  Import-Module WebAdministration
  Restart-WebAppPool -Name {{ pool_name }}
  Write-Output "App pool '{{ pool_name }}' recycled."
```

Create `scripts/iis/stop_apppool.yml`:
```yaml
name: Stop IIS App Pool
description: Stops a named IIS application pool.
category: iis
os_target: server2019
parameters:
  - name: pool_name
    label: App Pool Name
    type: text
    required: true
    placeholder: e.g. DefaultAppPool
script: |
  Import-Module WebAdministration
  Stop-WebAppPool -Name {{ pool_name }}
  $state = (Get-WebAppPoolState -Name {{ pool_name }}).Value
  Write-Output "App pool state: $state"
```

Create `scripts/iis/start_apppool.yml`:
```yaml
name: Start IIS App Pool
description: Starts a named IIS application pool.
category: iis
os_target: server2019
parameters:
  - name: pool_name
    label: App Pool Name
    type: text
    required: true
    placeholder: e.g. DefaultAppPool
script: |
  Import-Module WebAdministration
  Start-WebAppPool -Name {{ pool_name }}
  $state = (Get-WebAppPoolState -Name {{ pool_name }}).Value
  Write-Output "App pool state: $state"
```

Create `scripts/iis/list_apppools.yml`:
```yaml
name: List IIS App Pools
description: Lists all IIS application pools and their current state.
category: iis
os_target: server2019
parameters: []
script: |
  Import-Module WebAdministration
  Get-ChildItem IIS:\AppPools |
    Select-Object Name, State, ManagedRuntimeVersion, Enable32BitAppOnWin64 |
    Format-Table -AutoSize |
    Out-String
```

- [ ] **Step 2: Create process scripts**

```bash
mkdir -p scripts/processes
```

Create `scripts/processes/kill_process.yml`:
```yaml
name: Kill Process
description: Kills all running instances of a process by name.
category: processes
os_target: all
parameters:
  - name: process_name
    label: Process Name
    type: text
    required: true
    placeholder: e.g. notepad, chrome
script: |
  $procs = Get-Process -Name {{ process_name }} -ErrorAction SilentlyContinue
  if ($procs) {
    $procs | Stop-Process -Force
    Write-Output "Killed $($procs.Count) instance(s) of '{{ process_name }}'."
  } else {
    Write-Output "No running instances of '{{ process_name }}' found."
  }
```

Create `scripts/processes/kill_relaunch_process.yml`:
```yaml
name: Kill and Relaunch Process
description: Kills all instances of a process then relaunches the executable from the given path.
category: processes
os_target: all
parameters:
  - name: process_name
    label: Process Name
    type: text
    required: true
    placeholder: e.g. notepad
  - name: exe_path
    label: Executable Path
    type: text
    required: true
    placeholder: e.g. C:\Windows\notepad.exe
script: |
  $procs = Get-Process -Name {{ process_name }} -ErrorAction SilentlyContinue
  if ($procs) {
    $procs | Stop-Process -Force
    Write-Output "Killed $($procs.Count) instance(s) of '{{ process_name }}'."
  } else {
    Write-Output "No running instances found, launching fresh."
  }
  Start-Sleep -Seconds 1
  Start-Process -FilePath {{ exe_path }}
  Write-Output "Launched: {{ exe_path }}"
```

Create `scripts/processes/list_processes.yml`:
```yaml
name: List Processes
description: Lists running processes, optionally filtered by name. Leave filter blank to list all.
category: processes
os_target: all
parameters:
  - name: name_filter
    label: Name Filter (optional)
    type: text
    required: false
    default: "*"
    placeholder: e.g. sql (leave blank for all)
script: |
  Get-Process -Name {{ name_filter }} -ErrorAction SilentlyContinue |
    Sort-Object CPU -Descending |
    Select-Object -First 50 Name, Id,
      @{N='CPU(s)';E={[math]::Round($_.CPU,1)}},
      @{N='Mem(MB)';E={[math]::Round($_.WorkingSet/1MB,1)}} |
    Format-Table -AutoSize |
    Out-String
```

- [ ] **Step 3: Create network scripts**

```bash
mkdir -p scripts/network
```

Create `scripts/network/ping_host.yml`:
```yaml
name: Ping Host
description: Pings a hostname or IP address and reports round-trip time.
category: network
os_target: all
parameters:
  - name: target
    label: Hostname or IP
    type: text
    required: true
    placeholder: e.g. 8.8.8.8 or google.com
  - name: count
    label: Ping Count
    type: number
    required: false
    default: 4
script: |
  Test-Connection -ComputerName {{ target }} -Count {{ count }} |
    Select-Object Address, ResponseTime, StatusCode |
    Format-Table -AutoSize |
    Out-String
```

Create `scripts/network/check_port.yml`:
```yaml
name: Check Port Open
description: Tests whether a TCP port is reachable on a given host.
category: network
os_target: all
parameters:
  - name: target
    label: Hostname or IP
    type: text
    required: true
    placeholder: e.g. 192.168.1.1
  - name: port
    label: Port
    type: number
    required: true
    placeholder: e.g. 443
script: |
  $result = Test-NetConnection -ComputerName {{ target }} -Port {{ port }}
  Write-Output "Host: $($result.ComputerName)"
  Write-Output "Port: {{ port }}"
  Write-Output "TCP Test Succeeded: $($result.TcpTestSucceeded)"
```

Create `scripts/network/flush_dns.yml`:
```yaml
name: Flush DNS Cache
description: Clears the local DNS resolver cache.
category: network
os_target: all
parameters: []
script: |
  Clear-DnsClientCache
  Write-Output "DNS cache flushed successfully."
```

Create `scripts/network/get_adapter_info.yml`:
```yaml
name: Get Network Adapter Info
description: Lists all active network adapters with their IP addresses and link speed.
category: network
os_target: all
parameters: []
script: |
  Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | ForEach-Object {
    $ip = (Get-NetIPAddress -InterfaceIndex $_.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress
    [PSCustomObject]@{
      Name      = $_.Name
      Status    = $_.Status
      LinkSpeed = $_.LinkSpeed
      IPAddress = $ip
    }
  } | Format-Table -AutoSize | Out-String
```

- [ ] **Step 4: Commit**

```bash
git add scripts/iis/ scripts/processes/ scripts/network/
git commit -m "feat: preloaded IIS, process, and network YAML scripts"
```

---

## Task 11: Docker Build and Smoke Test

**Files:**
- Verify: all files in place
- Verify: `docker compose up --build` succeeds
- Verify: UI renders correctly at `http://localhost:5000`

- [ ] **Step 1: Run the full test suite one final time**

```bash
pytest -v
```

Expected: All tests PASS, no failures.

- [ ] **Step 2: Verify .env exists (copy from example if not)**

```bash
ls .env 2>/dev/null || cp .env.example .env
echo "Edit .env with real VM details before a live test"
```

- [ ] **Step 3: Build the Docker image**

```bash
docker compose build
```

Expected: Build completes without error. Python packages install cleanly.

- [ ] **Step 4: Start the container**

```bash
docker compose up -d
```

Expected: Container starts. Check logs with `docker compose logs -f`.

- [ ] **Step 5: Verify the app is serving**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/
```

Expected: `200`

- [ ] **Step 6: Verify script library loads**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/scripts
```

Expected: `200`

- [ ] **Step 7: Verify history page loads**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/history
```

Expected: `200`

- [ ] **Step 8: Stop the container**

```bash
docker compose down
```

- [ ] **Step 9: Final commit**

```bash
git add .
git commit -m "feat: complete winrm-admin implementation"
```

---

## Self-Review: Spec Coverage Check

| Spec Requirement | Covered In |
|---|---|
| Docker container, Flask + pywinrm | Task 1, 7 |
| .env VM config with name/IP/OS tag | Task 2 |
| Multiple VM dropdown | Task 7 (routes), Task 8 (base.html) |
| WinRM connection test on VM select | Task 6, 7 (`/api/vm/<name>/status`) |
| YAML script library | Task 4, 9, 10 |
| OS tag filtering (server2019/win11/all) | Task 4 |
| Dynamic parameter forms | Task 8 (run_form.html) |
| Input validation (required, typed) | Task 3 |
| PS injection protection | Task 3 (sanitizer single-quote escaping) |
| Services scripts (restart/stop/start/list) | Task 9 |
| IIS app pool scripts | Task 10 |
| Process kill/relaunch/list scripts | Task 10 |
| Network scripts (ping/port/DNS/adapter) | Task 10 |
| System scripts (eventlog/users/disk) | Task 9 |
| Win11-specific scripts (Explorer/WU/winget) | Task 9 |
| Run history with stdout+stderr | Task 5, 7 |
| History filter by VM and category | Task 5, 7, 8 |
| Startup validation on missing .env fields | Task 2 |
| Docker volume for history.db | Task 1 (docker-compose.yml) |
| Error output surfaced in UI | Task 8 (run_form.html) |
