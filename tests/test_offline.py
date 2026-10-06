import os
import socket
import subprocess
import sys

import pytest

from regret import offline
from regret.offline import NetworkBlockedError


@pytest.fixture
def clean_sockets():
    """Start unguarded; afterwards restore whatever state conftest set up."""
    was_installed = offline.is_installed()
    offline.uninstall()
    yield
    offline.uninstall()
    if was_installed:
        offline.install()


def test_external_tcp_blocked(clean_sockets):
    offline.install()
    with pytest.raises(NetworkBlockedError):
        socket.create_connection(("8.8.8.8", 53), timeout=1)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(NetworkBlockedError):
        s.connect(("8.8.8.8", 53))
    with pytest.raises(NetworkBlockedError):
        s.connect_ex(("8.8.8.8", 53))
    s.close()
    s6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    with pytest.raises(NetworkBlockedError):
        s6.connect(("2001:4860:4860::8888", 53, 0, 0))
    s6.close()


def test_dns_blocked_for_remote_hosts_only(clean_sockets):
    offline.install()
    with pytest.raises(NetworkBlockedError):
        socket.getaddrinfo("storage.googleapis.com", 443)
    assert socket.getaddrinfo("localhost", 80)


def test_loopback_tcp_works(clean_sockets):
    offline.install()
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port), timeout=2) as c:
            conn, _ = srv.accept()
            c.sendall(b"hi")
            assert conn.recv(2) == b"hi"
            conn.close()


def test_af_unix_works(clean_sockets):
    offline.install()
    a, b = socket.socketpair()
    a.sendall(b"x")
    assert b.recv(1) == b"x"
    a.close()
    b.close()


def test_install_is_idempotent(clean_sockets):
    offline.install()
    patched = socket.socket.connect
    offline.install()
    assert socket.socket.connect is patched
    offline.uninstall()
    assert not offline.is_installed()
    with pytest.raises(OSError):  # real connect to a closed local port, not blocked
        socket.create_connection(("127.0.0.1", 1), timeout=1)


def test_install_if_requested(clean_sockets, monkeypatch):
    monkeypatch.delenv("REGRET_BLOCK_NETWORK", raising=False)
    offline.install_if_requested()
    assert not offline.is_installed()
    monkeypatch.setenv("REGRET_BLOCK_NETWORK", "0")
    offline.install_if_requested()
    assert not offline.is_installed()
    monkeypatch.setenv("REGRET_BLOCK_NETWORK", "1")
    offline.install_if_requested()
    assert offline.is_installed()


def test_conftest_sets_fixture_config_unless_set():
    code = "import os,sys;sys.path.insert(0,'tests');import conftest;conftest.pytest_configure(None);print(os.environ['REGRET_CONFIG'])"
    env = {k: v for k, v in os.environ.items() if k != "REGRET_CONFIG"}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "fixture"
    env["REGRET_CONFIG"] = "full"
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "full"


def test_conftest_installs_guard_when_requested():
    code = "import sys;sys.path.insert(0,'tests');import conftest;conftest.pytest_configure(None);from regret import offline;print(offline.is_installed())"
    env = dict(os.environ)
    env["REGRET_BLOCK_NETWORK"] = "1"
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "True"
    env["REGRET_BLOCK_NETWORK"] = "0"
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
