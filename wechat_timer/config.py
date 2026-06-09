from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _parse_scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {'"', "'"} and value[-1:] == value[0]:
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if value.isdigit():
        return int(value)
    if "," in value:
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


def load_simple_yaml(path: Path) -> dict[str, object]:
    data: dict[str, object] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = _parse_scalar(value)
    return data


def _as_list(value: object, default: list[str]) -> list[str]:
    if value is None:
        return default
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _as_float_pair(value: object, default: tuple[float, float]) -> tuple[float, float]:
    if value is None:
        return default
    parts = value if isinstance(value, list) else str(value).split(",")
    if len(parts) != 2:
        return default
    try:
        return float(parts[0]), float(parts[1])
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class AppConfig:
    miniapp_name: str = "龙湖天街"
    run_time: str = "05:00"
    entry_mode: str = "search"
    locked_strategy: str = "retry_on_unlock"
    notify: str = "desktop"
    save_failure_screenshot: bool = True
    timeout_seconds: int = 30
    wechat_window_keywords: list[str] = field(default_factory=lambda: ["微信", "WeChat"])
    wechat_process_names: list[str] = field(default_factory=lambda: ["Weixin.exe", "WeChat.exe"])
    wechat_main_window_classes: list[str] = field(default_factory=lambda: ["Qt51514QWindowIcon"])
    miniapp_process_names: list[str] = field(default_factory=lambda: ["WeChatAppEx.exe"])
    wechat_shell_keywords: list[str] = field(default_factory=lambda: ["微信", "WeChat"])
    mini_program_entry_click_ratio: tuple[float, float] = (0.025, 0.503)
    wechat_focus_click_ratio: tuple[float, float] = (0.500, 0.020)
    mini_program_search_click_ratio: tuple[float, float] = (0.969, 0.107)
    mini_program_search_result_click_ratio: tuple[float, float] = (0.165, 0.220)
    wechat_mini_program_entry_template: str = r"assets\wechat_mini_program_entry.png"
    wechat_mini_program_entry_match_threshold: float = 0.78
    miniapp_logo_template: str = r"assets\longfor_logo.png"
    miniapp_logo_match_threshold: float = 0.88
    checkin_button_template: str = r"assets\longfor_checkin_button.png"
    checkin_button_match_threshold: float = 0.88
    member_tab_keywords: list[str] = field(default_factory=lambda: ["会员"])
    member_tab_click_ratio: tuple[float, float] = (0.870, 0.970)
    member_keywords: list[str] = field(default_factory=lambda: ["会员", "我的", "个人中心"])
    checkin_keywords: list[str] = field(default_factory=lambda: ["签到", "每日签到", "立即签到"])
    success_keywords: list[str] = field(
        default_factory=lambda: ["签到成功", "已签到", "积分到账", "今日已签到", "今日已获得"]
    )
    failure_keywords: list[str] = field(default_factory=lambda: ["认证", "登录", "授权", "网络异常", "失败", "错误"])

    @classmethod
    def load(cls, path: Path) -> "AppConfig":
        if not path.exists():
            return cls()
        data = load_simple_yaml(path)
        defaults = cls()
        return cls(
            miniapp_name=str(data.get("miniapp_name", defaults.miniapp_name)),
            run_time=str(data.get("run_time", defaults.run_time)),
            entry_mode=str(data.get("entry_mode", defaults.entry_mode)),
            locked_strategy=str(data.get("locked_strategy", defaults.locked_strategy)),
            notify=str(data.get("notify", defaults.notify)),
            save_failure_screenshot=bool(data.get("save_failure_screenshot", defaults.save_failure_screenshot)),
            timeout_seconds=int(data.get("timeout_seconds", defaults.timeout_seconds)),
            wechat_window_keywords=_as_list(data.get("wechat_window_keywords"), defaults.wechat_window_keywords),
            wechat_process_names=_as_list(data.get("wechat_process_names"), defaults.wechat_process_names),
            wechat_main_window_classes=_as_list(
                data.get("wechat_main_window_classes"),
                defaults.wechat_main_window_classes,
            ),
            miniapp_process_names=_as_list(data.get("miniapp_process_names"), defaults.miniapp_process_names),
            wechat_shell_keywords=_as_list(data.get("wechat_shell_keywords"), defaults.wechat_shell_keywords),
            mini_program_entry_click_ratio=_as_float_pair(
                data.get("mini_program_entry_click_ratio"),
                defaults.mini_program_entry_click_ratio,
            ),
            wechat_focus_click_ratio=_as_float_pair(
                data.get("wechat_focus_click_ratio"),
                defaults.wechat_focus_click_ratio,
            ),
            mini_program_search_click_ratio=_as_float_pair(
                data.get("mini_program_search_click_ratio"),
                defaults.mini_program_search_click_ratio,
            ),
            mini_program_search_result_click_ratio=_as_float_pair(
                data.get("mini_program_search_result_click_ratio"),
                defaults.mini_program_search_result_click_ratio,
            ),
            wechat_mini_program_entry_template=str(
                data.get(
                    "wechat_mini_program_entry_template",
                    defaults.wechat_mini_program_entry_template,
                )
            ),
            wechat_mini_program_entry_match_threshold=float(
                data.get(
                    "wechat_mini_program_entry_match_threshold",
                    defaults.wechat_mini_program_entry_match_threshold,
                )
            ),
            miniapp_logo_template=str(data.get("miniapp_logo_template", defaults.miniapp_logo_template)),
            miniapp_logo_match_threshold=float(
                data.get("miniapp_logo_match_threshold", defaults.miniapp_logo_match_threshold)
            ),
            checkin_button_template=str(
                data.get("checkin_button_template", defaults.checkin_button_template)
            ),
            checkin_button_match_threshold=float(
                data.get("checkin_button_match_threshold", defaults.checkin_button_match_threshold)
            ),
            member_tab_keywords=_as_list(data.get("member_tab_keywords"), defaults.member_tab_keywords),
            member_tab_click_ratio=_as_float_pair(
                data.get("member_tab_click_ratio"),
                defaults.member_tab_click_ratio,
            ),
            member_keywords=_as_list(data.get("member_keywords"), defaults.member_keywords),
            checkin_keywords=_as_list(data.get("checkin_keywords"), defaults.checkin_keywords),
            success_keywords=_as_list(data.get("success_keywords"), defaults.success_keywords),
            failure_keywords=_as_list(data.get("failure_keywords"), defaults.failure_keywords),
        )
