from __future__ import annotations

import logging
import subprocess

from .config import AppConfig


def notify_failure(config: AppConfig, title: str, message: str, logger: logging.Logger) -> None:
    if config.notify != "desktop":
        return
    escaped_title = _ps_escape(title)
    escaped_message = _ps_escape(message[:240])
    command = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$n = New-Object System.Windows.Forms.NotifyIcon; "
        "$n.Icon = [System.Drawing.SystemIcons]::Warning; "
        "$n.BalloonTipTitle = "
        f"'{escaped_title}'; "
        "$n.BalloonTipText = "
        f"'{escaped_message}'; "
        "$n.Visible = $true; "
        "$n.ShowBalloonTip(10000); "
        "Start-Sleep -Seconds 8; "
        "$n.Dispose();"
    )
    try:
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            check=False,
            timeout=15,
            capture_output=True,
            text=True,
        )
    except Exception:
        logger.debug("desktop notification failed", exc_info=True)


def _ps_escape(value: str) -> str:
    return value.replace("'", "''").replace("\r", " ").replace("\n", " ")

