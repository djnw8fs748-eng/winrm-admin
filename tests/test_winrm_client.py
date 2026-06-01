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
