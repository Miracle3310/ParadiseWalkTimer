from __future__ import annotations

from datetime import date
from pathlib import Path

from .automation import AutomationError, WeChatCheckinAutomation
from .config import AppConfig
from .desktop import is_workstation_locked
from .logging_setup import configure_logging
from .notify import notify_failure
from .screenshots import capture_failure_screenshot
from .state import RunState


EXIT_CODES = {
    "success": 0,
    "already_done": 0,
    "dry_run_ok": 0,
    "pending_locked": 2,
    "failed_action_required": 3,
}


def run(mode: str, config_path: Path, force: bool = False) -> int:
    project_root = config_path.resolve().parent
    config = AppConfig.load(config_path)
    logger = configure_logging(project_root / "logs")
    state = RunState.load(project_root / "state" / "state.json")
    today = date.today().isoformat()

    logger.info("start mode=%s force=%s target=%s", mode, force, config.miniapp_name)

    if mode in {"scheduled", "retry"} and state.last_success_date == today and not force:
        logger.info("skip because today's check-in is already recorded")
        state.record_result("already_done", "Already recorded success today.")
        state.save()
        return EXIT_CODES["already_done"]

    locked = is_workstation_locked()
    if locked and mode in {"scheduled", "retry"}:
        state.mark_pending_locked(today)
        state.save()
        logger.warning("workstation appears locked; marked pending for retry")
        return EXIT_CODES["pending_locked"]

    if mode == "retry" and state.pending_locked_date != today and not force:
        logger.info("skip retry because there is no pending locked run for today")
        state.record_result("already_done", "No pending retry for today.")
        state.save()
        return EXIT_CODES["already_done"]

    automation = WeChatCheckinAutomation(config=config, logger=logger)
    try:
        result = automation.run(dry_run=(mode == "dry-run"))
    except AutomationError as exc:
        message = str(exc)
        screenshot = None
        if config.save_failure_screenshot:
            screenshot = capture_failure_screenshot(
                project_root / "artifacts" / "screenshots",
                logger,
                display_root=project_root,
            )
        state.record_failure(message=message, screenshot=screenshot)
        state.save()
        logger.exception("check-in failed: %s", message)
        notify_failure(config=config, title="龙湖天街签到失败", message=message, logger=logger)
        return EXIT_CODES["failed_action_required"]
    except Exception as exc:  # Defensive boundary for scheduled unattended runs.
        message = f"Unexpected error: {exc}"
        screenshot = None
        if config.save_failure_screenshot:
            screenshot = capture_failure_screenshot(
                project_root / "artifacts" / "screenshots",
                logger,
                display_root=project_root,
            )
        state.record_failure(message=message, screenshot=screenshot)
        state.save()
        logger.exception("unexpected failure")
        notify_failure(config=config, title="龙湖天街签到失败", message=message, logger=logger)
        return EXIT_CODES["failed_action_required"]

    if result.status in {"success", "already_done"}:
        state.record_success(today=today, status=result.status, message=result.message)
    elif result.status == "dry_run_ok":
        state.record_result(result.status, result.message)
    else:
        state.record_failure(message=result.message)
        notify_failure(config=config, title="龙湖天街签到需要处理", message=result.message, logger=logger)
    state.save()

    logger.info("finish status=%s message=%s", result.status, result.message)
    return EXIT_CODES.get(result.status, EXIT_CODES["failed_action_required"])
