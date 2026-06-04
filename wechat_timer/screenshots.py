from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def capture_failure_screenshot(
    output_dir: Path,
    logger: logging.Logger,
    display_root: Path | None = None,
) -> str | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"failure-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
    try:
        from PIL import ImageGrab

        image = ImageGrab.grab()
        image.save(path)
        display_path = _relative_display_path(path, display_root)
        logger.info("saved failure screenshot=%s", display_path)
        return display_path
    except Exception:
        logger.debug("screenshot capture failed", exc_info=True)
        return None


def _relative_display_path(path: Path, display_root: Path | None) -> str:
    if display_root is not None:
        try:
            return str(path.resolve().relative_to(display_root.resolve()))
        except ValueError:
            pass
    return path.name
