import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ROUND_DIR = ROOT / "docs" / "rounds"


class RoundQueueTests(unittest.TestCase):
    def test_open_spec_cannot_have_completed_queue_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R999 | temporary open round | ✅ done |\n",
                encoding="utf-8",
            )
            (round_dir / "R999-open.md").write_text(
                "# R999\n\n**Статус:** в работе\n",
                encoding="utf-8",
            )

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.failures), 1,
                             "the round gate must reject R999's false ✅")
            self.assertIn("R999", result.failures[0][1])

    def test_completed_rounds_are_not_listed_as_in_progress(self):
        queue = (ROUND_DIR / "QUEUE.md").read_text(encoding="utf-8")
        stale = []
        for line in queue.splitlines():
            row = re.match(r"^\|\s*R(\d{3})\s*\|.*\|\s*(.*?)\s*\|$",
                           line)
            if not row:
                continue
            round_number, queue_status = row.groups()
            specs = list(ROUND_DIR.glob(f"R{round_number}-*.md"))
            if len(specs) != 1:
                stale.append(f"R{round_number}: expected one spec, found {len(specs)}")
                continue
            spec = specs[0].read_text(encoding="utf-8")
            status = re.search(r"^\*\*Статус:\*\*\s*(.+)$", spec,
                               flags=re.MULTILINE)
            if status:
                spec_complete = status.group(1).strip().lower().startswith(
                    ("done", "готово"))
                queue_complete = "✅" in queue_status
                if spec_complete != queue_complete:
                    stale.append(
                        f"R{round_number}: queue/spec completion mismatch")

        self.assertEqual(stale, [], "completed rounds still look open in QUEUE.md")


if __name__ == "__main__":
    unittest.main()
