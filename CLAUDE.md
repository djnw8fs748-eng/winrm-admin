# winrm-admin

Dockerised Flask web app for running PowerShell scripts on remote Windows VMs via WinRM.

## Stack

- **Backend:** Python 3.11, Flask, pywinrm
- **Templating:** Jinja2
- **Database:** SQLite (mounted Docker volume at `./data/history.db`)
- **Container:** Docker + Docker Compose
- **Script definitions:** YAML files in `app/scripts/`

## Project Structure

```
app/
  main.py           ← Flask routes
  winrm_client.py   ← WinRM connection and execution
  db.py             ← SQLite run history
  scripts/          ← YAML script definitions (services, iis, processes, network)
  templates/        ← Jinja2 HTML
  static/           ← CSS/JS
data/
  history.db        ← persisted run log (gitignored)
docs/
  superpowers/specs/  ← design docs
```

## VM Configuration

VMs are defined in `.env`:

```env
VM_HOSTS=name:ip:os_tag,...   # os_tag: server2019 | win11
WINRM_USERNAME=Administrator
WINRM_PASSWORD=yourpassword
WINRM_PORT=5985
WINRM_TRANSPORT=ntlm
```

Never commit `.env` — it contains credentials.

## Adding Scripts

Add a `.yml` file to the appropriate `app/scripts/<category>/` folder. See the existing scripts for the YAML schema (`name`, `description`, `category`, `os_target`, `parameters`, `script`). The UI picks them up automatically on restart.

## Running Locally

```bash
cp .env.example .env   # fill in your VM details
docker compose up --build
```

App runs at `http://localhost:5000`.

## Key Constraints

- All user-supplied parameter values must be sanitised before PowerShell substitution — never interpolate raw input
- WinRM connection errors must always surface to the UI, never silently fail
- Run history (stdout + stderr) is always captured regardless of success or failure
- The app refuses to start if required `.env` fields are missing
