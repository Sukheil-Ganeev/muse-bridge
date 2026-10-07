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

    def test_round_ids_above_999_are_checked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R1000 | temporary open round | ✅ done |\n",
                encoding="utf-8",
            )
            (round_dir / "R1000-open.md").write_text(
                "# R1000\n\n**Статус:** в работе\n",
                encoding="utf-8",
            )

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.failures), 1,
                             "the round gate must check four-digit round IDs")
            self.assertIn("R1000", result.failures[0][1])

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

    def test_latest_round_specs_must_be_in_queue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            round_ids = (1000, 990, 980, 970, 1010)
            for round_id in round_ids:
                (round_dir / f"R{round_id}-round.md").write_text(
                    f"# R{round_id}\n\n**Статус:** done\n",
                    encoding="utf-8")
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R1000 | recent | ✅ done |\n"
                "| R990 | recent | ✅ done |\n"
                "| R980 | recent | ✅ done |\n"
                "| R970 | stale | ✅ done |\n",
                encoding="utf-8",
            )

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(len(result.failures), 1,
                             "the gate must detect a recent spec omitted from the queue")
            self.assertIn("R1010", result.failures[0][1])
            self.assertIn("R970", result.failures[0][1])

    def test_done_synonym_is_recognized_as_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_dir = Path(temp_dir)
            (round_dir / "QUEUE.md").write_text(
                "| Раунд | Тема | Статус |\n"
                "|---|---|---|\n"
                "| R999 | completed synonym | ✅ PR #1 |\n",
                encoding="utf-8",
            )
            (round_dir / "R999-completed.md").write_text(
                "# R999\n\n**Статус:** ✅ сделано\n", encoding="utf-8")

            result = unittest.TestResult()
            case = RoundQueueTests(
                "test_completed_rounds_are_not_listed_as_in_progress")
            with mock.patch(__name__ + ".ROUND_DIR", round_dir):
                case.run(result)

            self.assertEqual(result.errors, [])
            self.assertEqual(result.failures, [],
                             "the gate must recognize 'сделано' as completion")

    def test_completed_rounds_are_not_listed_as_in_progress(self):
        queue = (ROUND_DIR / "QUEUE.md").read_text(encoding="utf-8")
        stale = []
        seen_round_numbers = set()
        for line in queue.splitlines():
            row = re.match(r"^\|\s*R([0-9]+)\s*\|.*\|\s*(.*?)\s*\|$",
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
            spec_completion = []
            for status in statuses:
                normalized_status = status.strip().lower()
                if normalized_status.startswith("✅"):
                    normalized_status = normalized_status[1:].strip()
                spec_completion.append(normalized_status.startswith(
                    ("done", "готово", "выполнено", "сделано", "merged")))
            if any(state != spec_completion[0] for state in spec_completion[1:]):
                stale.append(
                    f"R{round_number}: conflicting spec statuses")
                continue
            spec_complete = spec_completion[0]
            if spec_complete != queue_complete:
                stale.append(
                    f"R{round_number}: queue/spec completion mismatch")

        spec_round_numbers = set()
        for spec_path in ROUND_DIR.glob("R*-*.md"):
            match = re.match(r"^R([0-9]+)-", spec_path.name)
            if match:
                spec_round_numbers.add(match.group(1))
        expected_recent = set(sorted(
            spec_round_numbers, key=int, reverse=True)[:4])
        if seen_round_numbers != expected_recent:
            missing = sorted(expected_recent - seen_round_numbers,
                             key=int, reverse=True)
            stale_entries = sorted(seen_round_numbers - expected_recent,
                                   key=int, reverse=True)
            details = []
            if missing:
                details.append("missing " + ", ".join(
                    f"R{number}" for number in missing))
            if stale_entries:
                details.append("outside recent window " + ", ".join(
                    f"R{number}" for number in stale_entries))
            stale.append("QUEUE.md must list the four latest round specs: "
                         + "; ".join(details))

        self.assertEqual(stale, [], "completed rounds still look open in QUEUE.md")


if __name__ == "__main__":
    unittest.main()
