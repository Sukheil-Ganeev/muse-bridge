# R326 — итог раунда

**Состояние:** готово локально, без commit/push. Изменения оставлены в dirty tree для переноса родительским агентом.

## Что изменено

- `muse_bridge.py` и `codex_bridge.py`: ранние отказы закрывают соединение до ответа, если тело не было прочитано полностью; это охватывает Origin, ошибочные/слишком большие заголовки, неподдерживаемый Transfer-Encoding/Expect, таймаут или короткое тело, а также неизвестный маршрут.
- Неизвестный GET-маршрут также выставляет внутренний флаг закрытия: одного ответа `Connection: close` от `send_error()` недостаточно для остановки цикла обработчика.
- `tests/test_bridge.py`: добавлены проверки непрочитанного cross-site тела, короткого тела и неизвестного GET-маршрута для обоих мостов.
- `docs/rounds/R326-close-connection-on-early-reject.md` и `docs/rounds/QUEUE.md`: зафиксированы причина, решение и статус.

## Проверки

- До исправления: три теста непрочитанного/короткого тела упали, потому что `close_connection` оставался `False`; отдельный тест неизвестного GET-маршрута также сначала упал на этом флаге.
- После исправления: офлайн-набор `test_bridge` без `PostHandlerTests` и `HealthTests` — 98 тестов, `OK`.
- `PYTHONPATH=tests python3 -B -m unittest test_round_queue test_install_scripts test_env_port` — 5 тестов, `OK`.
- `PYTHONPYCACHEPREFIX=/tmp/muse-bridge-r326-pycache python3 -m py_compile muse_bridge.py codex_bridge.py tests/test_bridge.py` — код 0.
- `git diff --check` — код 0.
- Live loopback HTTP-проверки не запускались; поэтому интеграционный разбор второго запроса на одном реальном сокете отдельно не подтверждён.

## Осталось открытым

- Повторить сценарий с двумя HTTP-запросами на одном реальном keep-alive сокете в среде, где loopback доступен.
- Commit и push не выполнялись.
