from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .config import AppConfig
from .image_match import find_template_on_screen
from .windows_process import (
    activate_window_handle,
    find_top_level_window_handle,
    post_window_click,
    post_window_text,
    post_window_wheel,
    process_image_name,
)


class AutomationError(RuntimeError):
    pass


@dataclass(frozen=True)
class AutomationResult:
    status: str
    message: str


class WeChatCheckinAutomation:
    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self._process_name_cache: dict[int, str] = {}
        try:
            import uiautomation as auto
        except ImportError as exc:
            raise AutomationError(
                "Missing dependency 'uiautomation'. Run scripts\\setup.ps1 first."
            ) from exc
        self.auto = auto

    def run(self, dry_run: bool = False) -> AutomationResult:
        wechat = self._find_wechat_window()
        self._activate(wechat)
        self._open_mini_program(wechat)
        miniapp = self._wait_for_window_containing(
            [self.config.miniapp_name],
            timeout=self.config.timeout_seconds,
            process_names=self.config.miniapp_process_names,
        )
        self._activate(miniapp)
        self._click_member_tab(miniapp)
        time.sleep(1)

        visible_text = self._visible_text(miniapp)
        if self._contains_any(visible_text, self.config.success_keywords):
            self._close_window(miniapp)
            return AutomationResult("already_done", "Mini-program already shows a completed check-in state.")

        checkin_match = self._find_checkin_button_with_scroll(miniapp)
        if checkin_match is None:
            visible_text = self._visible_text(miniapp)
            if self._contains_any(visible_text, self.config.success_keywords):
                self._close_window(miniapp)
                return AutomationResult("already_done", "Mini-program already shows a completed check-in state.")
            if self._contains_any(visible_text, self.config.failure_keywords):
                raise AutomationError("Mini-program shows a failure or manual action keyword.")
            raise AutomationError(
                "Could not locate the Longfor '去签到' button on the member page. "
                "The page may have changed or may require manual action."
            )

        if dry_run:
            self._close_window(miniapp)
            return AutomationResult(
                "dry_run_ok",
                "Dry run visually located the Longfor check-in button without clicking it.",
            )

        self._click_visual_match(miniapp, checkin_match, "Longfor check-in button")
        outcome = self._wait_for_outcome_text(miniapp, self.config.timeout_seconds)
        if outcome == "success":
            self._close_window(miniapp)
            return AutomationResult("success", "Check-in success text was detected.")
        if outcome == "failure":
            raise AutomationError("Mini-program shows a failure or manual action keyword.")

        raise AutomationError(
            "Clicked the Longfor check-in entry but could not confirm success. "
            "A separate sign-in page may need an additional, explicitly recognized action."
        )

    def _find_wechat_window(self):
        window = self._wait_for_wechat_window(timeout=5, raise_on_timeout=False)
        if window is not None:
            return window

        hidden_handle = find_top_level_window_handle(
            process_names=self.config.wechat_process_names,
            class_names=self.config.wechat_main_window_classes,
            titles=self.config.wechat_window_keywords,
        )
        if hidden_handle:
            self.logger.info("restoring minimized/hidden WeChat main window handle=%s", hidden_handle)
            activate_window_handle(hidden_handle)
            window = self._wait_for_wechat_window(timeout=10, raise_on_timeout=False)
            if window is not None:
                return window

        if self._restore_wechat_from_shell():
            window = self._wait_for_wechat_window(timeout=10, raise_on_timeout=False)
            if window is not None:
                return window

        raise AutomationError(
            "Could not find a visible WeChat main window. The tool does not start WeChat or handle login. "
            "It tried the taskbar/system-tray WeChat icon, but no main interface appeared. "
            "Open the already logged-in WeChat main interface and retry. "
            f"Visible top-level windows: {self._top_level_summary()}"
        )

    def _restore_wechat_from_shell(self) -> bool:
        shell_classes = {
            "shell_traywnd",
            "notifyiconoverflowwindow",
            "xaml_explorerhostislandwindow",
        }
        try:
            top_level = self.auto.GetRootControl().GetChildren()
        except Exception:
            return False

        for window in top_level:
            class_name = (getattr(window, "ClassName", "") or "").lower()
            if class_name not in shell_classes:
                continue
            control = self._find_first_named(window, self.config.wechat_shell_keywords)
            if control is None:
                continue
            self.logger.info(
                "attempting to restore WeChat from taskbar/system tray name=%s class=%s",
                self._safe_name(control),
                class_name,
            )
            self._click_control(control, "taskbar/system-tray WeChat icon")
            return True
        self.logger.info("no taskbar/system-tray WeChat icon was exposed through UI Automation")
        return False

    def _wait_for_wechat_window(self, timeout: int, raise_on_timeout: bool = True):
        root = self.auto.GetRootControl()
        deadline = time.monotonic() + timeout
        expected_processes = {name.lower() for name in self.config.wechat_process_names}
        exact_titles = {name.lower() for name in self.config.wechat_window_keywords}
        while time.monotonic() < deadline:
            for child in root.GetChildren():
                name = self._safe_name(child)
                class_name = getattr(child, "ClassName", "") or ""
                process_name = self._control_process_name(child)
                if self._is_login_window(class_name):
                    self.logger.warning(
                        "ignoring WeChat login window name=%s class=%s process=%s",
                        name,
                        class_name,
                        process_name,
                    )
                    continue
                if (
                    process_name in expected_processes
                    and class_name.lower() in {name.lower() for name in self.config.wechat_main_window_classes}
                ):
                    self.logger.info(
                        "found WeChat window name=%s class=%s process=%s",
                        name,
                        class_name,
                        process_name,
                    )
                    return child
                if (
                    name.strip().lower() in exact_titles
                    and process_name in expected_processes
                    and class_name.lower() in {item.lower() for item in self.config.wechat_main_window_classes}
                ):
                    self.logger.info(
                        "found WeChat window by exact title name=%s class=%s process=%s",
                        name,
                        class_name,
                        process_name,
                    )
                    return child
            time.sleep(0.5)
        if raise_on_timeout:
            raise AutomationError("Could not find a visible WeChat main window.")
        return None

    def _wait_for_window_containing(
        self,
        keywords: Iterable[str],
        timeout: int,
        process_names: Iterable[str] | None = None,
    ):
        root = self.auto.GetRootControl()
        deadline = time.monotonic() + timeout
        keywords = [keyword for keyword in keywords if keyword]
        expected_processes = {name.lower() for name in process_names or []}
        while time.monotonic() < deadline:
            for child in root.GetChildren():
                name = self._safe_name(child)
                class_name = getattr(child, "ClassName", "") or ""
                process_name = self._control_process_name(child)
                if expected_processes and process_name not in expected_processes:
                    continue
                if any(keyword.lower() in name.lower() for keyword in keywords):
                    self.logger.info(
                        "found window name=%s class=%s process=%s",
                        name,
                        class_name,
                        process_name,
                    )
                    return child
                if "WeChat" in class_name and any(keyword in {"微信", "WeChat"} for keyword in keywords):
                    self.logger.info("found WeChat window by class=%s name=%s", class_name, name)
                    return child
            time.sleep(0.5)
        raise AutomationError(f"Could not find window containing any of: {', '.join(keywords)}")

    def _activate(self, control) -> None:
        handle = self._native_window_handle(control)
        if handle:
            if activate_window_handle(handle):
                self.logger.info("activated window through Win32 handle=%s", handle)
            else:
                self.logger.debug("Win32 window activation returned false handle=%s", handle)
        try:
            control.SetActive()
        except Exception:
            self.logger.debug("SetActive failed", exc_info=True)
        try:
            control.SetFocus()
        except Exception:
            self.logger.debug("SetFocus failed", exc_info=True)
        time.sleep(0.5)

    def _open_mini_program(self, wechat) -> None:
        entry = self._find_first_named(wechat, ["小程序", "Mini Programs", "Mini Program"])
        if entry is not None:
            self._click_control(entry, "mini-program entry")
        elif self._click_mini_program_entry_by_template(wechat):
            pass
        else:
            self._click_mini_program_entry_by_ratio(wechat)

        mini_program_page = self._wait_for_top_level_window_containing(
            ["小程序", "Mini Programs", "Mini Program"],
            self.config.wechat_process_names + self.config.miniapp_process_names,
            timeout=8,
        )
        if mini_program_page is None:
            raise AutomationError(
                "Mini-program page did not appear after clicking the entry. "
                f"Visible text: {self._visible_text_summary(self.auto.GetRootControl())}"
            )

        if self._click_mini_program_logo(mini_program_page):
            time.sleep(2)
            return

        target = self._find_first_named_in_processes(
            self.auto.GetRootControl(),
            [self.config.miniapp_name],
            self.config.wechat_process_names + self.config.miniapp_process_names,
        )
        if target is not None:
            self._click_control(target, "named mini-program")
            time.sleep(2)
            return

        if self.config.entry_mode != "search":
            raise AutomationError(
                f"Could not find mini-program '{self.config.miniapp_name}' through UI Automation, "
                "and entry_mode is not search."
            )

        self._search_and_open_mini_program(mini_program_page)

    def _click_mini_program_entry_by_template(self, wechat) -> bool:
        rectangle = self._window_rectangle(wechat)
        if rectangle is None:
            return False
        left, top, right, bottom = rectangle
        sidebar_region = (
            left,
            max(top, top + 80),
            min(right, left + max(90, int((right - left) * 0.08))),
            max(top, bottom - 80),
        )
        template_path = Path(self.config.wechat_mini_program_entry_template)
        match = find_template_on_screen(
            template_path=template_path,
            region=sidebar_region,
            threshold=self.config.wechat_mini_program_entry_match_threshold,
            logger=self.logger,
            label="WeChat mini-program entry",
        )
        if match is None:
            return False
        self._click_visual_match(wechat, match, "WeChat mini-program entry")
        return True

    def _click_mini_program_logo(self, mini_program_page) -> bool:
        rectangle = self._window_rectangle(mini_program_page)
        if rectangle is None:
            return False
        template_path = Path(self.config.miniapp_logo_template)
        match = find_template_on_screen(
            template_path=template_path,
            region=rectangle,
            threshold=self.config.miniapp_logo_match_threshold,
            logger=self.logger,
            label="mini-program logo",
        )
        if match is None:
            return False
        x, y, score = match
        handle = self._native_window_handle(mini_program_page)
        self.logger.info(
            "clicking matched mini-program logo name=%s score=%.3f screen=(%d,%d)",
            self.config.miniapp_name,
            score,
            x,
            y,
        )
        if handle and post_window_click(handle, x, y):
            return True
        self.auto.Click(x, y)
        return True

    def _click_member_tab(self, miniapp) -> None:
        rectangle = self._window_rectangle(miniapp)
        if rectangle is None:
            raise AutomationError("Could not read the mini-program window rectangle before opening member page.")

        target = self._find_bottom_named(miniapp, self.config.member_tab_keywords, rectangle)
        if target is not None:
            self._click_control(target, "member bottom tab")
            return

        self._click_window_ratio(miniapp, self.config.member_tab_click_ratio, "member bottom tab")

    def _find_checkin_button_with_scroll(self, miniapp) -> tuple[int, int, float] | None:
        deadline = time.monotonic() + self.config.timeout_seconds
        scroll_deltas = [120] * 8 + [-120] * 8
        scroll_index = 0
        while time.monotonic() < deadline:
            match = self._wait_for_visual_match(
                miniapp,
                template_path=Path(self.config.checkin_button_template),
                threshold=self.config.checkin_button_match_threshold,
                label="Longfor check-in button",
                timeout=1,
            )
            if match is not None:
                return match

            visible_text = self._visible_text(miniapp)
            if self._contains_any(visible_text, self.config.success_keywords):
                return None
            if scroll_index >= len(scroll_deltas):
                break
            self._scroll_member_page_step(miniapp, wheel_delta=scroll_deltas[scroll_index])
            scroll_index += 1
        return None

    def _scroll_member_page_step(self, miniapp, wheel_delta: int) -> None:
        rectangle = self._window_rectangle(miniapp)
        if rectangle is None:
            return
        left, top, right, bottom = rectangle
        x = int(left + (right - left) * 0.50)
        y = int(top + (bottom - top) * 0.62)
        handle = self._native_window_handle(miniapp)
        self.logger.info("scroll member page wheel_delta=%d screen=(%d,%d)", wheel_delta, x, y)
        if handle and post_window_wheel(handle, x, y, wheel_delta):
            time.sleep(0.35)
            return
        self.logger.debug("member page posted wheel scroll failed handle=%s", handle)

    def _wait_for_visual_match(
        self,
        window,
        template_path: Path,
        threshold: float,
        label: str,
        timeout: int,
    ) -> tuple[int, int, float] | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            rectangle = self._window_rectangle(window)
            if rectangle is None:
                raise AutomationError(f"Could not read the window rectangle while locating {label}.")
            match = find_template_on_screen(
                template_path=template_path,
                region=rectangle,
                threshold=threshold,
                logger=self.logger,
                label=label,
            )
            if match is not None:
                return match
            time.sleep(0.75)
        return None

    def _click_visual_match(
        self,
        window,
        match: tuple[int, int, float],
        label: str,
    ) -> None:
        x, y, score = match
        self.logger.info("clicking matched %s score=%.3f screen=(%d,%d)", label, score, x, y)
        handle = self._native_window_handle(window)
        if handle and post_window_click(handle, x, y):
            return
        try:
            self.auto.Click(x, y)
        except Exception as exc:
            raise AutomationError(f"Could not click matched {label}: {exc}") from exc

    def _search_and_open_mini_program(self, mini_program_page) -> None:
        self._activate(mini_program_page)
        self._click_window_ratio(
            mini_program_page,
            self.config.mini_program_search_click_ratio,
            "mini-program search button",
        )
        time.sleep(1)

        edit = self._find_first_by_control_type(mini_program_page, "EditControl")
        if edit is not None:
            self.logger.info("typing mini-program name into UIA search edit")
            try:
                edit.SetValue(self.config.miniapp_name)
            except Exception:
                edit.Click()
                self.auto.SendKeys(self.config.miniapp_name)
        else:
            self.logger.info("search edit has no UIA control; typing mini-program name into focused field")
            handle = self._native_window_handle(mini_program_page)
            if not handle or not post_window_text(handle, self.config.miniapp_name):
                self.auto.SendKeys(self.config.miniapp_name)
        time.sleep(2)

        target = self._find_first_named_in_processes(
            self.auto.GetRootControl(),
            [self.config.miniapp_name],
            self.config.wechat_process_names + self.config.miniapp_process_names,
        )
        if target is not None:
            self._click_control(target, "mini-program search result")
        else:
            self._click_window_ratio(
                mini_program_page,
                self.config.mini_program_search_result_click_ratio,
                "first exact-name mini-program search result",
            )
        time.sleep(2)

    def _click_mini_program_entry_by_ratio(self, wechat) -> None:
        class_name = (getattr(wechat, "ClassName", "") or "").lower()
        if "qt" not in class_name:
            raise AutomationError(
                "Could not find mini-program entry through UI Automation, and the WeChat window "
                f"class is not eligible for coordinate fallback: {class_name!r}."
            )

        self._click_window_ratio(
            wechat,
            self.config.wechat_focus_click_ratio,
            "WeChat title-bar focus area",
        )
        time.sleep(0.5)
        self._click_window_ratio(
            wechat,
            self.config.mini_program_entry_click_ratio,
            "mini-program entry",
        )

    def _click_window_ratio(
        self,
        window,
        ratio: tuple[float, float],
        label: str,
    ) -> None:
        rectangle = self._window_rectangle(window)
        if rectangle is None:
            raise AutomationError(f"Could not read the window rectangle for {label} coordinate fallback.")

        left, top, right, bottom = rectangle
        width = right - left
        height = bottom - top
        if width < 400 or height < 400:
            raise AutomationError(
                f"Window rectangle is too small for {label} coordinate fallback: {left},{top},{right},{bottom}."
            )

        ratio_x, ratio_y = ratio
        x = int(round(left + width * ratio_x))
        y = int(round(top + height * ratio_y))
        self.logger.info(
            "%s has no usable UIA name; clicking configured window-relative ratio "
            "x=%.3f y=%.3f at screen=(%d,%d) rect=(%d,%d,%d,%d)",
            label,
            ratio_x,
            ratio_y,
            x,
            y,
            int(left),
            int(top),
            int(right),
            int(bottom),
        )
        handle = self._native_window_handle(window)
        if handle and post_window_click(handle, x, y):
            self.logger.info("posted %s click directly to window handle=%s", label, handle)
            return
        try:
            self.auto.Click(x, y)
        except Exception as exc:
            raise AutomationError(f"Could not click {label} coordinate fallback: {exc}") from exc

    @staticmethod
    def _window_rectangle(window) -> tuple[int, int, int, int] | None:
        rectangle = getattr(window, "BoundingRectangle", None)
        if rectangle is None:
            return None
        left = int(float(getattr(rectangle, "left", getattr(rectangle, "Left", 0))))
        top = int(float(getattr(rectangle, "top", getattr(rectangle, "Top", 0))))
        right = int(float(getattr(rectangle, "right", getattr(rectangle, "Right", 0))))
        bottom = int(float(getattr(rectangle, "bottom", getattr(rectangle, "Bottom", 0))))
        if right <= left or bottom <= top:
            return None
        return left, top, right, bottom

    def _find_top_level_window_exact(
        self,
        names: Iterable[str],
        process_names: Iterable[str] | None = None,
    ):
        expected_names = {name.strip().lower() for name in names if name}
        expected_processes = {name.lower() for name in process_names or []}
        try:
            children = self.auto.GetRootControl().GetChildren()
        except Exception:
            return None
        for child in children:
            if expected_processes and self._control_process_name(child) not in expected_processes:
                continue
            if self._safe_name(child).strip().lower() in expected_names:
                return child
        return None

    def _find_top_level_window_containing(
        self,
        names: Iterable[str],
        process_names: Iterable[str] | None = None,
    ):
        expected_processes = {name.lower() for name in process_names or []}
        try:
            children = self.auto.GetRootControl().GetChildren()
        except Exception:
            return None
        for child in children:
            if expected_processes and self._control_process_name(child) not in expected_processes:
                continue
            if self._find_first_named(child, names) is not None:
                return child
        return None

    def _wait_for_top_level_window_containing(
        self,
        names: Iterable[str],
        process_names: Iterable[str] | None = None,
        timeout: int = 8,
    ):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            window = self._find_top_level_window_containing(names, process_names)
            if window is not None:
                return window
            time.sleep(0.5)
        return None

    def _click_first_named(self, root, keywords: Iterable[str], label: str) -> None:
        control = self._find_first_named(root, keywords)
        if control is None:
            raise AutomationError(
                f"Could not find {label}. Visible text: {self._visible_text_summary(root)}"
            )
        self._click_control(control, label)

    def _click_control(self, control, label: str) -> None:
        name = self._safe_name(control)
        self.logger.info("click %s name=%s", label, name)
        try:
            control.Click()
        except Exception:
            try:
                control.GetInvokePattern().Invoke()
            except Exception as exc:
                raise AutomationError(f"Could not click {label}: {exc}") from exc
        time.sleep(1)

    def _find_first_named(self, root, keywords: Iterable[str]):
        keywords = [keyword.lower() for keyword in keywords if keyword]
        queue = [root]
        visited = 0
        while queue and visited < 2000:
            control = queue.pop(0)
            visited += 1
            name = self._safe_name(control)
            if name and any(keyword in name.lower() for keyword in keywords):
                return control
            try:
                queue.extend(control.GetChildren())
            except Exception:
                continue
        return None

    def _find_bottom_named(
        self,
        root,
        keywords: Iterable[str],
        window_rectangle: tuple[int, int, int, int],
    ):
        keywords = {keyword.strip().lower() for keyword in keywords if keyword.strip()}
        _left, top, _right, bottom = window_rectangle
        height = bottom - top
        min_top = bottom - max(180, int(height * 0.18))
        queue = [root]
        visited = 0
        while queue and visited < 2000:
            control = queue.pop(0)
            visited += 1
            name = self._safe_name(control).strip()
            if name.lower() in keywords:
                rectangle = self._window_rectangle(control)
                if rectangle is not None and rectangle[1] >= min_top:
                    return control
            try:
                queue.extend(control.GetChildren())
            except Exception:
                continue
        return None

    def _find_first_by_control_type(self, root, control_type_name: str):
        queue = [root]
        visited = 0
        while queue and visited < 2000:
            control = queue.pop(0)
            visited += 1
            try:
                if control.ControlTypeName == control_type_name:
                    return control
            except Exception:
                pass
            try:
                queue.extend(control.GetChildren())
            except Exception:
                continue
        return None

    def _find_first_named_in_processes(
        self,
        root,
        keywords: Iterable[str],
        process_names: Iterable[str],
    ):
        expected_processes = {name.lower() for name in process_names}
        try:
            top_level = root.GetChildren()
        except Exception:
            return None
        for window in top_level:
            if self._control_process_name(window) not in expected_processes:
                continue
            control = self._find_first_named(window, keywords)
            if control is not None:
                return control
        return None

    def _wait_until_text(self, root, keywords: Iterable[str], timeout: int) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            text = self._visible_text(root)
            if self._contains_any(text, keywords):
                return
            time.sleep(0.5)
        raise AutomationError(f"Timed out waiting for text: {', '.join(keywords)}")

    def _wait_for_outcome_text(self, root, timeout: int) -> str | None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            text = self._visible_text(root)
            if self._contains_any(text, self.config.success_keywords):
                return "success"
            if self._contains_any(text, self.config.failure_keywords):
                return "failure"
            time.sleep(0.5)
        return None

    def _visible_text(self, root) -> str:
        names: list[str] = []
        queue = [root]
        visited = 0
        while queue and visited < 3000:
            control = queue.pop(0)
            visited += 1
            name = self._safe_name(control)
            if name:
                names.append(name)
            try:
                queue.extend(control.GetChildren())
            except Exception:
                continue
        text = "\n".join(dict.fromkeys(names))
        self.logger.debug("visible text sample=%s", text[:1000])
        return text

    def _visible_text_summary(self, root, limit: int = 600) -> str:
        text = self._visible_text(root).replace("\n", " | ")
        return text[:limit] if text else "<no UIA text exposed>"

    def _top_level_summary(self, limit: int = 12) -> str:
        items: list[str] = []
        try:
            children = self.auto.GetRootControl().GetChildren()
        except Exception:
            return "<could not enumerate desktop windows>"
        for child in children[:limit]:
            items.append(
                f"name={self._safe_name(child)!r}, class={getattr(child, 'ClassName', '')!r}, "
                f"process={self._control_process_name(child)!r}"
            )
        return "; ".join(items) if items else "<no top-level windows exposed>"

    def _control_process_name(self, control) -> str:
        try:
            pid = int(control.ProcessId)
        except Exception:
            return ""
        if pid not in self._process_name_cache:
            image = process_image_name(pid)
            self._process_name_cache[pid] = Path(image).name.lower() if image else ""
        return self._process_name_cache[pid]

    @staticmethod
    def _native_window_handle(control) -> int:
        try:
            return int(control.NativeWindowHandle)
        except Exception:
            return 0

    @staticmethod
    def _is_login_window(class_name: str) -> bool:
        return "loginwindow" in class_name.lower()

    @staticmethod
    def _contains_any(text: str, keywords: Iterable[str]) -> bool:
        lowered = text.lower()
        return any(keyword.lower() in lowered for keyword in keywords if keyword)

    @staticmethod
    def _safe_name(control) -> str:
        try:
            return control.Name or ""
        except Exception:
            return ""

    def _close_window(self, window) -> None:
        self._activate(window)
        close = self._find_first_named(window, ["关闭", "Close"])
        if close is not None:
            try:
                rectangle = self._window_rectangle(close)
                if rectangle is not None:
                    close.Click()
                    return
            except Exception:
                self.logger.debug("close button click failed", exc_info=True)
        try:
            self.auto.SendKeys("{Alt}{F4}")
        except Exception:
            self.logger.debug("Alt+F4 close failed", exc_info=True)
