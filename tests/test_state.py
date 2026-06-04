from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from wechat_timer.state import RunState


class StateTests(unittest.TestCase):
    def test_pending_locked_round_trip(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            state = RunState.load(path)
            state.mark_pending_locked("2026-06-04")
            state.save()

            loaded = RunState.load(path)

        self.assertEqual(loaded.pending_locked_date, "2026-06-04")
        self.assertEqual(loaded.last_status, "pending_locked")

    def test_success_clears_pending(self):
        state = RunState(path=Path("unused"))
        state.mark_pending_locked("2026-06-04")
        state.record_success("2026-06-04", "success", "done")

        self.assertIsNone(state.pending_locked_date)
        self.assertEqual(state.last_success_date, "2026-06-04")
        self.assertEqual(state.last_status, "success")


if __name__ == "__main__":
    unittest.main()

