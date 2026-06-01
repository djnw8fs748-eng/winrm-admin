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
    port_str = os.getenv("WINRM_PORT", "5985")
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: WINRM_PORT must be an integer, got: {port_str!r}", file=sys.stderr)
        sys.exit(1)
    transport = os.getenv("WINRM_TRANSPORT", "ntlm")
    if not transport:
        transport = "ntlm"

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
        vms.append(VM(name=parts[0].strip(), ip=parts[1].strip(), os_tag=parts[2].strip()))

    return Config(vms=vms, username=username, password=password, port=port, transport=transport)
