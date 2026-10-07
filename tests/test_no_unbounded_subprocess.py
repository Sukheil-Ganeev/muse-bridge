"""Gate: subprocess children must not hang forever in live code.

Rules for tracked .py files (outside frozen dirs):
- subprocess.run/call/check_call/check_output need timeout=...
- every X.wait()/X.communicate() on a subprocess needs timeout=...
- a subprocess.Popen whose variable is never waited on in the file must
  carry a '# timeout:' comment explaining what bounds the child.
"""
from __future__ import annotations

import ast
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_PREFIXES = (
    ".agents/",
    "docs/",
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
)
MARKER = "# timeout"


def _live_py_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "*.py"],
        cwd=ROOT, capture_output=True, check=True, timeout=30,
    )
    files = []
    for raw in out.stdout.split(b"\x00"):
        if not raw:
            continue
        rel = raw.decode("utf-8")
        if any(rel.startswith(p) for p in SKIP_PREFIXES):
            continue
        files.append(ROOT / rel)
    return files


class _PopenVars(ast.NodeVisitor):
    def __init__(self) -> None:
        self.popen_names: dict[str, int] = {}  # var -> lineno
        self.bounded: set[str] = set()
        self.unbounded_waits: list[tuple[str, int]] = []
        self.direct_calls_missing: list[int] = []

    def _is_subprocess_call(self, node: ast.Call, names: set[str]) -> bool:
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in names:
            src = ast.unparse(f)
            return "subprocess" in src
        return False

    def visit_Call(self, node: ast.Call) -> None:
        if self._is_subprocess_call(
            node, {"run", "call", "check_call", "check_output"}
        ):
            if not any(k.arg == "timeout" for k in node.keywords):
                self.direct_calls_missing.append(node.lineno)
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in ("wait", "communicate"):
            recv = f.value
            if isinstance(recv, ast.Name):
                if any(k.arg == "timeout" for k in node.keywords):
                    self.bounded.add(recv.id)
                else:
                    self.unbounded_waits.append((recv.id, node.lineno))
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        value = node.value
        if (
            isinstance(value, ast.Call)
            and self._is_subprocess_call(value, {"Popen"})
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.popen_names.setdefault(target.id, node.lineno)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            call = item.context_expr
            if (
                isinstance(call, ast.Call)
                and self._is_subprocess_call(call, {"Popen"})
            ):
                self.popen_names.setdefault("<with>", call.lineno)
        self.generic_visit(node)


class TestNoUnboundedSubprocess(unittest.TestCase):
    def test_live_subprocess_bounded(self) -> None:
        problems: list[str] = []
        for path in _live_py_files():
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8", errors="replace")
                )
            except SyntaxError:
                continue
            lines = path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            visitor = _PopenVars()
            visitor.visit(tree)
            rel = path.relative_to(ROOT)
            for lineno in visitor.direct_calls_missing:
                problems.append(f"{rel}:{lineno} subprocess call without timeout=")
            for name, lineno in visitor.unbounded_waits:
                if name in visitor.popen_names:
                    problems.append(
                        f"{rel}:{lineno} wait()/communicate() without timeout="
                    )
            for name, lineno in visitor.popen_names.items():
                if name in visitor.bounded:
                    continue
                line = lines[lineno - 1] if lineno <= len(lines) else ""
                if MARKER not in line:
                    problems.append(
                        f"{rel}:{lineno} Popen never waited on; "
                        "add '# timeout:' note or bounded wait"
                    )
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
