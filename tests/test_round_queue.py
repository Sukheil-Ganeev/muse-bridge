import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ROUND_DIR = ROOT / "docs" / "rounds"


class RoundQueueTests(unittest.TestCase):
    def test_completed_round_requires_status_in_spec(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R999 | temporary round without status | ✅ done |\n",
                encoding="utf-8",
            )
            (round_dir / "R999-open.md").write_text(
                "# R999\n\nNo status line.\n", encoding="utf-8")

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.failures), 1,
                             "the round gate must reject completion without a spec status")
            self.assertIn("R999", result.failures[0][1])
            self.assertIn("no spec status", result.failures[0][1])

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

    def test_conflicting_spec_status_lines_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R999 | conflicting statuses | ✅ done |\n",
                encoding="utf-8",
            )
            (round_dir / "R999-conflict.md").write_text(
                "# R999\n\n"
                "**Статус:** готово локально\n"
                "**Статус:** в работе\n",
                encoding="utf-8",
            )

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.failures), 1,
                             "the round gate must reject conflicting statuses")
            self.assertIn("R999", result.failures[0][1])
            self.assertIn("conflicting spec statuses", result.failures[0][1])

    def test_blank_status_line_cannot_hide_following_completed_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R999 | hidden completion | 🟡 в работе |\n",
                encoding="utf-8",
            )
            (round_dir / "R999-blank-status.md").write_text(
                "# R999\n\n"
                "**Статус:**\n"
                "**Статус:** done\n",
                encoding="utf-8",
            )

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.failures), 1,
                             "the round gate must reject a blank status line")
            self.assertIn("R999", result.failures[0][1])

    def test_duplicate_round_queue_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R999 | same round | ✅ done |\n"
                "| R999 | same round again | ✅ done |\n",
                encoding="utf-8",
            )
            (round_dir / "R999-duplicate.md").write_text(
                "# R999\n\n**Статус:** done\n", encoding="utf-8")

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.failures), 1,
                             "the round gate must reject duplicate queue IDs")
            self.assertIn("R999", result.failures[0][1])
            self.assertIn("duplicate queue entries", result.failures[0][1])

    def test_completed_rounds_are_not_listed_as_in_progress(self):
        queue = (ROUND_DIR / "QUEUE.md").read_text(encoding="utf-8")
        stale = []
        seen_round_numbers = set()
        for line in queue.splitlines():
            row = re.match(r"^\|\s*R(\d{3})\s*\|.*\|\s*(.*?)\s*\|$",
                           line)
            if not row:
                continue
            round_number, queue_status = row.groups()
            if round_number in seen_round_numbers:
                stale.append(f"R{round_number}: duplicate queue entries")
                continue
            seen_round_numbers.add(round_number)
            specs = list(ROUND_DIR.glob(f"R{round_number}-*.md"))
            if len(specs) != 1:
                stale.append(f"R{round_number}: expected one spec, found {len(specs)}")
                continue
            spec = specs[0].read_text(encoding="utf-8")
            statuses = re.findall(
                r"^\*\*Статус:\*\*[ \t]*([^\r\n]*)\r?$", spec,
                flags=re.MULTILINE)
            queue_complete = "✅" in queue_status
            if not statuses:
                if queue_complete:
                    stale.append(
                        f"R{round_number}: completed queue entry has no spec status")
                continue
            if any(not status.strip() for status in statuses):
                stale.append(f"R{round_number}: blank spec status")
                continue
            spec_completion = [
                status.strip().lower().startswith(
                    ("done", "готово", "выполнено", "merged"))
                for status in statuses]
            if any(state != spec_completion[0] for state in spec_completion[1:]):
                stale.append(
                    f"R{round_number}: conflicting spec statuses")
                continue
            spec_complete = spec_completion[0]
            if spec_complete != queue_complete:
                stale.append(
                    f"R{round_number}: queue/spec completion mismatch")

        self.assertEqual(stale, [], "completed rounds still look open in QUEUE.md")


if __name__ == "__main__":
    unittest.main()
