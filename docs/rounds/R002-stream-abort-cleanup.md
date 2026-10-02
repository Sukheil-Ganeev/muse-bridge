# R002 — отмена muse exec при обрыве клиента и уборка temp-файла

## Зазор

`stream_muse` (`muse_bridge.py`): когда HTTP-клиент обрывает SSE-соединение,
`on_delta` бросает `BrokenPipeError`, но дочерний `muse exec` продолжает жечь
compute до срабатывания deadline-таймера (до 280 с), а thread ждёт
`proc.wait(timeout=EXEC_TIMEOUT)`. Плюс на ЛЮБОМ ошибочном пути
(BrokenPipe, timeout, kill) `prompt_path` не удаляется — утечка temp-файлов,
и `err_fp` может остаться незакрытым.

## CHECK / EXPECT

- CHECK: клиент обрывается во время стрима (on_delta бросает) → процесс
  убивается немедленно (kill до wait), temp prompt-файл удалён, deadline
  отменён.
- CHECK: нормальный завершающийся стрим → kill НЕ вызывается (poll() != None),
  файл удалён, возвращённый текст полный.
- EXPECT: python3 -m unittest tests.test_bridge — все PASS; новый
  StreamAbortTests покрывает оба пути.

## План минимальной правки

Схлопнуть cleanup в один `finally` после read-loop: `stop.set()` →
`proc.kill()` если `poll() is None` → `Path(prompt_path).unlink` →
короткий `proc.wait(10)` → `deadline.cancel()`. Убрать отдельный блок
`proc.wait(timeout=EXEC_TIMEOUT)` (hard-timeout уже обеспечен deadline-таймером
в read-loop). `err_fp.close()` — безусловно после чтения ошибки/успеха.

## EVIDENCE

```
$ python3 -m unittest discover -s tests
test_client_abort_kills_exec_and_removes_prompt_file ... ok
test_clean_stream_returns_text_without_kill ... ok
Ran 17 tests in 2.547s
OK
$ git diff --check   # clean
```

До правки `test_client_abort_kills_exec_and_removes_prompt_file` был RED:
`AssertionError: False is not true` на `proc.killed` — процесс продолжал
работать после обрыва клиента. После правки — GREEN.
