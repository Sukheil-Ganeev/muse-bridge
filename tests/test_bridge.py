"""Contract tests for muse_bridge — offline, no muse CLI needed."""

from email.message import Message
import importlib
import io
import json
import os
import socket
import sys
import tempfile
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

    def test_falsey_non_string_text_parts_are_preserved(self):
        out = self.mb.build_prompt([{"role": "user", "content": [
            {"type": "text", "text": 0},
            {"type": "text", "text": False}]}])
        self.assertEqual(out, "[user]\n0 False")


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

    def test_null_content_is_empty_not_literal_none(self):
        prompt = self.cb.build_prompt([
            {"role": "assistant", "content": None}])
        self.assertNotIn("None", prompt)
        self.assertEqual(prompt, "[assistant]\n")


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

    def test_missing_messages_returns_400(self):
        self.assertEqual(self._post({})["status"], 400)

    def test_null_messages_returns_400(self):
        self.assertEqual(self._post({"messages": None})["status"], 400)

    def test_duplicate_keys_returns_400(self):
        body = b'{"model": "a", "model": "b", "messages": []}'
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        self.cb.Handler.do_POST(handler)
        self.assertEqual(response["status"], 400)


class CodexContentLengthTests(unittest.TestCase):
    def setUp(self):
        self.cb = fresh_codex_bridge()

    def _post_with_length(self, body, length_header):
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": length_header}
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        with mock.patch.object(self.cb, "run_codex", return_value="ok"):
            self.cb.Handler.do_POST(handler)
        return response

    def test_garbage_content_length_returns_400(self):
        resp = self._post_with_length(b"{}", "not-a-number")
        self.assertEqual(resp["status"], 400)

    def test_oversized_content_length_returns_413(self):
        resp = self._post_with_length(
            b"{}", str(self.cb.MAX_BODY_BYTES + 1))
        self.assertEqual(resp["status"], 413)


class RequestHeaderTimeoutTests(unittest.TestCase):
    class FakeSocket:
        def __init__(self):
            self.timeouts = []

        def settimeout(self, value):
            self.timeouts.append(value)

        def makefile(self, _mode, _buffering=None):
            return io.BytesIO()

    def _assert_handler_setup_sets_idle_timeout(self, module):
        connection = self.FakeSocket()
        handler = module.Handler.__new__(module.Handler)
        handler.request = connection
        handler.client_address = ("127.0.0.1", 0)
        handler.server = None
        handler.setup()
        self.assertEqual(connection.timeouts, [30])

    def test_muse_limits_idle_request_line_and_header_reads(self):
        self._assert_handler_setup_sets_idle_timeout(fresh_bridge())

    def test_codex_limits_idle_request_line_and_header_reads(self):
        self._assert_handler_setup_sets_idle_timeout(fresh_codex_bridge())


class AbsoluteRequestHeaderDeadlineTests(unittest.TestCase):
    class FakeClock:
        def __init__(self):
            self.now = 0.0

        def monotonic(self):
            return self.now

    class FakeSocket:
        def __init__(self):
            self.timeout = None
            self.timeouts = []

        def settimeout(self, value):
            self.timeout = value
            self.timeouts.append(value)

    class SlowReader:
        def __init__(self, clock, connection):
            self.clock = clock
            self.connection = connection
            self.read_count = 0

        def read(self, _size):
            delay = 0.4
            self.read_count += 1
            if delay > self.connection.timeout:
                self.clock.now += self.connection.timeout
                raise socket.timeout("deadline")
            self.clock.now += delay
            return b"x"

    def _assert_absolute_deadline(self, module):
        clock = self.FakeClock()
        connection = self.FakeSocket()
        reader = self.SlowReader(clock, connection)
        with mock.patch.object(module.time, "monotonic",
                               side_effect=clock.monotonic):
            guarded = module._HeaderDeadlineReader(
                reader, connection, timeout=1.0)
            with self.assertRaises(socket.timeout):
                guarded.readline()
        self.assertEqual(reader.read_count, 3)
        self.assertAlmostEqual(clock.now, 1.0)
        self.assertEqual(len(connection.timeouts), 3)
        self.assertAlmostEqual(connection.timeouts[-1], 0.2)

    def test_muse_header_reader_uses_one_absolute_deadline(self):
        self._assert_absolute_deadline(fresh_bridge())

    def test_codex_header_reader_uses_one_absolute_deadline(self):
        self._assert_absolute_deadline(fresh_codex_bridge())

    def _assert_handler_wraps_header_reads(self, module):
        connection = self.FakeSocket()
        original = io.BytesIO(b"GET /health HTTP/1.1\r\n")
        handler = module.Handler.__new__(module.Handler)
        handler.rfile = original
        handler.connection = connection

        def observe_reader(instance):
            instance.observed_reader = instance.rfile

        with mock.patch.object(module.http.server.BaseHTTPRequestHandler,
                               "handle_one_request", observe_reader):
            module.Handler.handle_one_request(handler)

        self.assertIsInstance(handler.observed_reader,
                              module._HeaderDeadlineReader)
        self.assertIs(handler.rfile, original)
        self.assertEqual(connection.timeouts[-1], module.REQUEST_IDLE_TIMEOUT)

    def test_muse_handler_applies_deadline_to_each_request(self):
        self._assert_handler_wraps_header_reads(fresh_bridge())

    def test_codex_handler_applies_deadline_to_each_request(self):
        self._assert_handler_wraps_header_reads(fresh_codex_bridge())

    def _assert_handler_parses_request(self, module):
        connection = self.FakeSocket()
        handler = module.Handler.__new__(module.Handler)
        handler.rfile = io.BytesIO(
            b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n")
        handler.wfile = io.BytesIO()
        handler.connection = connection
        handler.client_address = ("127.0.0.1", 12345)
        handler.close_connection = True

        module.Handler.handle_one_request(handler)

        self.assertEqual(handler.path, "/health")
        self.assertIn(b" 200 OK\r\n", handler.wfile.getvalue())
        self.assertEqual(connection.timeouts[-1], module.REQUEST_IDLE_TIMEOUT)

    def test_muse_handler_parses_request_with_wrapped_reader(self):
        self._assert_handler_parses_request(fresh_bridge())

    def test_codex_handler_parses_request_with_wrapped_reader(self):
        self._assert_handler_parses_request(fresh_codex_bridge())

    def _assert_parse_restores_idle_timeout(self, module, raises_timeout):
        connection = self.FakeSocket()
        handler = module.Handler.__new__(module.Handler)
        handler.connection = connection
        handler.close_connection = False
        errors = []
        handler.send_error = lambda *args: errors.append(args)
        base_handler = module.http.server.BaseHTTPRequestHandler
        side_effect = (socket.timeout("deadline") if raises_timeout else None)
        with mock.patch.object(base_handler, "parse_request",
                               side_effect=side_effect,
                               return_value=True):
            result = module.Handler.parse_request(handler)
        self.assertEqual(connection.timeouts[-1], module.REQUEST_IDLE_TIMEOUT)
        if raises_timeout:
            self.assertFalse(result)
            self.assertTrue(handler.close_connection)
            self.assertEqual(errors[0][0], 408)
        else:
            self.assertTrue(result)

    def test_muse_parse_restores_idle_timeout_after_headers(self):
        self._assert_parse_restores_idle_timeout(fresh_bridge(), False)

    def test_codex_parse_restores_idle_timeout_after_headers(self):
        self._assert_parse_restores_idle_timeout(fresh_codex_bridge(), False)

    def test_muse_header_timeout_returns_408_and_closes(self):
        self._assert_parse_restores_idle_timeout(fresh_bridge(), True)

    def test_codex_header_timeout_returns_408_and_closes(self):
        self._assert_parse_restores_idle_timeout(fresh_codex_bridge(), True)


class PostBodyDeadlineTests(unittest.TestCase):
    class FakeConnection:
        def __init__(self, timeout=7):
            self.original_timeout = timeout
            self.timeouts = []

        def gettimeout(self):
            return self.original_timeout

        def settimeout(self, value):
            self.timeouts.append(value)

    def _assert_partial_body_times_out(self, module):
        response = {}

        class SlowBody:
            def read(self, _length):
                raise TimeoutError("body read deadline")

        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": "10"}
        handler.rfile = SlowBody()
        handler.connection = self.FakeConnection(timeout=None)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        with mock.patch.object(module, "POST_BODY_READ_TIMEOUT", 0.05,
                                create=True):
            module.Handler.do_POST(handler)

        self.assertEqual(response["status"], 408)
        self.assertTrue(handler.connection.timeouts)
        self.assertIsNone(handler.connection.timeouts[-1])

    def _assert_complete_body_is_read(self, module):
        body = b'{"messages": []}'
        connection = self.FakeConnection()
        with mock.patch.object(module, "POST_BODY_READ_TIMEOUT", 0.05,
                                create=True):
            actual = module._read_request_body(
                io.BytesIO(body), connection, len(body))
        self.assertEqual(actual, body)
        self.assertEqual(connection.timeouts[-1], 7)
        self.assertGreater(connection.timeouts[0], 0)
        self.assertLessEqual(connection.timeouts[0], 0.05)

    def _assert_deadline_is_total_not_per_chunk(self, module):
        class OneByteReader:
            def __init__(self):
                self.calls = 0

            def read1(self, _length):
                self.calls += 1
                return b"x"

            def read(self, _length):
                return self.read1(_length)

        reader = OneByteReader()
        connection = self.FakeConnection(timeout=None)
        with mock.patch.object(module, "POST_BODY_READ_TIMEOUT", 0.05,
                                create=True), \
             mock.patch.object(module.time, "monotonic",
                               side_effect=[10.0, 10.02, 10.06]):
            with self.assertRaises(TimeoutError):
                module._read_request_body(reader, connection, 2)
        self.assertEqual(reader.calls, 1)
        self.assertIsNone(connection.timeouts[-1])

    def test_muse_rejects_a_body_that_exceeds_its_read_deadline(self):
        self._assert_partial_body_times_out(fresh_bridge())

    def test_codex_rejects_a_body_that_exceeds_its_read_deadline(self):
        self._assert_partial_body_times_out(fresh_codex_bridge())

    def test_muse_reads_complete_body_and_restores_timeout(self):
        self._assert_complete_body_is_read(fresh_bridge())

    def test_codex_reads_complete_body_and_restores_timeout(self):
        self._assert_complete_body_is_read(fresh_codex_bridge())

    def test_muse_uses_one_deadline_for_all_body_chunks(self):
        self._assert_deadline_is_total_not_per_chunk(fresh_bridge())

    def test_codex_uses_one_deadline_for_all_body_chunks(self):
        self._assert_deadline_is_total_not_per_chunk(fresh_codex_bridge())


class MusePostValidationTests(unittest.TestCase):
    def setUp(self):
        self.mb = fresh_bridge()

    def _post(self, payload):
        body = json.dumps(payload).encode()
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        with mock.patch.object(self.mb, "run_muse", return_value="ok"):
            self.mb.Handler.do_POST(handler)
        return response

    def test_missing_messages_returns_400(self):
        self.assertEqual(self._post({})["status"], 400)

    def test_null_messages_returns_400(self):
        self.assertEqual(self._post({"messages": None})["status"], 400)

    def test_duplicate_keys_returns_400(self):
        body = b'{"messages": [], "stream": true, "stream": false}'
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        self.mb.Handler.do_POST(handler)
        self.assertEqual(response["status"], 400)


class TruncatedBodyTests(unittest.TestCase):
    def _post_with_short_body(self, bridge, runner_name):
        body = b'{"messages":[]}'
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {"Content-Length": str(len(body) + 1)}
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        with mock.patch.object(bridge, runner_name, return_value="ok") as run:
            bridge.Handler.do_POST(handler)
        return response, run

    def test_muse_rejects_short_body_without_running_cli(self):
        bridge = fresh_bridge()
        response, run = self._post_with_short_body(bridge, "run_muse")
        self.assertEqual(response["status"], 400)
        run.assert_not_called()

    def test_codex_rejects_short_body_without_running_cli(self):
        bridge = fresh_codex_bridge()
        response, run = self._post_with_short_body(bridge, "run_codex")
        self.assertEqual(response["status"], 400)
        run.assert_not_called()


class DuplicateContentLengthTests(unittest.TestCase):
    def _post_with_conflicting_lengths(self, bridge, runner_name):
        body = b'{"messages":[]}'
        headers = Message()
        headers.add_header("Content-Length", str(len(body)))
        headers.add_header("Content-Length", str(len(body) + 1))
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = headers
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        with mock.patch.object(bridge, runner_name, return_value="ok") as run:
            bridge.Handler.do_POST(handler)
        return response, run

    def test_muse_rejects_conflicting_lengths_without_running_cli(self):
        bridge = fresh_bridge()
        response, run = self._post_with_conflicting_lengths(
            bridge, "run_muse")
        self.assertEqual(response["status"], 400)
        run.assert_not_called()

    def test_codex_rejects_conflicting_lengths_without_running_cli(self):
        bridge = fresh_codex_bridge()
        response, run = self._post_with_conflicting_lengths(
            bridge, "run_codex")
        self.assertEqual(response["status"], 400)
        run.assert_not_called()


class TransferEncodingTests(unittest.TestCase):
    def _post_with_transfer_encoding(self, bridge, runner_name):
        body = b'{"messages":[]}'
        headers = Message()
        headers.add_header("Content-Length", str(len(body)))
        headers.add_header("Transfer-Encoding", "chunked")
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = headers
        handler.rfile = io.BytesIO(body)
        handler._json = lambda status, obj: response.update(
            status=status, body=obj)
        with mock.patch.object(bridge, runner_name, return_value="ok") as run:
            bridge.Handler.do_POST(handler)
        return response, run

    def test_muse_rejects_transfer_encoding_without_running_cli(self):
        bridge = fresh_bridge()
        response, run = self._post_with_transfer_encoding(bridge, "run_muse")
        self.assertEqual(response["status"], 400)
        run.assert_not_called()

    def test_codex_rejects_transfer_encoding_without_running_cli(self):
        bridge = fresh_codex_bridge()
        response, run = self._post_with_transfer_encoding(bridge, "run_codex")
        self.assertEqual(response["status"], 400)
        run.assert_not_called()


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

    def test_terminal_failure_after_completed_text_is_reported(self):
        completed = json.dumps({"payload_type": "run.terminal.completed",
                                "payload": {"text": "partial answer"}})
        failed = json.dumps({"payload_type": "run.terminal.failed",
                             "payload": {"reason": "quota exceeded"}})
        proc = mock.Mock(stdout=completed + "\n" + failed + "\n", stderr="")
        with mock.patch.object(self.mb.subprocess, "run", return_value=proc):
            with self.assertRaisesRegex(RuntimeError, "quota exceeded"):
                self.mb.run_muse("m", "p")

    def test_terminal_failure_without_reason_after_completed_text_is_reported(
            self):
        completed = json.dumps({"payload_type": "run.terminal.completed",
                                "payload": {"text": "partial answer"}})
        failed = json.dumps({"payload_type": "run.terminal.failed",
                             "payload": {}})
        proc = mock.Mock(stdout=completed + "\n" + failed + "\n", stderr="")
        with mock.patch.object(self.mb.subprocess, "run", return_value=proc):
            with self.assertRaisesRegex(RuntimeError, "muse exec failed"):
                self.mb.run_muse("m", "p")


class PromptTempCreationFailureTests(unittest.TestCase):
    def test_muse_removes_temp_file_when_prompt_write_fails(self):
        mb = fresh_bridge()
        with tempfile.TemporaryDirectory(dir=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))) as temp_dir:
            with mock.patch.object(mb.tempfile, "gettempdir",
                                   return_value=temp_dir), \
                 mock.patch.object(mb.subprocess, "run") as run:
                with self.assertRaises(UnicodeEncodeError):
                    mb.run_muse("m", "prefix\ud800")
            run.assert_not_called()
            self.assertEqual(os.listdir(temp_dir), [])

    def test_stream_muse_removes_temp_file_when_prompt_write_fails(self):
        mb = fresh_bridge()
        with tempfile.TemporaryDirectory(dir=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))) as temp_dir:
            with mock.patch.object(mb.tempfile, "gettempdir",
                                   return_value=temp_dir), \
                 mock.patch.object(mb.subprocess, "Popen") as popen:
                with self.assertRaises(UnicodeEncodeError):
                    mb.stream_muse("m", "prefix\ud800", "high", lambda _: None)
            popen.assert_not_called()
            self.assertEqual(os.listdir(temp_dir), [])

    def test_codex_removes_temp_file_when_prompt_write_fails(self):
        cb = fresh_codex_bridge()
        with tempfile.TemporaryDirectory(dir=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))) as temp_dir:
            with mock.patch.object(cb.tempfile, "gettempdir",
                                   return_value=temp_dir), \
                 mock.patch.object(cb.subprocess, "run") as run:
                with self.assertRaises(UnicodeEncodeError):
                    cb.run_codex("m", "prefix\ud800")
            run.assert_not_called()
            self.assertEqual(os.listdir(temp_dir), [])


class ContentLengthParsingTests(unittest.TestCase):
    def setUp(self):
        self.mb = fresh_bridge()

    def _post_with_length(self, length):
        response = {}
        handler = type("HandlerStub", (), {})()
        handler.path = "/v1/chat/completions"
        handler.headers = {} if length is None else {"Content-Length": length}
        handler.rfile = io.BytesIO(b'{"messages":[]}')
        handler._json = lambda status, body: response.update(
            status=status, body=body)
        with mock.patch.object(self.mb, "run_muse", return_value="ok"):
            self.mb.Handler.do_POST(handler)
        return response

    def test_missing_header_means_empty_body_and_returns_400(self):
        self.assertEqual(self._post_with_length(None)["status"], 400)

    def test_ascii_decimal_length_is_accepted(self):
        self.assertEqual(
            self._post_with_length(str(len(b'{"messages":[]}')))["status"],
            200)

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

    def __init__(self, events, returncode=0):
        self.stdout = _FakeStdout(events)
        self.killed = False
        self.wait_calls = []
        self.returncode = returncode

    def poll(self):
        return self.returncode if (self.killed or self.stdout.closed) else None

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.wait_calls.append(timeout)
        return self.returncode


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

    def test_client_abort_closes_stderr_temp_file(self):
        proc = _FakeProc([_delta("he")])
        recorded = {}
        real_tempfile = self.mb.tempfile.TemporaryFile

        def spy_tempfile(*args, **kwargs):
            fp = real_tempfile(*args, **kwargs)
            recorded["stderr"] = fp
            return fp

        with tempfile.TemporaryDirectory(dir=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))) as temp_dir:
            with mock.patch.object(self.mb.tempfile, "gettempdir",
                                   return_value=temp_dir), \
                 mock.patch.object(self.mb.tempfile, "TemporaryFile",
                                   side_effect=spy_tempfile), \
                 mock.patch.object(self.mb.subprocess, "Popen",
                                   return_value=proc):
                def abort(_piece):
                    raise BrokenPipeError("client gone")

                with self.assertRaises(BrokenPipeError):
                    self.mb.stream_muse("m", "p", "high", abort)

        self.assertTrue(recorded["stderr"].closed)

    def test_timer_start_failure_kills_exec_and_cleans_temp_files(self):
        proc = _FakeProc([])
        recorded = self._patched(proc)
        recorded_stderr = {}
        real_tempfile = self.mb.tempfile.TemporaryFile

        def spy_tempfile(*args, **kwargs):
            fp = real_tempfile(*args, **kwargs)
            recorded_stderr["fp"] = fp
            return fp

        with tempfile.TemporaryDirectory(dir=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))) as temp_dir:
            with mock.patch.object(self.mb.tempfile, "gettempdir",
                                   return_value=temp_dir), \
                 mock.patch.object(self.mb.tempfile, "TemporaryFile",
                                   side_effect=spy_tempfile), \
                 mock.patch.object(self.mb.threading.Timer, "start",
                                   side_effect=RuntimeError("no timer thread")):
                with self.assertRaisesRegex(RuntimeError, "no timer thread"):
                    self.mb.stream_muse("m", "p", "high", lambda _: None)

        self.assertTrue(proc.killed)
        self.assertTrue(proc.wait_calls)
        self.assertFalse(os.path.exists(recorded["path"]))
        self.assertTrue(recorded_stderr["fp"].closed)

    def test_keepalive_start_failure_kills_exec_and_cleans_temp_files(self):
        proc = _FakeProc([])
        recorded = self._patched(proc)
        recorded_stderr = {}
        timers = []
        real_tempfile = self.mb.tempfile.TemporaryFile

        class TimerStub:
            def __init__(self):
                self.cancelled = False

            def start(self):
                pass

            def cancel(self):
                self.cancelled = True

        def fake_timer(*_args, **_kwargs):
            timer = TimerStub()
            timers.append(timer)
            return timer

        def spy_tempfile(*args, **kwargs):
            fp = real_tempfile(*args, **kwargs)
            recorded_stderr["fp"] = fp
            return fp

        watch = mock.Mock()
        watch.start.side_effect = RuntimeError("no keepalive thread")
        with tempfile.TemporaryDirectory(dir=os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))) as temp_dir:
            with mock.patch.object(self.mb.tempfile, "gettempdir",
                                   return_value=temp_dir), \
                 mock.patch.object(self.mb.tempfile, "TemporaryFile",
                                   side_effect=spy_tempfile), \
                 mock.patch.object(self.mb.threading, "Timer",
                                   side_effect=fake_timer), \
                 mock.patch.object(self.mb.threading, "Thread",
                                   return_value=watch):
                with self.assertRaisesRegex(RuntimeError,
                                            "no keepalive thread"):
                    self.mb.stream_muse("m", "p", "high", lambda _: None)

        self.assertTrue(proc.killed)
        self.assertTrue(proc.wait_calls)
        self.assertTrue(timers[0].cancelled)
        self.assertFalse(os.path.exists(recorded["path"]))
        self.assertTrue(recorded_stderr["fp"].closed)

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

    def test_terminal_failure_after_partial_output_is_reported(self):
        event = json.dumps({"payload_type": "run.terminal.failed",
                            "payload": {"reason": "quota exceeded"}})
        proc = _FakeProc([_delta("partial"), event])
        recorded = self._patched(proc)
        with self.assertRaisesRegex(RuntimeError, "quota exceeded"):
            self.mb.stream_muse("m", "p", "high", lambda _: None)
        self.assertFalse(os.path.exists(recorded["path"]))

    def test_terminal_failure_without_reason_after_partial_output_is_reported(self):
        event = json.dumps({"payload_type": "run.terminal.failed",
                            "payload": {}})
        proc = _FakeProc([_delta("partial"), event])
        recorded = self._patched(proc)
        with self.assertRaisesRegex(RuntimeError, "unknown reason"):
            self.mb.stream_muse("m", "p", "high", lambda _: None)
        self.assertFalse(os.path.exists(recorded["path"]))

    def test_nonzero_process_exit_after_partial_output_is_reported(self):
        proc = _FakeProc([_delta("partial")], returncode=17)
        recorded = self._patched(proc)
        with self.assertRaisesRegex(RuntimeError, "exited with status 17"):
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


class StreamKeepaliveAbortTests(unittest.TestCase):
    def setUp(self):
        self.mb = fresh_bridge()

    def test_keepalive_write_failure_kills_cli_while_stdout_waits(self):
        stdout_waiting = threading.Event()
        release_stdout = threading.Event()
        killed = threading.Event()

        class BlockingStdout:
            def __iter__(self):
                return self

            def __next__(self):
                stdout_waiting.set()
                release_stdout.wait(timeout=2)
                raise StopIteration

        class FakeProc:
            stdout = BlockingStdout()

            def poll(self):
                return -9 if killed.is_set() else None

            def kill(self):
                killed.set()
                release_stdout.set()

            def wait(self, timeout=None):
                return -9

        proc = FakeProc()
        failures = []

        def broken_keepalive(piece):
            if piece is None:
                raise BrokenPipeError("client gone")

        def run_stream():
            try:
                self.mb.stream_muse("m", "p", "high", broken_keepalive)
            except Exception as exc:
                failures.append(exc)

        worker = threading.Thread(target=run_stream, daemon=True)
        with mock.patch.object(self.mb.subprocess, "Popen", return_value=proc), \
             mock.patch.object(self.mb, "KEEPALIVE_SEC", 0.01):
            worker.start()

            def cleanup():
                release_stdout.set()
                worker.join(timeout=2)

            self.addCleanup(cleanup)
            self.assertTrue(stdout_waiting.wait(timeout=1))
            self.assertTrue(
                killed.wait(timeout=0.5),
                "CLI kept running after the keepalive write failed")
            worker.join(timeout=1)

        self.assertFalse(worker.is_alive())
        self.assertTrue(failures)
        self.assertIsInstance(failures[0], RuntimeError)


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
