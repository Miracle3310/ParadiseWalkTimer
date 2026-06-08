import os
import unittest

from wechat_timer.windows_process import (
    activate_window_handle,
    find_top_level_window_handle,
    get_window_state,
    post_window_click,
    post_window_text,
    post_window_wheel,
    process_image_name,
    restore_window_state,
)


class WindowsProcessTests(unittest.TestCase):
    def test_current_process_has_python_image_name(self):
        image = process_image_name(os.getpid())
        self.assertTrue(image.lower().endswith("python.exe"), image)

    def test_invalid_window_handle_is_not_activated(self):
        self.assertFalse(activate_window_handle(0))
        self.assertIsNone(get_window_state(0))
        self.assertFalse(restore_window_state(None))
        self.assertFalse(post_window_click(0, 10, 10))
        self.assertFalse(post_window_text(0, "test"))
        self.assertFalse(post_window_wheel(0, 10, 10, -120))

    def test_no_window_for_impossible_process_name(self):
        handle = find_top_level_window_handle(
            process_names=["this-process-does-not-exist.exe"],
            class_names=["NoClass"],
            titles=["NoTitle"],
        )
        self.assertEqual(handle, 0)


if __name__ == "__main__":
    unittest.main()
