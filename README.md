# winrm-admin

A self-hosted Docker web app for running PowerShell scripts on remote Windows virtual machines via WinRM. Built for sysadmins who want a browser-based interface to restart services, manage IIS app pools, kill and relaunch processes, and run network diagnostics — without RDPing into every machine.

## Features

- **Multi-VM support** — define multiple Windows targets in `.env`, select them from a dropdown
- **OS-aware script library** — scripts are tagged for Windows Server 2019, Windows 11, or both; the UI filters automatically based on the selected VM
- **Dynamic variable forms** — preloaded scripts expose their parameters as typed input fields, no PowerShell knowledge required
- **Run history** — every execution is logged with timestamp, VM, parameters, and full stdout/stderr output
- **WinRM native** — uses Windows Remote Management, no agents or third-party software needed on the target VMs

## Preloaded Scripts

| Category | Scripts |
|---|---|
| Services | Restart, Stop, Start, List |
| IIS App Pools (Server 2019) | Recycle, Stop, Start, List |
| Processes | Kill by name, Kill and relaunch, List |
| Network | Ping, Port check, Flush DNS, Adapter info |
| System | Event log errors, Logged-on users, Disk space, Restart Explorer (Win11), Clear WU cache (Win11) |
| Windows Update | Check pending updates, List installed hotfixes, Trigger update scan |
| Firewall | Get profile status, List rules, Enable rule, Disable rule |
| Scheduled Tasks | List tasks, Run task, Enable task, Disable task |
| Registry | Check key exists, Get value, Set value |

## Requirements

- Docker and Docker Compose
- Windows VMs with WinRM enabled (`Enable-PSRemoting -Force` on the target)
- Network access from the Docker host to the VMs on port 5985 (or 5986 for HTTPS)

## Quick Start

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/winrm-admin.git
cd winrm-admin
```

**2. Configure your VMs**
```bash
cp .env.example .env
```

Edit `.env`:
```env
VM_HOSTS=dc01:192.168.1.10:server2019,workstation1:192.168.1.20:win11
WINRM_USERNAME=Administrator
WINRM_PASSWORD=yourpassword
WINRM_PORT=5985
WINRM_TRANSPORT=ntlm
```

**3. Start the app**
```bash
docker compose up --build
```

Open `http://localhost:5000` in your browser.

## Deployment

### First-time setup

```bash
git clone https://github.com/djnw8fs748-eng/winrm-admin.git
cd winrm-admin
cp .env.example .env
```

Edit `.env` with your VM details (see Quick Start above), then build and start:

```bash
docker compose up --build -d
```

The `-d` flag runs the container in the background. The app starts at `http://localhost:5000`.

### Run history persistence

Run history is stored in `data/history.db` on the Docker host (mounted as a volume). This file survives container restarts and rebuilds — do not delete it unless you want to clear the history.

### Updating to a new version

```bash
git pull
docker compose up --build -d
```

The build step picks up any code or script changes. The `data/` volume is untouched.

### Stopping and starting

```bash
docker compose stop        # stop the container, keep the image
docker compose start       # start it again
docker compose down        # stop and remove the container (data volume preserved)
```

### Viewing logs

```bash
docker compose logs -f
```

### Changing VM configuration

Edit `.env`, then restart the container:

```bash
docker compose restart
```

No rebuild is needed for `.env` changes — environment variables are loaded at startup.

### Running on a non-default port

To expose the app on a different host port (e.g. 8080), edit `docker-compose.yml`:

```yaml
ports:
  - "8080:5000"
```

Then run `docker compose up -d` (no rebuild needed for port changes).

---

## Enabling WinRM on Target VMs

Run the following on each Windows VM (as Administrator):

```powershell
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
Restart-Service WinRM
```

For NTLM auth over HTTP (port 5985), also run:

```powershell
Set-Item WSMan:\localhost\Service\Auth\Basic -Value $true
Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value $true
```

> **Note:** For production use, prefer HTTPS (port 5986) with a certificate and NTLM or Kerberos auth without `AllowUnencrypted`.

## Adding Custom Scripts

Create a `.yml` file in `app/scripts/<category>/`:

```yaml
name: My Custom Script
description: Does something useful
category: services
os_target: all          # server2019 | win11 | all
parameters:
  - name: target_name
    label: Target Name
    type: text
    required: true
    placeholder: e.g. MyApp
script: |
  Write-Output "Running against {{ target_name }}"
```

Restart the container and your script appears in the library automatically.

## Security Notes

- `.env` contains credentials — never commit it to version control
- The app assumes a trusted network; there is no built-in user authentication for the web UI
- All user parameter values are sanitised before PowerShell substitution
- For internet-facing deployments, place behind a reverse proxy with authentication (e.g. Nginx + basic auth, or Authelia)

## License

MIT
