"""
Network utilities for zget.
"""

import ipaddress
import shutil
import subprocess


def get_tailscale_ip() -> str | None:
    """
    Get the local Tailscale IPv4 address.

    Returns:
        str: The IPv4 address (e.g., '100.104.29.122') or None if not available/running.
    """
    # 1. Try finding the executable
    ts_path = shutil.which("tailscale")
    if not ts_path:
        # Common macOS path if not in PATH
        if shutil.which("/opt/homebrew/bin/tailscale"):
            ts_path = "/opt/homebrew/bin/tailscale"
        elif shutil.which("/Applications/Tailscale.app/Contents/MacOS/Tailscale"):
            # Rare but possible direct app usage
            ts_path = "/Applications/Tailscale.app/Contents/MacOS/Tailscale"

    if not ts_path:
        return None

    # 2. Run 'tailscale ip -4'
    try:
        result = subprocess.run([ts_path, "ip", "-4"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            ip = result.stdout.strip()
            # Basic validation
            try:
                ipaddress.IPv4Address(ip)
                return ip
            except ValueError:
                return None
    except Exception:
        pass

    return None
