# New Script Categories — Design Spec
**Date:** 2026-06-10
**Status:** Approved

---

## Overview

Add 14 new PowerShell scripts across 4 new categories: `windows_update`, `firewall`, `scheduled_tasks`, and `registry`. All scripts target `os_target: all`. One line in `app.py` registers the new categories in the history filter dropdown. No other code changes are required.

---

## New Script Inventory

### `scripts/windows_update/` (3 scripts)

| File | Name | Description |
|---|---|---|
| `check_update_status.yml` | Check Windows Update Status | Show pending updates via `Get-WindowsUpdate`; falls back to WMI if the module is absent |
| `list_installed_updates.yml` | List Installed Updates | List recently installed updates via `Get-HotFix`; `count` param, default 20 |
| `trigger_update_check.yml` | Trigger Update Check | Force a check via `wuauclt /detectnow` and `UsoClient StartScan` |

### `scripts/firewall/` (4 scripts)

| File | Name | Description |
|---|---|---|
| `get_firewall_profiles.yml` | Get Firewall Profiles | Show enabled/disabled status for Domain, Private, and Public profiles |
| `list_firewall_rules.yml` | List Firewall Rules | List enabled rules; optional `name_filter` param (default `*`) |
| `enable_firewall_rule.yml` | Enable Firewall Rule | Enable a named rule via `Enable-NetFirewallRule`; `rule_name` param |
| `disable_firewall_rule.yml` | Disable Firewall Rule | Disable a named rule via `Disable-NetFirewallRule`; `rule_name` param |

### `scripts/scheduled_tasks/` (4 scripts)

| File | Name | Description |
|---|---|---|
| `list_scheduled_tasks.yml` | List Scheduled Tasks | List tasks with status; optional `folder` param (default `\`) |
| `run_scheduled_task.yml` | Run Scheduled Task | Trigger a task immediately via `Start-ScheduledTask`; `task_name` and `folder` params |
| `enable_scheduled_task.yml` | Enable Scheduled Task | Enable a task via `Enable-ScheduledTask`; `task_name` and `folder` params |
| `disable_scheduled_task.yml` | Disable Scheduled Task | Disable a task via `Disable-ScheduledTask`; `task_name` and `folder` params |

### `scripts/registry/` (3 scripts)

| File | Name | Description |
|---|---|---|
| `get_registry_value.yml` | Get Registry Value | Read a value via `Get-ItemProperty`; params: `hive` (HKLM/HKCU), `key_path`, `value_name` |
| `set_registry_value.yml` | Set Registry Value | Write a value via `Set-ItemProperty`; params: `hive`, `key_path`, `value_name`, `value_data`, `value_type` (String/DWORD/QWord/Binary) |
| `check_registry_key.yml` | Check Registry Key | Test if a key exists via `Test-Path`; params: `hive`, `key_path` |

---

## Code Changes

### `app.py`

Extend the `categories` list in the `history()` route:

```python
# before
categories = ["services", "iis", "processes", "network", "system"]

# after
categories = ["services", "iis", "processes", "network", "system",
              "windows_update", "firewall", "scheduled_tasks", "registry"]
```

### `.github/workflows/ci.yml`

Update the script count assertion in the `docker-build` job from `20` to `34`:

```yaml
assert t == 34, f'Expected 34 scripts, got {t}'
```

---

## Testing

No new unit or integration tests required. `test_script_loader.py` tests `load_all_scripts` generically and picks up new categories automatically. The CI `docker-build` script count assertion validates all 34 scripts load cleanly inside the container.

---

## What Is Not Changing

- `script_loader.py` — already handles arbitrary categories dynamically
- `db.py` — stores `script_id` as a free-form string, no schema change
- All templates — render categories generically from the data passed by routes
- Sanitizer — existing text/number escaping covers all new parameter types
