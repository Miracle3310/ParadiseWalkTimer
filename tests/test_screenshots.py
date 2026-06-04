from pathlib import Path
import unittest

from wechat_timer.screenshots import _relative_display_path


class ScreenshotPathTests(unittest.TestCase):
    def test_path_inside_project_is_relative(self):
        root = Path("project").resolve()
        path = root / "artifacts" / "screenshots" / "failure.png"

        display_path = _relative_display_path(path, root)

        self.assertEqual(display_path, str(Path("artifacts") / "screenshots" / "failure.png"))
        self.assertFalse(Path(display_path).is_absolute())

    def test_path_outside_project_uses_filename_only(self):
        root = Path("project").resolve()
        path = root.parent / "private" / "failure.png"

        display_path = _relative_display_path(path, root)

        self.assertEqual(display_path, "failure.png")


if __name__ == "__main__":
    unittest.main()
