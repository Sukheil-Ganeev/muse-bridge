import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUND_DIR = ROOT / "docs" / "rounds"


class RoundQueueTests(unittest.TestCase):
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
            if (status and status.group(1).strip().lower().startswith(
                    ("done", "готово")) and "✅" not in queue_status):
                stale.append(f"R{round_number}: {queue_status}")

        self.assertEqual(stale, [], "completed rounds still look open in QUEUE.md")


if __name__ == "__main__":
    unittest.main()
