"""Codex Bridge — use your ChatGPT/Codex subscription in OpenAI-compatible apps.

Optional companion to muse_bridge.py. Serves the same OpenAI-compatible API,
but each request runs `codex exec` in a read-only sandbox (so it uses your
ChatGPT subscription login instead of a billed API key).

Endpoints
---------
  GET  /v1/models
  POST /v1/chat/completions   (non-streaming)

Requirements
------------
- Python 3.9+
- Codex CLI installed and logged in (`codex` on PATH)

Usage
-----
  python codex_bridge.py        # listens on 127.0.0.1:11472

Optional environment variables:
  CODEX_BRIDGE_PORT   port (default 11472)
  CODEX_BRIDGE_EXE    full path to codex (auto-detected if unset)
"""

import http.server
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _env_int(name: str, fallback: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return fallback
    try:
        return int(raw)
    except ValueError:
        print(f"{name}={raw!r} is not an integer, using {fallback}", file=sys.stderr, flush=True)
        return fallback


PORT = _env_int("CODEX_BRIDGE_PORT", 11472)
EXEC_TIMEOUT = 280

MODELS = [
    "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini",
]


def find_codex() -> str:
    override = os.environ.get("CODEX_BRIDGE_EXE")
    if override and Path(override).exists():
        return override
    exe = shutil.which("codex")
    if exe:
        return exe
    if os.name == "nt":
        for name in ("codex.cmd", "codex.exe", "codex"):
            found = shutil.which(name)
            if found:
                return found
    return "codex"


CODEX_EXE = find_codex()


def build_prompt(messages) -> str:
    parts = []
    for m in messages or []:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict))
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts) or "(empty)"


def run_codex(model: str, prompt: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as pf:
        pf.write(prompt)
        prompt_path = pf.name
    out_path = str(Path(tempfile.gettempdir()) / "codex-bridge-out.txt")
    try:
        with open(prompt_path, encoding="utf-8") as stdin_fp:
            proc = subprocess.run(
                [CODEX_EXE, "exec", "-s", "read-only", "-m", model,
                 "-o", out_path, "-"],
                stdin=stdin_fp, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=EXEC_TIMEOUT)
    finally:
        Path(prompt_path).unlink(missing_ok=True)
    text = Path(out_path).read_text(encoding="utf-8",
                                    errors="replace").strip() if Path(
        out_path).exists() else ""
    if not text:
        err = (proc.stderr or "")[-500:]
        raise RuntimeError("codex exec produced no text. " + err)
    return text


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CodexBridge/1.0"

    def log_message(self, fmt, *args):
        pass

    def _json(self, status: int, obj) -> None:
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/v1/models", "/v1/models/"):
            self._json(200, {
                "object": "list",
                "data": [{"id": m, "object": "model", "owned_by": "openai"}
                         for m in MODELS]})
            print(f"GET {self.path} -> 200", flush=True)
        elif self.path in ("/", "/health"):
            self._json(200, {"ok": True})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path not in ("/v1/chat/completions",
                             "/v1/chat/completions/"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._json(400, {"error": {"message": "bad json"}})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": {"message": "payload must be a json object"}})
            return
        messages = payload.get("messages")
        if messages is not None and (
                not isinstance(messages, list)
                or any(not isinstance(message, dict) for message in messages)):
            self._json(400, {"error": {"message": "messages must be a list of objects"}})
            return
        model = str(payload.get("model") or MODELS[0])
        if model not in MODELS:
            model = MODELS[0]
        prompt = build_prompt(payload.get("messages"))
        try:
            text = run_codex(model, prompt)
        except Exception as e:
            self._json(502, {"error": {"message": str(e)[:300]}})
            print(f"POST {self.path} -> 502 exec-failed", flush=True)
            return
        self._json(200, {
            "id": "bridge-1",
            "object": "chat.completion",
            "model": model,
            "choices": [{"index": 0,
                         "message": {"role": "assistant",
                                     "content": text},
                         "finish_reason": "stop"}]})
        print(f"POST {self.path} model={model} -> 200", flush=True)


def main() -> None:
    print(f"codex_bridge: codex={CODEX_EXE} port={PORT}", flush=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    print(f"codex_bridge listening on 127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
