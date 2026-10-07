"""Muse Bridge — use your Muse Code subscription in any OpenAI-compatible app.

What it does
------------
Runs a tiny local HTTP server that speaks the OpenAI chat API. Each request is
translated into a `muse exec` call, so the answer comes from your existing
Muse Code subscription (login, not a billed API key). No API key is needed and
no request/response content is ever logged.

Endpoints
---------
  GET  /v1/models            -> list of Muse models
  GET  /health               -> {"ok": true}
  POST /v1/chat/completions  -> OpenAI-style chat (stream and non-stream)

Requirements
------------
- Python 3.9+
- Muse Code CLI installed and logged in (`muse` on PATH, or ~/.local/bin/muse)
  On Windows the CLI is usually `muse.exe` / `muse.cmd`.

Usage
-----
  python muse_bridge.py            # listens on 127.0.0.1:11471

Optional environment variables:
  MUSE_BRIDGE_PORT    port to listen on (default 11471)
  MUSE_BRIDGE_EXE     full path to the muse binary (auto-detected if unset)
  MUSE_BRIDGE_MODELS  comma-separated model list (defaults below)
"""

import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from request_deadline import HeaderDeadlineReader as _HeaderDeadlineReader
from request_origin import (
    is_trusted_local_request as _is_trusted_local_request,
)
import logging

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


PORT = _env_int("MUSE_BRIDGE_PORT", 11471)
EXEC_TIMEOUT = 280
KEEPALIVE_SEC = 15
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


DEFAULT_MODELS = [
    "muse-spark-1.3",
    "muse-spark-1.2",
    "muse-spark-1.1",
    "muse-spark-1.3-contributor",
    "muse-spark-1.2-contributor",
]
MODELS = [m.strip() for m in
          os.environ.get("MUSE_BRIDGE_MODELS", ",".join(DEFAULT_MODELS)).split(",")
          if m.strip()] or list(DEFAULT_MODELS)

# Fallback model when the request names none or an unknown one. Defaults
# to the second entry (spark-1.2) but must exist even for a 1-item list.
DEFAULT_MODEL = MODELS[1] if len(MODELS) > 1 else MODELS[0]

# Flags that keep the nested agent tame in headless mode: no approvals that
# hang, no shell, no file writes, no web tools, bounded steps.
TAME_FLAGS = ["--approval-mode", "never", "--disable-shell",
              "--disable-write", "--disable-web-tools",
              "--max-model-steps", "25",
              "--no-foreign-personal-context", "--no-session-log"]

# Effort spelling from the app -> muse CLI flag. CLI+API accept only
# minimal|low|medium|high|xhigh|max|ultra; the API rejects max/ultra for
# muse-spark, so we cap at xhigh.
EFFORT_MAP = {"off": "minimal", "none": "minimal", "minimal": "minimal",
              "low": "low", "medium": "medium", "high": "high",
              "xhigh": "xhigh", "max": "xhigh", "ultra": "xhigh"}


def find_muse() -> str:
    """Locate the muse CLI on this machine, cross-platform."""
    override = os.environ.get("MUSE_BRIDGE_EXE")
    if override:
        if Path(override).exists():
            return override
        raise FileNotFoundError("MUSE_BRIDGE_EXE points to a missing path")
    exe = shutil.which("muse")
    if exe:
        return exe
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "muse",
        home / ".local" / "bin" / "muse.exe",
        home / "bin" / "muse",
        home / "bin" / "muse.exe",
        home / "bin" / "muse.cmd",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # On Windows the CLI is often muse.exe / muse.cmd.
    if os.name == "nt":
        for name in ("muse.exe", "muse.cmd", "muse"):
            found = shutil.which(name)
            if found:
                return found
    return "muse"


MUSE_EXE = find_muse()


def _muse_command(args):
    """Build the subprocess command, wrapping .cmd/.bat on Windows."""
    if os.name == "nt" and MUSE_EXE.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", MUSE_EXE] + args
    return [MUSE_EXE] + args


def extract_effort(payload) -> str:
    raw = payload.get("reasoning_effort")
    if raw is None:
        reasoning = payload.get("reasoning")
        if isinstance(reasoning, dict):
            raw = reasoning.get("effort", payload.get("effort"))
        elif reasoning is not None:
            raw = reasoning
        else:
            raw = payload.get("effort")
    return EFFORT_MAP.get(str(raw or "high").lower(), "high")


def build_prompt(messages) -> str:
    parts = []
    for m in messages or []:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(p.get("text")) for p in content if isinstance(p, dict)
                and p.get("text") is not None and p.get("text") != "")
        if content is None:
            content = ""
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts) or "(empty)"


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


def run_muse(model: str, prompt: str, effort: str = "high") -> str:
    prompt_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as pf:
            prompt_path = pf.name
            pf.write(prompt)
        proc = subprocess.run(
            _muse_command(["exec", "--json", "--model", model,
                           "--reasoning-effort", effort] + TAME_FLAGS +
                          ["--prompt-file", prompt_path]),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=EXEC_TIMEOUT)
    finally:
        if prompt_path is not None:
            Path(prompt_path).unlink(missing_ok=True)
    text = ""
    failure = ""
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except Exception as _exc:
            logging.getLogger(__name__).debug("suppressed %s", _exc)
            continue
        if ev.get("payload_type") == "run.terminal.completed":
            text = ((ev.get("payload") or {}).get("text") or text) or ""
        elif ev.get("payload_type") == "run.terminal.failed":
            payload = ev.get("payload")
            reason = (payload.get("reason") if isinstance(payload, dict)
                      else None)
            failure = str(reason)[:200] if reason else "unknown reason"
    if failure:
        err = (proc.stderr or "")[-500:]
        raise RuntimeError("muse exec failed: " + failure +
                           (" " + err if err else ""))
    if not text:
        err = (proc.stderr or "")[-500:]
        raise RuntimeError("muse exec produced no text. " + err)
    return text


def stream_muse(model: str, prompt: str, effort: str, on_delta) -> str:
    """Run muse exec and forward incremental text via on_delta(chunk).

    on_delta is also called with None every KEEPALIVE_SEC of silence so the
    HTTP client sees a live stream on long agent runs. Returns the full text.
    """
    prompt_path = None
    # stderr goes to a temp file (not a pipe) so a chatty muse cannot block
    # the child by filling the pipe buffer while we only read stdout.
    err_fp = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                         encoding="utf-8") as pf:
            prompt_path = pf.name
            pf.write(prompt)
        err_fp = tempfile.TemporaryFile("w+", encoding="utf-8",
                                        errors="replace")
        proc = subprocess.Popen(
            _muse_command(["exec", "--json", "--model", model,
                           "--reasoning-effort", effort] + TAME_FLAGS +
                          ["--prompt-file", prompt_path]),
            stdout=subprocess.PIPE, stderr=err_fp,
            text=True, encoding="utf-8", errors="replace",
            bufsize=1)
    except BaseException:
        if prompt_path is not None:
            Path(prompt_path).unlink(missing_ok=True)
        if err_fp is not None:
            err_fp.close()
        raise
    print(f"exec spawned model={model} effort={effort}", flush=True)
    deadline = threading.Timer(EXEC_TIMEOUT, proc.kill)
    deadline.daemon = True
    full = []
    failure = ""
    exit_status = None
    stop = threading.Event()
    watch_started = False

    def watchdog():
        while not stop.wait(KEEPALIVE_SEC):
            try:
                on_delta(None)
            except Exception:
                try:
                    proc.kill()
                except OSError as _exc:
                    logging.getLogger(__name__).debug("suppressed %s", _exc)
                break

    watch = threading.Thread(target=watchdog, daemon=True)
    try:
        deadline.start()
        watch.start()
        watch_started = True
        for line in proc.stdout:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except Exception as _exc:
                logging.getLogger(__name__).debug("suppressed %s", _exc)
                continue
            pt = ev.get("payload_type")
            if pt == "run.output.delta":
                chunk = ((ev.get("payload") or {}).get("text")) or ""
                if chunk:
                    full.append(chunk)
                    on_delta(chunk)
            elif pt == "run.terminal.completed":
                text = ((ev.get("payload") or {}).get("text")) or ""
                joined = "".join(full)
                if text and not joined:
                    full.append(text)
                    on_delta(text)
                elif text and text.startswith(joined) and len(text) > len(joined):
                    tail = text[len(joined):]
                    full.append(tail)
                    on_delta(tail)
                elif text and text != joined:
                    failure = "completed output did not match streamed deltas"
            elif pt == "run.terminal.failed":
                payload = ev.get("payload")
                reason = payload.get("reason") if isinstance(payload, dict) else None
                failure = str(reason)[:200] if reason else "unknown reason"
                print(f"exec terminal-failed: {failure}", flush=True)
    finally:
        # Every exit path — client abort, supervision startup failure, parse
        # errors, terminal failure, deadline kill — lands here: stop the
        # watchdog, cancel a still-running exec instead of waiting
        # EXEC_TIMEOUT for it, reap it, and drop the prompt file.
        stop.set()
        if proc.poll() is None:
            proc.kill()
        if watch_started:
            watch.join()
        Path(prompt_path).unlink(missing_ok=True)
        try:
            exit_status = proc.wait(timeout=10)
        except Exception:
            exit_status = proc.poll()
        deadline.cancel()
        if sys.exc_info()[0] is not None:
            err_fp.close()
    try:
        if failure or exit_status != 0 or not "".join(full):
            try:
                err_fp.seek(0)
                err = err_fp.read()[-500:]
            except Exception:
                err = ""
            if failure:
                raise RuntimeError("muse exec failed: " + failure +
                                   (" " + err if err else ""))
            if exit_status != 0:
                raise RuntimeError("muse exec exited with status " +
                                   str(exit_status) +
                                   (" " + err if err else ""))
            raise RuntimeError("muse exec produced no text. " + err)
        return "".join(full)
    finally:
        err_fp.close()


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "MuseBridge/1.0"
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

    def _sse(self, obj, lock=None) -> None:
        data = ("data: " + json.dumps(obj) + "\n\n").encode()
        if lock is not None:
            with lock:
                self.wfile.write(data)
                self.wfile.flush()
        else:
            self.wfile.write(data)
            self.wfile.flush()

    def _stream_chat(self, model: str, prompt: str, effort: str) -> None:
        # Watchdog thread and main thread both write to the same socket.
        # Concurrent writes on Windows can raise OSError [Errno 22], so one
        # lock per request serializes every socket write.
        wlock = threading.Lock()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        self.close_connection = True

        def chunk(content=None, finish=None):
            delta = {} if content is None else {"content": content}
            self._sse({"id": "bridge-1",
                       "object": "chat.completion.chunk",
                       "created": int(time.time()),
                       "model": model,
                       "choices": [{"index": 0, "delta": delta,
                                    "finish_reason": finish}]}, lock=wlock)
            return content

        def on_delta(piece):
            if piece is None:
                with wlock:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            else:
                chunk(piece)

        try:
            stream_muse(model, prompt, effort, on_delta)
            chunk(None, "stop")
            with wlock:
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            self.close_connection = True
            print(f"POST {self.path} model={model} effort={effort} "
                  f"stream -> 200", flush=True)
        except BrokenPipeError:
            print(f"POST {self.path} model={model} effort={effort} "
                  f"stream client-abort", flush=True)
        except Exception as e:
            try:
                self._sse({"error": {"message": str(e)[:300]}}, lock=wlock)
            except Exception as _exc:
                logging.getLogger(__name__).debug("suppressed %s", _exc)
            print(f"POST {self.path} -> 502 stream-failed", flush=True)

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
                "data": [{"id": m, "object": "model", "owned_by": "meta"}
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
        if length < 0 or length > MAX_BODY_BYTES:
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
                or any(not isinstance(m, dict) for m in messages)):
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
        model = str(payload.get("model") or DEFAULT_MODEL)
        if model not in MODELS:
            model = DEFAULT_MODEL
        prompt = build_prompt(payload.get("messages"))
        try:
            prompt.encode("utf-8")
        except UnicodeEncodeError:
            self._json(400, {
                "error": {"message": "messages must contain valid Unicode text"}})
            return
        effort = extract_effort(payload)
        if payload.get("stream") is True:
            self._stream_chat(model, prompt, effort)
            return
        try:
            text = run_muse(model, prompt, effort)
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
        print(f"POST {self.path} model={model} effort={effort} -> 200",
              flush=True)


def main() -> None:
    print(f"muse_bridge: muse={MUSE_EXE} port={PORT} "
          f"models={len(MODELS)}", flush=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.daemon_threads = True
    print(f"muse_bridge listening on 127.0.0.1:{PORT}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
