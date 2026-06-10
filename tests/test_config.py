from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from wechat_timer.config import AppConfig


class ConfigTests(unittest.TestCase):
    def test_loads_simple_yaml_values(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text(
                "\n".join(
                    [
                        "miniapp_name: 龙湖天街",
                        'run_time: "03:00"',
                        "save_failure_screenshot: false",
                        "timeout_seconds: 12",
                        "wechat_process_names: Weixin.exe,WeChat.exe",
                        "wechat_main_window_classes: Qt51514QWindowIcon",
                        "miniapp_process_names: WeChatAppEx.exe",
                        "wechat_shell_keywords: 微信,WeChat",
                        "mini_program_entry_click_ratio: 0.025,0.503",
                        "wechat_focus_click_ratio: 0.500,0.020",
                        "mini_program_search_click_ratio: 0.969,0.107",
                        "mini_program_search_result_click_ratio: 0.165,0.220",
                        r"wechat_mini_program_entry_template: assets\wechat_mini_program_entry.png",
                        "wechat_mini_program_entry_match_threshold: 0.81",
                        r"miniapp_logo_template: assets\longfor_logo.png",
                        "miniapp_logo_match_threshold: 0.88",
                        r"checkin_button_template: assets\longfor_checkin_button.png",
                        "checkin_button_match_threshold: 0.91",
                        "member_tab_keywords: 会员",
                        "member_tab_click_ratio: 0.870,0.970",
                        "member_keywords: 会员,我的",
                        "success_keywords: 已签到,今日已获得",
                    ]
                ),
                encoding="utf-8",
            )

            config = AppConfig.load(path)

        self.assertEqual(config.miniapp_name, "龙湖天街")
        self.assertEqual(config.run_time, "03:00")
        self.assertFalse(config.save_failure_screenshot)
        self.assertEqual(config.timeout_seconds, 12)
        self.assertEqual(config.wechat_process_names, ["Weixin.exe", "WeChat.exe"])
        self.assertEqual(config.wechat_main_window_classes, ["Qt51514QWindowIcon"])
        self.assertEqual(config.miniapp_process_names, ["WeChatAppEx.exe"])
        self.assertEqual(config.wechat_shell_keywords, ["微信", "WeChat"])
        self.assertEqual(config.mini_program_entry_click_ratio, (0.025, 0.503))
        self.assertEqual(config.wechat_focus_click_ratio, (0.500, 0.020))
        self.assertEqual(config.mini_program_search_click_ratio, (0.969, 0.107))
        self.assertEqual(config.mini_program_search_result_click_ratio, (0.165, 0.220))
        self.assertEqual(config.wechat_mini_program_entry_template, r"assets\wechat_mini_program_entry.png")
        self.assertEqual(config.wechat_mini_program_entry_match_threshold, 0.81)
        self.assertEqual(config.miniapp_logo_template, r"assets\longfor_logo.png")
        self.assertEqual(config.miniapp_logo_match_threshold, 0.88)
        self.assertEqual(config.checkin_button_template, r"assets\longfor_checkin_button.png")
        self.assertEqual(config.checkin_button_match_threshold, 0.91)
        self.assertEqual(config.member_tab_keywords, ["会员"])
        self.assertEqual(config.member_tab_click_ratio, (0.870, 0.970))
        self.assertEqual(config.member_keywords, ["会员", "我的"])
        self.assertEqual(config.success_keywords, ["已签到", "今日已获得"])


if __name__ == "__main__":
    unittest.main()
