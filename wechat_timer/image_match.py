from __future__ import annotations

import logging
from pathlib import Path


def find_template_on_screen(
    template_path: Path,
    region: tuple[int, int, int, int],
    threshold: float,
    logger: logging.Logger,
    label: str = "image template",
) -> tuple[int, int, float] | None:
    try:
        import cv2
        import numpy as np
        from PIL import ImageGrab
    except ImportError as exc:
        logger.debug("image matching dependency is missing: %s", exc)
        return None

    if not template_path.exists():
        logger.warning("%s does not exist: %s", label, template_path)
        return None

    try:
        screenshot = ImageGrab.grab()
    except Exception:
        logger.debug("screen capture for image matching failed", exc_info=True)
        return None

    screen = cv2.cvtColor(np.asarray(screenshot), cv2.COLOR_RGB2BGR)
    template = cv2.imread(str(template_path), cv2.IMREAD_COLOR)
    if template is None:
        logger.warning("could not read %s: %s", label, template_path)
        return None

    left, top, right, bottom = region
    left = max(0, left)
    top = max(0, top)
    right = min(screen.shape[1], right)
    bottom = min(screen.shape[0], bottom)
    if right <= left or bottom <= top:
        return None

    haystack = screen[top:bottom, left:right]
    best_score = -1.0
    best_center: tuple[int, int] | None = None
    for scale in (0.75, 0.85, 0.90, 1.0, 1.10, 1.20, 1.25):
        width = max(8, round(template.shape[1] * scale))
        height = max(8, round(template.shape[0] * scale))
        if width >= haystack.shape[1] or height >= haystack.shape[0]:
            continue
        resized = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
        result = cv2.matchTemplate(haystack, resized, cv2.TM_CCOEFF_NORMED)
        _min_value, max_value, _min_location, max_location = cv2.minMaxLoc(result)
        if max_value > best_score:
            best_score = float(max_value)
            best_center = (
                left + max_location[0] + width // 2,
                top + max_location[1] + height // 2,
            )

    logger.info(
        "%s match score=%.3f threshold=%.3f center=%s",
        label,
        best_score,
        threshold,
        best_center,
    )
    if best_center is None or best_score < threshold:
        return None
    return best_center[0], best_center[1], best_score
