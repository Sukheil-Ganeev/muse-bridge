# R066 — сохранять falsey-значения в текстовых частях Muse

**Статус:** готово · без commit/push  
**Дата:** 2026-10-03

## Цель

Не терять допустимое значение текстовой части `0` или `false` при сборке
промпта в Muse Bridge.

## Проблема

`build_prompt` отбрасывал часть, если `text` было ложным в Python. Поэтому
`0` и `False` пропадали, хотя остальные нестроковые значения преобразуются
в текст.

## Сделано

Пропускаются только отсутствующее (`None`) и пустая строка; прочие значения
текстового поля сохраняются через `str()`.

## Проверка

- До исправления: `python3 -m unittest discover -s tests -p test_bridge.py -k falsey_non_string_text_parts_are_preserved` — 1 ошибка; ожидалось `[user]\n0 False`, фактически `[user]\n`.
- После исправления: `PYTHONPATH=tests python3 -m unittest test_bridge.ExtractEffortTests test_bridge.BuildPromptTests test_bridge.ModelListTests test_bridge.CodexBuildPromptTests test_bridge.CodexPostValidationTests test_bridge.CodexContentLengthTests test_bridge.MusePostValidationTests test_bridge.TruncatedBodyTests test_bridge.DuplicateContentLengthTests test_bridge.CodexOutputIsolationTests test_bridge.TerminalFailureTests test_bridge.ContentLengthParsingTests test_bridge.StreamAbortTests` — 39 тестов, `OK`.
- `python3 -m py_compile muse_bridge.py tests/test_bridge.py` — успешно.
- `git diff --check` — успешно.
- HTTP-тесты с loopback-сокетами не запускались; раунд проверяет сборку промпта и офлайн-регрессии.
