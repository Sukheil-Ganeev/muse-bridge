"""AST-гейт: Path.mkdir()/os.makedirs() обязаны передавать exist_ok во всех tracked .py.

Без exist_ok повторный запуск падает с FileExistsError — сценарии
создания каталогов должны быть идемпотентными. os.mkdir (без 's')
исключён: у него нет параметра exist_ok.
"""

import ast
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PREFIXES = (".agents/",)


def _tracked_py() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files", "-z", "*.py"], cwd=ROOT, timeout=60
    ).decode().split("\x00")
    return [n for n in out if n and not n.startswith(SKIP_PREFIXES)]


def _is_mkdir_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name) and node.func.id == "makedirs":
        return True
    if isinstance(node.func, ast.Attribute) and node.func.attr in ("mkdir", "makedirs"):
        if node.func.attr == "mkdir" and isinstance(node.func.value, ast.Name) and node.func.value.id == "os":
            return False  # os.mkdir не принимает exist_ok
        return True
    return False


class TestUnboundedMkdir(unittest.TestCase):
    def test_mkdir_calls_pass_exist_ok(self):
        hits = []
        for name in _tracked_py():
            try:
                tree = ast.parse(
                    (ROOT / name).read_text(encoding="utf-8-sig"), filename=name
                )
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not _is_mkdir_call(node):
                    continue
                if not any(k.arg == "exist_ok" for k in node.keywords):
                    hits.append(f"{name}:{node.lineno}")
        self.assertEqual(hits, [], "mkdir/makedirs without exist_ok")


if __name__ == "__main__":
    unittest.main()
