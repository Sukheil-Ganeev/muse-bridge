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
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from request_deadline import HeaderDeadlineReader as _HeaderDeadlineReader
from request_origin import (
    is_trusted_local_request as _is_trusted_local_request,
)

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
MAX_BODY_BYTES = 4 * 1024 * 1024
POST_BODY_READ_TIMEOUT = 30
REQUEST_IDLE_TIMEOUT = 30
REQUEST_HEADER_READ_TIMEOUT = 30
MESSAGE_ROLES = {"system", "developer", "user", "assistant", "tool",
                 "function"}


def _no_duplicate_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


MODELS = [
    "gpt-5.1-codex-max",
    "gpt-5.1-codex-mini",
]


def find_codex() -> str:
    override = os.environ.get("CODEX_BRIDGE_EXE")
    if override:
        if Path(override).exists():
            return override
        raise FileNotFoundError("CODEX_BRIDGE_EXE points to a missing path")
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


def _codex_command(args):
    """Build the subprocess command, wrapping .cmd/.bat on Windows."""
    if os.name == "nt" and CODEX_EXE.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", CODEX_EXE] + args
    return [CODEX_EXE] + args


def _parse_content_length(value):
    if value is None:
        return 0
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError("bad content-length")
    return int(value)


def _content_length_header(headers):
    get_all = getattr(headers, "get_all", None)
    values = get_all("Content-Length") if get_all else None
    if values and any(value.strip() != values[0].strip()
                      for value in values[1:]):
        raise ValueError("conflicting content-length")
    return values[0] if values else headers.get("Content-Length")


def _has_json_content_type(headers):
    get_all = getattr(headers, "get_all", None)
    values = get_all("Content-Type") if get_all else None
    if values is not None:
        if len(values) != 1:
            return False
        value = values[0]
    else:
        value = headers.get("Content-Type")
    if not isinstance(value, str):
        return False
    return value.split(";", 1)[0].strip().lower() == "application/json"


def _read_request_body(reader, connection, length):
    if connection is None:
        return reader.read(length)
    previous_timeout = connection.gettimeout()
    deadline = time.monotonic() + POST_BODY_READ_TIMEOUT
    chunks = []
    remaining = length
    read_chunk = getattr(reader, "read1", reader.read)
    try:
        while remaining:
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                raise socket.timeout("request body read timed out")
            connection.settimeout(timeout)
            chunk = read_chunk(min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        connection.settimeout(previous_timeout)


def _reject_before_body(handler, status: int, obj) -> None:
    handler.close_connection = True
    handler._json(status, obj)


def build_prompt(messages) -> str:
    parts = []
    for m in messages or []:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(p.get("text") if p.get("text") is not None else "")
                for p in content if isinstance(p, dict))
        if content is None:
            content = ""
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts) or "(empty)"


def run_codex(model: str, prompt: str) -> str:
    prompt_path = None
    out_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as pf:
            prompt_path = pf.name
            pf.write(prompt)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as out_fp:
            out_path = out_fp.name
        with open(prompt_path, encoding="utf-8") as stdin_fp:
            proc = subprocess.run(
                _codex_command(["exec", "-s", "read-only", "-m", model,
                                "-o", out_path, "-"]),
                stdin=stdin_fp, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=EXEC_TIMEOUT)
        text = Path(out_path).read_text(encoding="utf-8",
                                       errors="replace")
        if not text.strip():
            err = (proc.stderr or "")[-500:]
            raise RuntimeError("codex exec produced no text. " + err)
        return text
    finally:
        if prompt_path is not None:
            Path(prompt_path).unlink(missing_ok=True)
        if out_path is not None:
            Path(out_path).unlink(missing_ok=True)


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CodexBridge/1.0"
    timeout = REQUEST_IDLE_TIMEOUT

    def handle_one_request(self):
        reader = self.rfile
        self.rfile = _HeaderDeadlineReader(
            reader, self.connection, REQUEST_HEADER_READ_TIMEOUT)
        try:
            super().handle_one_request()
        finally:
            self.rfile = reader
            self.connection.settimeout(self.timeout)

    def parse_request(self):
        try:
            return super().parse_request()
        except (socket.timeout, TimeoutError):
            self.close_connection = True
            self.connection.settimeout(self.timeout)
            self.send_error(408, "Request Timeout")
            return False
        finally:
            self.connection.settimeout(self.timeout)

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
        server = getattr(self, "server", None)
        port = server.server_address[1] if server is not None else PORT
        if not _is_trusted_local_request(self.headers, port):
            _reject_before_body(
                self, 403, {"error": {"message": "local requests only"}})
            return
        if self.path in ("/v1/models", "/v1/models/"):
            self._json(200, {
                "object": "list",
                "data": [{"id": m, "object": "model", "owned_by": "openai"}
                         for m in MODELS]})
            print(f"GET {self.path} -> 200", flush=True)
        elif self.path in ("/", "/health"):
            self._json(200, {"ok": True})
        else:
            self.close_connection = True
            self.send_error(404)

    def do_POST(self):
        server = getattr(self, "server", None)
        port = server.server_address[1] if server is not None else PORT
        if not _is_trusted_local_request(self.headers, port):
            _reject_before_body(
                self, 403, {"error": {"message": "local requests only"}})
            return
        if self.path not in ("/v1/chat/completions",
                             "/v1/chat/completions/"):
            self.close_connection = True
            self.send_error(404)
            return
        if self.headers.get("Transfer-Encoding") is not None:
            _reject_before_body(self, 400, {
                "error": {"message": "transfer-encoding is not supported"}})
            return
        try:
            length = _parse_content_length(
                _content_length_header(self.headers))
        except ValueError:
            _reject_before_body(
                self, 400, {"error": {"message": "bad content-length"}})
            return
        if length > MAX_BODY_BYTES:
            _reject_before_body(
                self, 413, {"error": {"message": "payload too large"}})
            return
        if not _has_json_content_type(self.headers):
            _reject_before_body(self, 415, {
                "error": {"message": "content-type must be application/json"}})
            return
        get_all = getattr(self.headers, "get_all", None)
        expect_values = get_all("Expect") if get_all else None
        if expect_values is None:
            expect = self.headers.get("Expect")
            expect_values = [expect] if expect is not None else []
        if expect_values:
            if (len(expect_values) != 1
                    or expect_values[0].strip().lower() != "100-continue"
                    or self.request_version != "HTTP/1.1"):
                _reject_before_body(self, 417, {
                    "error": {"message": "expectation is not supported"}})
                return
            self.wfile.write(b"HTTP/1.1 100 Continue\r\n\r\n")
            self.wfile.flush()
        try:
            body = _read_request_body(
                self.rfile, getattr(self, "connection", None), length)
            if len(body) != length:
                _reject_before_body(self, 400, {
                    "error": {"message": "incomplete request body"}})
                return
            payload = json.loads(
                (body or b"{}").decode("utf-8"),
                object_pairs_hook=_no_duplicate_object)
        except (socket.timeout, TimeoutError):
            _reject_before_body(self, 408, {
                "error": {"message": "request body read timed out"}})
            return
        except Exception:
            self._json(400, {"error": {"message": "bad json"}})
            return
        if not isinstance(payload, dict):
            self._json(400, {"error": {"message": "payload must be a json object"}})
            return
        messages = payload.get("messages")
        if (not isinstance(messages, list)
                or any(not isinstance(message, dict) for message in messages)):
            self._json(400, {"error": {"message": "messages must be a list of objects"}})
            return
        if any("role" in message and (
                not isinstance(message["role"], str)
                or message["role"] not in MESSAGE_ROLES)
               for message in messages):
            self._json(400, {"error": {"message": "message role is not supported"}})
            return
        if any(isinstance(message.get("content"), list)
               and any(not isinstance(part, dict)
                       or part.get("type", "text") != "text"
                       for part in message["content"])
               for message in messages):
            self._json(400, {
                "error": {"message": "only text content parts are supported"}})
            return
        if payload.get("stream") is True:
            self._json(400, {
                "error": {"message": "streaming is not supported"}})
            return
        model = str(payload.get("model") or MODELS[0])
        if model not in MODELS:
            model = MODELS[0]
        prompt = build_prompt(payload.get("messages"))
        try:
            prompt.encode("utf-8")
        except UnicodeEncodeError:
            self._json(400, {
                "error": {"message": "messages must contain valid Unicode text"}})
            return
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
