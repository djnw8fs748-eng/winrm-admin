# New Script Categories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 14 new PowerShell scripts across 4 new categories (`windows_update`, `firewall`, `scheduled_tasks`, `registry`) and register the categories in the history filter dropdown.

**Architecture:** Each category is a new subdirectory under `scripts/`. Scripts follow the existing YAML schema (`name`, `description`, `category`, `os_target`, `parameters`, `script`). The only code change is a one-line update to the `categories` list in `app.py`. The CI script count assertion is dynamic and self-updating.

**Tech Stack:** YAML, PowerShell (rendered via Jinja2), Flask, Python 3.11

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `scripts/windows_update/check_update_status.yml` | Create | Query pending updates via COM object |
| `scripts/windows_update/list_installed_updates.yml` | Create | List installed hotfixes via `Get-HotFix` |
| `scripts/windows_update/trigger_update_check.yml` | Create | Trigger update scan via `wuauclt` + `UsoClient` |
| `scripts/firewall/get_firewall_profiles.yml` | Create | Show Domain/Private/Public profile status |
| `scripts/firewall/list_firewall_rules.yml` | Create | List enabled rules with optional name filter |
| `scripts/firewall/enable_firewall_rule.yml` | Create | Enable a named firewall rule |
| `scripts/firewall/disable_firewall_rule.yml` | Create | Disable a named firewall rule |
| `scripts/scheduled_tasks/list_scheduled_tasks.yml` | Create | List tasks with state, filtered by folder |
| `scripts/scheduled_tasks/run_scheduled_task.yml` | Create | Trigger a task immediately |
| `scripts/scheduled_tasks/enable_scheduled_task.yml` | Create | Enable a named task |
| `scripts/scheduled_tasks/disable_scheduled_task.yml` | Create | Disable a named task |
| `scripts/registry/get_registry_value.yml` | Create | Read a registry value |
| `scripts/registry/set_registry_value.yml` | Create | Write a registry value |
| `scripts/registry/check_registry_key.yml` | Create | Test if a registry key exists |
| `app.py` | Modify | Add 4 new categories to history filter |

---

## Task 1: `windows_update` scripts

**Files:**
- Create: `scripts/windows_update/check_update_status.yml`
- Create: `scripts/windows_update/list_installed_updates.yml`
- Create: `scripts/windows_update/trigger_update_check.yml`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p scripts/windows_update
```

- [ ] **Step 2: Create `check_update_status.yml`**

```yaml
name: Check Windows Update Status
description: Lists pending (not yet installed) Windows updates.
category: windows_update
os_target: all
parameters: []
script: |
  try {
    $searcher = (New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher()
    $result = $searcher.Search("IsInstalled=0 and IsHidden=0")
    Write-Output "Pending updates: $($result.Updates.Count)"
    $result.Updates | ForEach-Object { Write-Output "  - $($_.Title)" }
  } catch {
    Write-Output "Could not query Windows Update: $_"
  }
```

- [ ] **Step 3: Create `list_installed_updates.yml`**

```yaml
name: List Installed Updates
description: Lists recently installed Windows updates (hotfixes). Sorted newest first.
category: windows_update
os_target: all
parameters:
  - name: count
    label: Number of Updates
    type: number
    required: false
    default: 20
script: |
  Get-HotFix |
    Sort-Object InstalledOn -Descending -ErrorAction SilentlyContinue |
    Select-Object -First {{ count }} HotFixID, InstalledOn, Description, InstalledBy |
    Format-Table -AutoSize |
    Out-String
```

- [ ] **Step 4: Create `trigger_update_check.yml`**

```yaml
name: Trigger Update Check
description: Forces Windows to check for new updates immediately.
category: windows_update
os_target: all
parameters: []
script: |
  Write-Output "Triggering Windows Update scan..."
  wuauclt /detectnow
  UsoClient StartScan 2>$null
  Write-Output "Scan triggered. Allow a few minutes then recheck update status."
```

- [ ] **Step 5: Verify all 3 scripts load cleanly**

```bash
python -c "
from script_loader import load_all_scripts
scripts = load_all_scripts()
wu = scripts.get('windows_update', [])
names = [s['name'] for s in wu]
assert len(wu) == 3, f'Expected 3 windows_update scripts, got {len(wu)}: {names}'
assert 'Check Windows Update Status' in names
assert 'List Installed Updates' in names
assert 'Trigger Update Check' in names
print('OK:', names)
"
```

Expected: `OK: ['Check Windows Update Status', 'List Installed Updates', 'Trigger Update Check']`

- [ ] **Step 6: Commit**

```bash
git add scripts/windows_update/
git commit -m "feat: add windows_update scripts (check status, list installed, trigger scan)"
```

---

## Task 2: `firewall` scripts

**Files:**
- Create: `scripts/firewall/get_firewall_profiles.yml`
- Create: `scripts/firewall/list_firewall_rules.yml`
- Create: `scripts/firewall/enable_firewall_rule.yml`
- Create: `scripts/firewall/disable_firewall_rule.yml`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p scripts/firewall
```

- [ ] **Step 2: Create `get_firewall_profiles.yml`**

```yaml
name: Get Firewall Profiles
description: Shows enabled/disabled status and default actions for Domain, Private, and Public firewall profiles.
category: firewall
os_target: all
parameters: []
script: |
  Get-NetFirewallProfile |
    Select-Object Name, Enabled, DefaultInboundAction, DefaultOutboundAction |
    Format-Table -AutoSize |
    Out-String
```

- [ ] **Step 3: Create `list_firewall_rules.yml`**

```yaml
name: List Firewall Rules
description: Lists enabled firewall rules, optionally filtered by display name. Use * to list all.
category: firewall
os_target: all
parameters:
  - name: name_filter
    label: Name Filter
    type: text
    required: false
    default: "*"
    placeholder: e.g. Remote (leave blank for all)
script: |
  Get-NetFirewallRule -Enabled True |
    Where-Object { $_.DisplayName -like {{ name_filter }} } |
    Select-Object DisplayName, Direction, Action, Profile |
    Sort-Object Direction, DisplayName |
    Format-Table -AutoSize |
    Out-String
```

- [ ] **Step 4: Create `enable_firewall_rule.yml`**

```yaml
name: Enable Firewall Rule
description: Enables a firewall rule by its display name.
category: firewall
os_target: all
parameters:
  - name: rule_name
    label: Rule Display Name
    type: text
    required: true
    placeholder: e.g. Remote Desktop - User Mode (TCP-In)
script: |
  Enable-NetFirewallRule -DisplayName {{ rule_name }} -ErrorAction Stop
  $rule = Get-NetFirewallRule -DisplayName {{ rule_name }} -ErrorAction SilentlyContinue
  Write-Output "Rule: $($rule.DisplayName)"
  Write-Output "Enabled: $($rule.Enabled)"
```

- [ ] **Step 5: Create `disable_firewall_rule.yml`**

```yaml
name: Disable Firewall Rule
description: Disables a firewall rule by its display name.
category: firewall
os_target: all
parameters:
  - name: rule_name
    label: Rule Display Name
    type: text
    required: true
    placeholder: e.g. Remote Desktop - User Mode (TCP-In)
script: |
  Disable-NetFirewallRule -DisplayName {{ rule_name }} -ErrorAction Stop
  $rule = Get-NetFirewallRule -DisplayName {{ rule_name }} -ErrorAction SilentlyContinue
  Write-Output "Rule: $($rule.DisplayName)"
  Write-Output "Enabled: $($rule.Enabled)"
```

- [ ] **Step 6: Verify all 4 scripts load cleanly**

```bash
python -c "
from script_loader import load_all_scripts
scripts = load_all_scripts()
fw = scripts.get('firewall', [])
names = [s['name'] for s in fw]
assert len(fw) == 4, f'Expected 4 firewall scripts, got {len(fw)}: {names}'
assert 'Get Firewall Profiles' in names
assert 'List Firewall Rules' in names
assert 'Enable Firewall Rule' in names
assert 'Disable Firewall Rule' in names
print('OK:', names)
"
```

Expected: `OK: ['Disable Firewall Rule', 'Enable Firewall Rule', 'Get Firewall Profiles', 'List Firewall Rules']`

- [ ] **Step 7: Commit**

```bash
git add scripts/firewall/
git commit -m "feat: add firewall scripts (profiles, list rules, enable/disable rule)"
```

---

## Task 3: `scheduled_tasks` scripts

**Files:**
- Create: `scripts/scheduled_tasks/list_scheduled_tasks.yml`
- Create: `scripts/scheduled_tasks/run_scheduled_task.yml`
- Create: `scripts/scheduled_tasks/enable_scheduled_task.yml`
- Create: `scripts/scheduled_tasks/disable_scheduled_task.yml`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p scripts/scheduled_tasks
```

- [ ] **Step 2: Create `list_scheduled_tasks.yml`**

```yaml
name: List Scheduled Tasks
description: Lists scheduled tasks and their current state. Use \ for the root folder or \* for all folders.
category: scheduled_tasks
os_target: all
parameters:
  - name: folder
    label: Task Folder
    type: text
    required: false
    default: "\\*"
    placeholder: "e.g. \\ for root, \\Microsoft for a subtree"
script: |
  Get-ScheduledTask |
    Where-Object { $_.TaskPath -like {{ folder }} } |
    Select-Object TaskName, TaskPath, State |
    Sort-Object TaskPath, TaskName |
    Format-Table -AutoSize |
    Out-String
```

- [ ] **Step 3: Create `run_scheduled_task.yml`**

```yaml
name: Run Scheduled Task
description: Triggers a scheduled task to run immediately, regardless of its schedule.
category: scheduled_tasks
os_target: all
parameters:
  - name: task_name
    label: Task Name
    type: text
    required: true
    placeholder: e.g. Defrag
  - name: folder
    label: Task Folder
    type: text
    required: false
    default: "\\"
    placeholder: "e.g. \\ for root"
script: |
  Start-ScheduledTask -TaskName {{ task_name }} -TaskPath {{ folder }} -ErrorAction Stop
  Start-Sleep -Seconds 2
  $task = Get-ScheduledTask -TaskName {{ task_name }} -TaskPath {{ folder }} -ErrorAction SilentlyContinue
  if ($task) {
    Write-Output "Task: $($task.TaskName)"
    Write-Output "State: $($task.State)"
  }
```

- [ ] **Step 4: Create `enable_scheduled_task.yml`**

```yaml
name: Enable Scheduled Task
description: Enables a scheduled task so it can run on its configured schedule.
category: scheduled_tasks
os_target: all
parameters:
  - name: task_name
    label: Task Name
    type: text
    required: true
    placeholder: e.g. Defrag
  - name: folder
    label: Task Folder
    type: text
    required: false
    default: "\\"
    placeholder: "e.g. \\ for root"
script: |
  Enable-ScheduledTask -TaskName {{ task_name }} -TaskPath {{ folder }} -ErrorAction Stop
  $task = Get-ScheduledTask -TaskName {{ task_name }} -TaskPath {{ folder }} -ErrorAction SilentlyContinue
  if ($task) {
    Write-Output "Task: $($task.TaskName)"
    Write-Output "State: $($task.State)"
  }
```

- [ ] **Step 5: Create `disable_scheduled_task.yml`**

```yaml
name: Disable Scheduled Task
description: Disables a scheduled task so it will not run on its configured schedule.
category: scheduled_tasks
os_target: all
parameters:
  - name: task_name
    label: Task Name
    type: text
    required: true
    placeholder: e.g. Defrag
  - name: folder
    label: Task Folder
    type: text
    required: false
    default: "\\"
    placeholder: "e.g. \\ for root"
script: |
  Disable-ScheduledTask -TaskName {{ task_name }} -TaskPath {{ folder }} -ErrorAction Stop
  $task = Get-ScheduledTask -TaskName {{ task_name }} -TaskPath {{ folder }} -ErrorAction SilentlyContinue
  if ($task) {
    Write-Output "Task: $($task.TaskName)"
    Write-Output "State: $($task.State)"
  }
```

- [ ] **Step 6: Verify all 4 scripts load cleanly**

```bash
python -c "
from script_loader import load_all_scripts
scripts = load_all_scripts()
st = scripts.get('scheduled_tasks', [])
names = [s['name'] for s in st]
assert len(st) == 4, f'Expected 4 scheduled_tasks scripts, got {len(st)}: {names}'
assert 'List Scheduled Tasks' in names
assert 'Run Scheduled Task' in names
assert 'Enable Scheduled Task' in names
assert 'Disable Scheduled Task' in names
print('OK:', names)
"
```

Expected: `OK: ['Disable Scheduled Task', 'Enable Scheduled Task', 'List Scheduled Tasks', 'Run Scheduled Task']`

- [ ] **Step 7: Commit**

```bash
git add scripts/scheduled_tasks/
git commit -m "feat: add scheduled_tasks scripts (list, run, enable, disable)"
```

---

## Task 4: `registry` scripts

**Files:**
- Create: `scripts/registry/check_registry_key.yml`
- Create: `scripts/registry/get_registry_value.yml`
- Create: `scripts/registry/set_registry_value.yml`

**Note on parameter rendering:** The sanitizer wraps all `text` params in single quotes. So `{{ hive }}` renders as `'HKLM'` and `{{ key_path }}` as `'SOFTWARE\Microsoft\Windows NT\CurrentVersion'`. The path is built by string concatenation: `'HKLM' + ":\" + 'SOFTWARE\...'` → `HKLM:\SOFTWARE\...`. PowerShell property access with a single-quoted name (`$props.'ProductName'`) is valid syntax.

- [ ] **Step 1: Create the directory**

```bash
mkdir -p scripts/registry
```

- [ ] **Step 2: Create `check_registry_key.yml`**

```yaml
name: Check Registry Key
description: Tests whether a registry key path exists.
category: registry
os_target: all
parameters:
  - name: hive
    label: Hive
    type: text
    required: true
    placeholder: "HKLM or HKCU"
  - name: key_path
    label: Key Path
    type: text
    required: true
    placeholder: "e.g. SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"
script: |
  $path = {{ hive }} + ":\" + {{ key_path }}
  if (Test-Path $path) {
    Write-Output "EXISTS: $path"
  } else {
    Write-Output "NOT FOUND: $path"
  }
```

- [ ] **Step 3: Create `get_registry_value.yml`**

```yaml
name: Get Registry Value
description: Reads a single value from a registry key.
category: registry
os_target: all
parameters:
  - name: hive
    label: Hive
    type: text
    required: true
    placeholder: "HKLM or HKCU"
  - name: key_path
    label: Key Path
    type: text
    required: true
    placeholder: "e.g. SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion"
  - name: value_name
    label: Value Name
    type: text
    required: true
    placeholder: "e.g. ProductName"
script: |
  $path = {{ hive }} + ":\" + {{ key_path }}
  $props = Get-ItemProperty -Path $path -Name {{ value_name }} -ErrorAction Stop
  Write-Output "{{ value_name }}: $($props.{{ value_name }})"
```

- [ ] **Step 4: Create `set_registry_value.yml`**

```yaml
name: Set Registry Value
description: Writes a value to a registry key. The key must already exist.
category: registry
os_target: all
parameters:
  - name: hive
    label: Hive
    type: text
    required: true
    placeholder: "HKLM or HKCU"
  - name: key_path
    label: Key Path
    type: text
    required: true
    placeholder: "e.g. SOFTWARE\\MyApp\\Settings"
  - name: value_name
    label: Value Name
    type: text
    required: true
    placeholder: "e.g. EnableFeature"
  - name: value_data
    label: Value Data
    type: text
    required: true
    placeholder: "e.g. 1"
  - name: value_type
    label: Value Type
    type: text
    required: false
    default: "String"
    placeholder: "String, DWORD, QWord, Binary"
script: |
  $path = {{ hive }} + ":\" + {{ key_path }}
  Set-ItemProperty -Path $path -Name {{ value_name }} -Value {{ value_data }} -Type {{ value_type }} -ErrorAction Stop
  $check = Get-ItemProperty -Path $path -Name {{ value_name }} -ErrorAction SilentlyContinue
  Write-Output "Set {{ value_name }} = $($check.{{ value_name }})"
```

- [ ] **Step 5: Verify all 3 scripts load cleanly**

```bash
python -c "
from script_loader import load_all_scripts
scripts = load_all_scripts()
reg = scripts.get('registry', [])
names = [s['name'] for s in reg]
assert len(reg) == 3, f'Expected 3 registry scripts, got {len(reg)}: {names}'
assert 'Check Registry Key' in names
assert 'Get Registry Value' in names
assert 'Set Registry Value' in names
print('OK:', names)
"
```

Expected: `OK: ['Check Registry Key', 'Get Registry Value', 'Set Registry Value']`

- [ ] **Step 6: Commit**

```bash
git add scripts/registry/
git commit -m "feat: add registry scripts (check key, get value, set value)"
```

---

## Task 5: Update `app.py` history filter

**Files:**
- Modify: `app.py:76` (the `categories` list in the `history()` route)

- [ ] **Step 1: Update the categories list in `app.py`**

Find this line (around line 76):

```python
categories = ["services", "iis", "processes", "network", "system"]
```

Replace with:

```python
categories = ["services", "iis", "processes", "network", "system",
              "windows_update", "firewall", "scheduled_tasks", "registry"]
```

- [ ] **Step 2: Run the full unit test suite**

```bash
.venv/bin/pytest tests/ --ignore=tests/integration/ -q
```

Expected: `39 passed` (no new tests; existing tests cover the history route generically)

- [ ] **Step 3: Verify total script count**

```bash
python -c "
from script_loader import load_all_scripts
total = sum(len(v) for v in load_all_scripts().values())
assert total == 34, f'Expected 34 scripts, got {total}'
print(f'OK: {total} scripts loaded')
"
```

Expected: `OK: 34 scripts loaded`

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: register windows_update, firewall, scheduled_tasks, registry in history filter"
```

---

## Self-Review: Spec Coverage

| Spec Requirement | Covered In |
|---|---|
| `windows_update/check_update_status.yml` | Task 1 Step 2 |
| `windows_update/list_installed_updates.yml` | Task 1 Step 3 |
| `windows_update/trigger_update_check.yml` | Task 1 Step 4 |
| `firewall/get_firewall_profiles.yml` | Task 2 Step 2 |
| `firewall/list_firewall_rules.yml` | Task 2 Step 3 |
| `firewall/enable_firewall_rule.yml` | Task 2 Step 4 |
| `firewall/disable_firewall_rule.yml` | Task 2 Step 5 |
| `scheduled_tasks/list_scheduled_tasks.yml` | Task 3 Step 2 |
| `scheduled_tasks/run_scheduled_task.yml` | Task 3 Step 3 |
| `scheduled_tasks/enable_scheduled_task.yml` | Task 3 Step 4 |
| `scheduled_tasks/disable_scheduled_task.yml` | Task 3 Step 5 |
| `registry/check_registry_key.yml` | Task 4 Step 2 |
| `registry/get_registry_value.yml` | Task 4 Step 3 |
| `registry/set_registry_value.yml` | Task 4 Step 4 |
| All `os_target: all` | All tasks |
| Update `app.py` categories list | Task 5 Step 1 |
| CI script count self-updating (no change needed) | Confirmed — uses `find scripts/ -name "*.yml" \| wc -l` |
