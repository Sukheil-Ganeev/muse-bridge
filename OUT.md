# R346 + R356 — итог раундов

**Состояние:** оба раунда проверены локально; commit/push не выполнялись.
`OUT.md` оставлен в корне репозитория, работа велась только внутри него.

## Файлы

- `muse_bridge.py`, `codex_bridge.py`: проверять роль каждого сообщения;
  Codex `.cmd/.bat` на Windows запускать через `cmd /c`.
- `tests/test_bridge.py`: регрессии для некорректных ролей в обоих мостах и
  для выбора команды Codex в Windows.
- `docs/rounds/R346-message-role-validation.md`,
  `docs/rounds/R356-windows-codex-command-wrapper.md`,
  `docs/rounds/QUEUE.md`: спецификации и статусы раундов.
- `OUT.md`: прежний отчёт сохранён; ниже добавлен результат R366.

## Проверки

- R346 до исправления: адресный unittest — 1 тест, 6 провалов; оба моста
  принимали `role: null`, число и строку, подменяющую границы роли.
- R346 после исправления: адресный unittest — 1 тест, `OK`.
- R356 до исправления: адресный unittest завершился `AttributeError` — команды
  Codex `.cmd/.bat` не было.
- Первый вариант теста запускал `run_codex()` при подменённом `os.name` на Linux;
  он упёрся в Windows-формат временного пути в `tempfile`. Тест заменён
  изолированной проверкой построения команды, которая до исправления падала на
  отсутствующем `_codex_command`.
- R356 после исправления: адресные unittest — 2 теста, `OK`.
  Они проверяют построение argv; фактический запуск Windows `cmd.exe` в Linux
  sandbox не выполнялся.
- Общий офлайн-набор прежних раундов: 107 тестов за 0.590 сек., `OK`.
  Классы `PostHandlerTests` и `HealthTests`, которым нужен loopback-сокет,
  исключены из этого офлайн-прогона.
- `python3 -m py_compile muse_bridge.py codex_bridge.py tests/test_bridge.py` —
  код 0; временный кэш компиляции удалён автоматически.
- `git diff --check` — код 0.
- Python 3.14.4. `pytest` отсутствует (`No module named pytest`), поэтому
  использован разрешённый unittest-набор без установки пакетов.

## Осталось

- Loopback HTTP-тесты здесь не запускались; живой сетевой результат не заявлен.
- Изменения оставлены в рабочем дереве для переноса родительским агентом.

## R366 — нетекстовые части запроса не теряются молча

До начала работы `OUT.md` был удалён в рабочем дереве. По требованию задания
отчёт восстановлен из версии HEAD; прежний текст сохранён, ниже добавлена новая
часть.

**Итог:** Muse Bridge и Codex Bridge теперь отвечают 400 до запуска CLI, если
массив `content` содержит не-объект или явный тип части, отличный от `text`.
Текстовые части, включая части без поля `type`, сохраняют прежнее поведение.

**Файлы R366:** `muse_bridge.py`, `codex_bridge.py`, `tests/test_bridge.py`,
`docs/rounds/R366-text-only-content-parts.md`, `docs/rounds/QUEUE.md`, `OUT.md`.

**Тест до исправления:**

```text
$ PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest test_bridge.UnsupportedContentPartTests
Ran 1 test in 0.020s
FAILED (failures=2)
```

Оба подслучая получили 200 вместо 400: мосты отбрасывали `image_url` и всё же
вызывали CLI.

**После исправления:** выбранный офлайн-набор из 108 unittest прошёл за 0.614 сек.:

```text
Ran 108 tests in 0.614s
OK
```

В набор вошли тесты мостов без сетевого bind, установщиков и очереди раундов;
`PostHandlerTests` и `HealthTests` не запускались. Точный запуск:

```text
PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest \
test_bridge.ExtractEffortTests test_bridge.BuildPromptTests test_bridge.ModelListTests \
test_bridge.FindMuseTests test_bridge.FindCodexTests test_bridge.CodexWindowsCommandTests \
test_bridge.CodexBuildPromptTests test_bridge.CodexPostValidationTests \
test_bridge.CodexContentLengthTests test_bridge.RequestExpectationTests \
test_bridge.RequestOriginProtectionTests test_bridge.EarlyRejectConnectionTests \
test_bridge.RequestHeaderTimeoutTests test_bridge.AbsoluteRequestHeaderDeadlineTests \
test_bridge.PostBodyDeadlineTests test_bridge.MusePostValidationTests \
test_bridge.MessageRoleValidationTests test_bridge.UnsupportedContentPartTests \
test_bridge.TruncatedBodyTests test_bridge.DuplicateContentLengthTests \
test_bridge.TransferEncodingTests test_bridge.CodexOutputIsolationTests \
test_bridge.CodexOutputWhitespaceTests test_bridge.TerminalFailureTests \
test_bridge.PromptTempCreationFailureTests test_bridge.ContentLengthParsingTests \
test_bridge.StreamAbortTests test_bridge.StreamKeepaliveAbortTests \
test_bridge.StreamKeepaliveCompletionTests test_install_scripts \
test_round_queue.RoundQueueTests
```

`py_compile` успешно проверил три изменённых Python-файла; байткод записывался
во временные файлы внутри репозитория, затем эти файлы удалены. `git diff --check`
успешен. `pytest` недоступен, `tests/test_env_port.py` (pytest-style) не запускался.
Commit и push не выполнялись. Остались незапущенные loopback-проверки; фактический
запуск Windows `cmd.exe` не проверялся в Linux sandbox.

## R406 — отклонять одиночные Unicode-суррогаты до запуска CLI

**Итог:** Muse Bridge и Codex Bridge теперь отвечают 400, если собранный промпт
не кодируется в UTF-8 из-за экранированного одиночного суррогата. Процесс CLI не
запускается. Обычный Unicode-текст и потоковые запросы без такого значения
сохраняют прежнее поведение.

**Файлы R406:** `muse_bridge.py`, `codex_bridge.py`, `tests/test_bridge.py`,
`docs/rounds/R406-reject-escaped-surrogates.md`, `docs/rounds/QUEUE.md`, `OUT.md`.

**Тест до исправления:** `EscapedSurrogateJsonTests` — 1 тест, 2 провала; оба
моста вернули 502 вместо 400.

**После исправления:** тест R406 прошёл. Выбранный офлайн-набор — 113 тестов за
0.600 сек., `OK`. В него не вошли `PostHandlerTests` и `HealthTests`, которым
нужны loopback-сокеты. `python3 -m py_compile muse_bridge.py codex_bridge.py
tests/test_bridge.py` и `git diff --check` — успешно.

Commit и push не выполнялись; результат оставлен для переноса родительским
агентом.

## R436 — новый Python-файл не пропускает AST-гейт subprocess-timeout

**Итог:** локальная проверка теперь замечает новые, ещё не добавленные в Git
Python-файлы и проверяет в них ограничение ожидания дочерних процессов.

**Файлы:** `tests/test_no_unbounded_subprocess.py`,
`docs/rounds/R436-untracked-python-subprocess-gate.md`,
`docs/rounds/QUEUE.md`, `OUT.md`.

**До исправления:** новый адресный тест завершился одним провалом: временный
неотслеживаемый `.py` отсутствовал в `_live_py_files()`.

**После исправления:** `PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m
unittest test_no_unbounded_subprocess test_round_queue` — 3 теста, `OK`.
`python3 -m py_compile tests/test_no_unbounded_subprocess.py` и
`git diff --check` — успешно.

Полный `unittest discover` выполнил 130 тестов: 13 HTTP-проверок завершились
ошибкой sandbox при попытке открыть loopback-сокет (`PermissionError`), другие
117 прошли. `pytest` отсутствует; ничего не устанавливалось. Временный
`.pyc` удалён. Commit и push не выполнялись.
