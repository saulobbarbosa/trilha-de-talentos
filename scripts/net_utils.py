from __future__ import annotations

import json
import socket
import subprocess
import sys

VIRTUAL_ADAPTER_MARKERS = (
    "warp",
    "wsl",
    "vethernet",
    "virtualbox",
    "vmware",
    "hyper-v",
    "default switch",
    "loopback",
    "docker",
    "tailscale",
    "zerotier",
)

PREFERRED_ADAPTER_MARKERS = ("wi-fi", "wifi", "wireless", "wlan", "ethernet", "lan")


def _windows_default_route_ips() -> list[tuple[int, str, str]]:
    if sys.platform != "win32":
        return []

    script = (
        "$rows = foreach ($route in Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue) {"
        "$ip = Get-NetIPAddress -InterfaceIndex $route.InterfaceIndex -AddressFamily IPv4 "
        "-ErrorAction SilentlyContinue | "
        "Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | "
        "Select-Object -First 1; "
        "if ($ip) { [PSCustomObject]@{ alias = $ip.InterfaceAlias; ip = $ip.IPAddress; "
        "metric = [int]$route.RouteMetric + [int]$route.InterfaceMetric } } }; "
        "$rows | Sort-Object metric | ConvertTo-Json -Compress"
    )

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=6,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if completed.returncode != 0 or not completed.stdout.strip():
        return []

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return []

    candidates: list[tuple[int, str, str]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        alias = str(item.get("alias") or "")
        ip = str(item.get("ip") or "")
        if not ip:
            continue
        try:
            metric = int(item.get("metric", 9999))
        except (TypeError, ValueError):
            metric = 9999
        candidates.append((metric, alias, ip))
    return candidates


def get_lan_ip() -> str:
    candidates = _windows_default_route_ips()
    if candidates:
        physical = [
            candidate
            for candidate in candidates
            if not any(marker in candidate[1].lower() for marker in VIRTUAL_ADAPTER_MARKERS)
        ]
        usable = physical or candidates
        preferred = [
            candidate
            for candidate in usable
            if any(marker in candidate[1].lower() for marker in PREFERRED_ADAPTER_MARKERS)
        ]
        return (preferred or usable)[0][2]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()
