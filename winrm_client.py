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
