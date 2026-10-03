"""Contract tests for muse_bridge — offline, no muse CLI needed."""

import importlib
import io
import json
import os
import socket
import sys
import threading
import unittest
import urllib.request
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def fresh_bridge(models_env=None):
    env = {}
    if models_env is not None:
        env["MUSE_BRIDGE_MODELS"] = models_env
    with mock.patch.dict(os.environ, env):
        for name in ("muse_bridge",):
            sys.modules.pop(name, None)
        return importlib.import_module("muse_bridge")


def fresh_codex_bridge():
    sys.modules.pop("codex_bridge", None)
    return importlib.import_module("codex_bridge")


class ExtractEffortTests(unittest.TestCase):
    def setUp(self):
        self.mb = fresh_bridge()

    def test_default_is_high(self):
        self.assertEqual(self.mb.extract_effort({}), "high")

    def test_reasoning_effort_field(self):
        self.assertEqual(
            self.mb.extract_effort({"reasoning_effort": "low"}), "low")

    def test_reasoning_object(self):
        self.assertEqual(
            self.mb.extract_effort({"reasoning": {"effort": "xhigh"}}),
            "xhigh")

    def test_reasoning_string_is_effort(self):
        # Некоторые клиенты шлют "reasoning": "low" — не словарь.
        self.assertEqual(
            self.mb.extract_effort({"reasoning": "low"}), "low")

    def test_max_and_ultra_cap_at_xhigh(self):
        self.assertEqual(
            self.mb.extract_effort({"reasoning_effort": "max"}), "xhigh")
        self.assertEqual(
            self.mb.extract_effort({"reasoning_effort": "ultra"}), "xhigh")

    def test_unknown_falls_back_to_high(self):
        self.assertEqual(
            self.mb.extract_effort({"reasoning_effort": "weird"}), "high")


class BuildPromptTests(unittest.TestCase):
    def setUp(self):
        self.mb = fresh_bridge()

    def test_empty_messages(self):
        self.assertEqual(self.mb.build_prompt([]), "(empty)")
        self.assertEqual(self.mb.build_prompt(None), "(empty)")

    def test_roles_and_order(self):
        out = self.mb.build_prompt([
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "hi"}])
        self.assertEqual(out, "[system]\nrules\n\n[user]\nhi")

    def test_list_content_parts(self):
        out = self.mb.build_prompt([{"role": "user", "content": [
            {"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}])
        self.assertEqual(out, "[user]\na b")

    def test_null_content_is_empty_not_literal_none(self):
        out = self.mb.build_prompt([
            {"role": "assistant", "content": None}])
        self.assertNotIn("None", out)
        self.assertEqual(out, "[assistant]\n")

    def test_null_text_in_parts_is_empty(self):
        out = self.mb.build_prompt([{"role": "user", "content": [
            {"type": "text", "text": None}, {"type": "text", "text": "x"}]}])
        self.assertNotIn("None", out)
        self.assertEqual(out, "[user]\nx")


class ModelListTests(unittest.TestCase):
    def test_single_model_env_parses(self):
        mb = fresh_bridge("only-model")
        self.assertEqual(mb.MODELS, ["only-model"])

    def test_empty_env_falls_back_to_defaults(self):
        mb = fresh_bridge(" , ,")
        self.assertEqual(mb.MODELS, mb.DEFAULT_MODELS)


class CodexBuildPromptTests(unittest.TestCase):
    def setUp(self):
        self.cb = fresh_codex_bridge()

    def test_numeric_text_part_is_coerced_to_string(self):
        prompt = self.cb.build_prompt([{
            "role": "user",
            "content": [{"type": "text", "text": 123}],
        }])
        self.assertEqual(prompt, "[user]\n123")


class CodexPostValidationTests(unittest.TestCase):
    def setUp(self):
        self.cb = fresh_codex_bridge()

    def _post(self, payload):
        body = json.dumps(payload).encode()
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        with mock.patch.object(self.cb, "run_codex", return_value="ok"):
            self.cb.Handler.do_POST(handler)
        return response

    def test_non_object_payload_returns_400(self):
        self.assertEqual(self._post(["a", "b"])["status"], 400)

    def test_non_list_messages_returns_400(self):
        self.assertEqual(self._post({"messages": "hello"})["status"], 400)

    def test_non_object_message_item_returns_400(self):
        self.assertEqual(self._post({"messages": [42]})["status"], 400)


class CodexOutputIsolationTests(unittest.TestCase):
    def setUp(self):
        self.cb = fresh_codex_bridge()

    def test_concurrent_calls_use_and_remove_distinct_output_files(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with self.cb.tempfile.TemporaryDirectory(dir=repo) as temp_dir:
            started = threading.Barrier(2)
            written = threading.Barrier(2)
            results = {}
            failures = []

            def fake_run(args, **_kwargs):
                output_path = args[args.index("-o") + 1]
                answer = threading.current_thread().name
                started.wait(timeout=5)
                with open(output_path, "w", encoding="utf-8") as output:
                    output.write(answer)
                written.wait(timeout=5)
                return mock.Mock(stderr="")

            def invoke(answer):
                try:
                    results[answer] = self.cb.run_codex("m", "p")
                except BaseException as exc:
                    failures.append(exc)

            with mock.patch.object(self.cb.tempfile, "gettempdir",
                                   return_value=temp_dir), \
                 mock.patch.object(self.cb.subprocess, "run",
                                   side_effect=fake_run):
                threads = [threading.Thread(target=invoke, args=(answer,),
                                            name=answer)
                           for answer in ("answer-A", "answer-B")]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=10)

            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(failures, [])
            self.assertEqual(results, {"answer-A": "answer-A",
                                       "answer-B": "answer-B"})
            self.assertEqual(os.listdir(temp_dir), [])


class TerminalFailureTests(unittest.TestCase):
    def setUp(self):
        self.mb = fresh_bridge()

    def test_terminal_failure_reason_is_reported(self):
        event = json.dumps({"payload_type": "run.terminal.failed",
                            "payload": {"reason": "quota exceeded"}})
        proc = mock.Mock(stdout=event + "\n", stderr="")
        with mock.patch.object(self.mb.subprocess, "run", return_value=proc):
            with self.assertRaisesRegex(RuntimeError, "quota exceeded"):
                self.mb.run_muse("m", "p")


class ContentLengthParsingTests(unittest.TestCase):
    def setUp(self):
        self.mb = fresh_bridge()

    def _post_with_length(self, length):
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {} if length is None else {"Content-Length": length}
        handler.rfile = io.BytesIO(b"{}")
        handler._json = lambda status, body: response.update(
            status=status, body=body)
        with mock.patch.object(self.mb, "run_muse", return_value="ok"):
            self.mb.Handler.do_POST(handler)
        return response

    def test_missing_header_means_empty_body(self):
        self.assertEqual(self._post_with_length(None)["status"], 200)

    def test_ascii_decimal_length_is_accepted(self):
        self.assertEqual(self._post_with_length("2")["status"], 200)

    def test_non_decimal_forms_are_rejected(self):
        for value in ("1_0", "+10", "", "١٠"):
            with self.subTest(value=value):
                self.assertEqual(self._post_with_length(value)["status"], 400)


class PostHandlerTests(unittest.TestCase):
    """HTTP-level: POST must never crash on model selection."""

    def _serve(self, models_env=None):
        mb = fresh_bridge(models_env)
        srv = mb.http.server.ThreadingHTTPServer(("127.0.0.1", 0), mb.Handler)
        port = srv.server_address[1]
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        self.addCleanup(srv.shutdown)
        return mb, port

    def _post(self, port, payload):
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_post_single_model_list_no_indexerror(self):
        mb, port = self._serve("solo-model")
        with mock.patch.object(mb, "run_muse", return_value="ok-text"):
            status, body = self._post(port, {
                "model": "solo-model",
                "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(status, 200)
        self.assertEqual(body["choices"][0]["message"]["content"], "ok-text")

    def test_unknown_model_falls_back_not_crash(self):
        mb, port = self._serve("solo-model")
        seen = {}
        def fake_run(model, prompt, effort="high"):
            seen["model"] = model
            return "ok"
        with mock.patch.object(mb, "run_muse", side_effect=fake_run):
            status, _ = self._post(port, {
                "model": "nonexistent",
                "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(status, 200)
        self.assertEqual(seen["model"], "solo-model")

    def test_non_object_payload_returns_400(self):
        mb, port = self._serve()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=b'["a","b"]', headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_non_list_messages_returns_400(self):
        mb, port = self._serve()
        status, _ = self._post(port, {
            "model": "muse-spark-1.3", "messages": "hello"})
        self.assertEqual(status, 400)

    def test_non_object_message_item_returns_400(self):
        mb, port = self._serve()
        status, _ = self._post(port, {
            "model": "muse-spark-1.3", "messages": [42, {"role": "user", "content": "hi"}]})
        self.assertEqual(status, 400)

    def test_non_string_text_part_coerced_not_dropped(self):
        mb, port = self._serve()
        with mock.patch.object(mb, "run_muse", return_value="ok") as run:
            status, _ = self._post(port, {
                "model": "muse-spark-1.3",
                "messages": [{"role": "user",
                              "content": [{"type": "text", "text": 123}]}]})
        self.assertEqual(status, 200)
        self.assertIn("123", run.call_args[0][1])

    def test_non_string_content_coerced_not_dropped(self):
        mb, port = self._serve()
        with mock.patch.object(mb, "run_muse", return_value="ok") as run:
            status, _ = self._post(port, {
                "model": "muse-spark-1.3",
                "messages": [{"role": "user", "content": 7}]})
        self.assertEqual(status, 200)
        self.assertIn("7", run.call_args[0][1])

    def test_exec_failure_returns_502_json(self):
        mb, port = self._serve()
        with mock.patch.object(mb, "run_muse",
                               side_effect=RuntimeError("boom")):
            status, body = self._post(port, {
                "model": "muse-spark-1.3",
                "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(status, 502)
        self.assertIn("boom", body["error"]["message"])

    def test_stream_string_false_is_not_streaming(self):
        # stream="false" (строка) — не булево true, ответ должен быть JSON, не SSE.
        mb, port = self._serve()
        seen = {"streamed": False}
        def fake_stream(self, model, prompt, effort):
            seen["streamed"] = True
        with mock.patch.object(mb.Handler, "_stream_chat", fake_stream), \
             mock.patch.object(mb, "run_muse", return_value="ok"):
            status, body = self._post(port, {
                "model": "muse-spark-1.3", "stream": "false",
                "messages": [{"role": "user", "content": "hi"}]})
        self.assertFalse(seen["streamed"])
        self.assertEqual(status, 200)
        self.assertEqual(body["choices"][0]["message"]["content"], "ok")

    def test_bad_json_returns_400(self):
        mb, port = self._serve()
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            data=b"{not json", headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10)
            self.fail("expected HTTPError")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def _raw_post(self, port, headers: bytes):
        with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
            s.sendall(b"POST /v1/chat/completions HTTP/1.1\r\n"
                      b"Host: 127.0.0.1\r\n" + headers + b"\r\n")
            chunks = []
            while True:
                try:
                    data = s.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                chunks.append(data)
        return b"".join(chunks)

    def test_bad_content_length_returns_400_not_hang(self):
        mb, port = self._serve()
        resp = self._raw_post(port, b"Content-Length: abc\r\n\r\n")
        self.assertTrue(resp.startswith(b"HTTP/1.0 400") or
                        resp.startswith(b"HTTP/1.1 400"), resp[:80])

    def test_oversized_content_length_returns_413(self):
        mb, port = self._serve()
        resp = self._raw_post(port, b"Content-Length: 99999999\r\n\r\n")
        self.assertIn(b" 413 ", resp.split(b"\r\n")[0])


class _FakeStdout:
    def __init__(self, lines):
        self._lines = iter(lines)
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return next(self._lines)
        except StopIteration:
            self.closed = True
            raise


class _FakeProc:
    """Stand-in for subprocess.Popen: stdout closes when drained."""

    def __init__(self, events):
        self.stdout = _FakeStdout(events)
        self.killed = False
        self.wait_calls = []

    def poll(self):
        return 0 if (self.killed or self.stdout.closed) else None

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        return 0


def _delta(text):
    return json.dumps({"payload_type": "run.output.delta",
                       "payload": {"text": text}})


class StreamAbortTests(unittest.TestCase):
    """stream_muse: cancel exec + remove temp prompt file on every exit."""

    def setUp(self):
        self.mb = fresh_bridge()

    def _patched(self, proc):
        recorded = {}
        real_ntf = self.mb.tempfile.NamedTemporaryFile

        def spy(*a, **kw):
            f = real_ntf(*a, **kw)
            recorded["path"] = f.name
            return f

        patches = [
            mock.patch.object(self.mb.subprocess, "Popen",
                              return_value=proc),
            mock.patch.object(self.mb.tempfile, "NamedTemporaryFile",
                              side_effect=spy),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return recorded

    def test_client_abort_kills_exec_and_removes_prompt_file(self):
        proc = _FakeProc([_delta("he"), _delta("llo")])
        recorded = self._patched(proc)

        def boom(_piece):
            raise BrokenPipeError("client gone")

        with self.assertRaises(BrokenPipeError):
            self.mb.stream_muse("m", "p", "high", boom)
        self.assertTrue(proc.killed)
        self.assertTrue(proc.wait_calls)
        self.assertFalse(os.path.exists(recorded["path"]))

    def test_clean_stream_returns_text_without_kill(self):
        proc = _FakeProc([_delta("he"), _delta("llo")])
        recorded = self._patched(proc)
        got = []
        out = self.mb.stream_muse("m", "p", "high", got.append)
        self.assertEqual(out, "hello")
        self.assertEqual(got, ["he", "llo"])
        self.assertFalse(proc.killed)
        self.assertFalse(os.path.exists(recorded["path"]))

    def test_terminal_failure_reason_is_reported(self):
        event = json.dumps({"payload_type": "run.terminal.failed",
                            "payload": {"reason": "quota exceeded"}})
        proc = _FakeProc([event])
        recorded = self._patched(proc)
        with self.assertRaisesRegex(RuntimeError, "quota exceeded"):
            self.mb.stream_muse("m", "p", "high", lambda _: None)
        self.assertFalse(os.path.exists(recorded["path"]))

    def test_spawn_failure_closes_stderr_and_removes_prompt_file(self):
        recorded = {}
        real_ntf = self.mb.tempfile.NamedTemporaryFile
        real_tf = self.mb.tempfile.TemporaryFile

        def spy_named_temp(*args, **kwargs):
            f = real_ntf(*args, **kwargs)
            recorded["path"] = f.name
            return f

        def spy_temp(*args, **kwargs):
            f = real_tf(*args, **kwargs)
            recorded["err_fp"] = f
            return f

        with mock.patch.object(self.mb.tempfile, "NamedTemporaryFile",
                               side_effect=spy_named_temp), \
             mock.patch.object(self.mb.tempfile, "TemporaryFile",
                               side_effect=spy_temp), \
             mock.patch.object(self.mb.subprocess, "Popen",
                               side_effect=OSError("cannot spawn")):
            with self.assertRaisesRegex(OSError, "cannot spawn"):
                self.mb.stream_muse("m", "p", "high", lambda _: None)

        self.assertFalse(os.path.exists(recorded["path"]))
        self.assertTrue(recorded["err_fp"].closed)


class HealthTests(unittest.TestCase):
    def test_health_and_models(self):
        mb = fresh_bridge("a,b")
        srv = mb.http.server.ThreadingHTTPServer(("127.0.0.1", 0), mb.Handler)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/health", timeout=10) as r:
            self.assertEqual(json.loads(r.read())["ok"], True)
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/v1/models", timeout=10) as r:
            ids = [m["id"] for m in json.loads(r.read())["data"]]
        self.assertEqual(ids, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
