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

## R466 — POST требует однозначный JSON Content-Type

**Итог:** Muse Bridge и Codex Bridge отвечают HTTP 415 до чтения тела и запуска
CLI, если Content-Type отсутствует, повторяется или объявляет не JSON.
application/json с параметром charset принимается.

**Файлы:** muse_bridge.py, codex_bridge.py, tests/test_bridge.py,
docs/rounds/R466-json-content-type.md, docs/rounds/QUEUE.md, OUT.md.

**До исправления:** PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m
unittest test_bridge.JsonContentTypeTests — 3 теста, 2 провала; оба моста
приняли запрос без Content-Type и вернули 200 вместо 415.

**После исправления:** адресный набор — 3 теста за 0.019 сек., OK. Выбранный
офлайн-набор мостов, дедлайнов, потоковой обработки, очереди и установщиков —
119 тестов за 0.698 сек., OK.

**Дополнительные гейты:** Python 3.14.4;
PYTHONPYCACHEPREFIX=/tmp/muse-bridge-r466-pycache python3 -m py_compile
muse_bridge.py codex_bridge.py tests/test_bridge.py tests/test_round_queue.py —
код 0; git diff --check — код 0. Сокетные тесты с loopback-bind не запускались:
sandbox запрещает bind локального порта. Commit и push не выполнялись.

## R476 — завершённая запись очереди требует статуса в спеке

**Итог:** тестовый гейт теперь считает ошибкой завершённую строку очереди
(`✅`), если у соответствующей спеки нет строки `**Статус:**`. Для старых
записей без статуса, которые очередь не отмечает завершёнными, предупреждение
не создаётся. Статусы добавлены в завершённые исторические спеки; `merged`
распознаётся как завершённое состояние.

**Файлы R476:** `tests/test_round_queue.py`, `docs/rounds/QUEUE.md`,
`docs/rounds/R476-round-queue-requires-spec-status.md`, `OUT.md` и девять
исторических спек R001–R011 с уже завершёнными строками в очереди.

**Тест до исправления:** адресная регрессия выполнила проверку очереди, но
получила 0 расхождений вместо ожидаемого 1: отсутствие статуса не проверялось.

**После исправления:** `PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m
unittest test_round_queue` — 3 теста, `OK`.

`PYTHONPYCACHEPREFIX=/tmp/muse-bridge-r476-pycache python3 -m py_compile
tests/test_round_queue.py` — код 0; `git diff --check` — код 0. Commit и push не
выполняются; результат оставлен для переноса.

## R486 — противоречивые статусы спеки не проходят гейт

**Итог:** проверка раундов теперь сверяет все строки `**Статус:**` в спеке.
Если они расходятся в том, завершён раунд или ещё открыт, проверка сообщает
ошибку вместо того, чтобы верить только первой строке. Повторные формулировки
одного состояния принимаются; `выполнено` распознаётся как завершение.

**Файлы R486:** `tests/test_round_queue.py`, `docs/rounds/QUEUE.md`,
`docs/rounds/R486-duplicate-spec-status.md`, `OUT.md`.

**Тест до исправления:**

```text
PYTHONPATH=tests python3 -B -m unittest test_round_queue.RoundQueueTests.test_duplicate_spec_status_lines_are_rejected
Ran 1 test
FAILED (failures=1)
AssertionError: 0 != 1 : the round gate must reject duplicate status lines
```

Тест показал, что завершённая первая строка скрывала следующую строку «в работе».
При проверке всего набора также обнаружилась уже существующая пара завершённых
формулировок `done` / `выполнено` у R456; обе теперь считаются одним состоянием.

**После исправления:**

```text
PYTHONPATH=tests python3 -B -m unittest test_round_queue
Ran 6 tests in 0.011s
OK
```

Дополнительный тест также поймал случай пустой строки статуса, после которой
«done» скрывалось из-за `\s*`, перешедшего через перевод строки; этот сценарий
падал до исправления и проходит теперь.

`python3 -m py_compile tests/test_round_queue.py` — код 0;
`git diff --check` — код 0. Файл байткода, созданный компилятором в
`tests/__pycache__`, удалён. Commit и push не выполнялись; изменения оставлены
для переноса родительским агентом.

## R496 — повторный номер раунда не проходит проверку очереди

**Итог:** проверка теперь считает ошибкой второй и последующий строки очереди с
одинаковым номером раунда, даже если обе строки ссылаются на одну спеку и имеют
одинаковый завершённый статус.

**Файлы R496:** `tests/test_round_queue.py`, `docs/rounds/QUEUE.md`,
`docs/rounds/R496-duplicate-round-queue-ids.md`, `OUT.md`.

**Тест до исправления:**

```text
PYTHONPATH=tests python3 -B -m unittest test_round_queue.RoundQueueTests.test_duplicate_round_queue_ids_are_rejected
Ran 1 test
FAILED (failures=1)
AssertionError: 0 != 1 : the round gate must reject duplicate queue IDs
```

**После исправления:**

```text
PYTHONPATH=tests python3 -B -m unittest test_round_queue
Ran 6 tests in 0.011s
OK
```

`python3 -m py_compile tests/test_round_queue.py` и `git diff --check` — код 0.
Временный `.pyc` удалён. Commit и push не выполнялись; изменения оставлены для
переноса родительским агентом.
## R506 — проверять номера раундов длиннее трёх цифр

**Итог:** тест очереди теперь проверяет `R1000` и последующие номера; раньше
строка с четырьмя цифрами полностью выпадала из проверки статуса очереди и спеки.

**Файлы:** `tests/test_round_queue.py`, `docs/rounds/R506-round-queue-four-digit-ids.md`,
`docs/rounds/QUEUE.md`, `OUT.md`.

**До исправления:**
`PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest
test_round_queue.RoundQueueTests.test_round_ids_above_999_are_checked` — 1 тест,
провал; обнаружено `0` расхождений вместо ожидаемого `1` для `R1000`.

**Проверки после исправления:**

```text
$ PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest test_round_queue test_no_unbounded_subprocess
Ran 6 tests in 0.297s
OK

$ PYTHONPYCACHEPREFIX="$PWD/.round486-pycache" python3 -m py_compile tests/test_round_queue.py
exit code: 0

$ git diff --check
exit code: 0
```

Временный каталог байткода внутри репозитория удалён после компиляции. Пакеты
не устанавливались. Осталась прежняя открытая запись R008: там не пройдены
HTTP-проверки, требующие loopback-bind в sandbox; R506 её не затрагивает.
Изменения оставлены локально для переноса родительским агентом; commit/push не
выполнялись.
