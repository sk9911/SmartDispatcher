"""Offline guard: block outbound network so tests and the report run without it."""

import ipaddress
import os
import socket

ENV_VAR = "REGRET_BLOCK_NETWORK"


class NetworkBlockedError(OSError):
    """Raised when code tries to reach a non-local host while the guard is on."""


_originals: dict = {}
_LOCAL_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost", ""}


def _is_local_ip(host: str) -> bool:
    host = host.split("%", 1)[0]
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _is_local_host(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    return host.lower() in _LOCAL_NAMES or _is_local_ip(host)


def _check_address(sock, address) -> None:
    if sock.family not in (socket.AF_INET, socket.AF_INET6):
        return  # AF_UNIX etc.
    host = address[0] if isinstance(address, tuple) else address
    if not _is_local_host(host):
        raise NetworkBlockedError(f"network blocked: connect to {host!r}")


def is_installed() -> bool:
    return bool(_originals)


def install() -> None:
    if _originals:
        return
    connect = socket.socket.connect
    connect_ex = socket.socket.connect_ex
    getaddrinfo = socket.getaddrinfo
    create_connection = socket.create_connection
    _originals.update(
        connect=connect, connect_ex=connect_ex,
        getaddrinfo=getaddrinfo, create_connection=create_connection,
    )

    def guarded_connect(self, address):
        _check_address(self, address)
        return connect(self, address)

    def guarded_connect_ex(self, address):
        _check_address(self, address)
        return connect_ex(self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_local_host(host):
            raise NetworkBlockedError(f"network blocked: DNS lookup of {host!r}")
        return getaddrinfo(host, *args, **kwargs)

    def guarded_create_connection(address, *args, **kwargs):
        if not _is_local_host(address[0]):
            raise NetworkBlockedError(f"network blocked: connect to {address[0]!r}")
        return create_connection(address, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.getaddrinfo = guarded_getaddrinfo
    socket.create_connection = guarded_create_connection


def uninstall() -> None:
    if not _originals:
        return
    socket.socket.connect = _originals["connect"]
    socket.socket.connect_ex = _originals["connect_ex"]
    socket.getaddrinfo = _originals["getaddrinfo"]
    socket.create_connection = _originals["create_connection"]
    _originals.clear()


def install_if_requested() -> None:
    if os.environ.get(ENV_VAR) == "1":
        install()
