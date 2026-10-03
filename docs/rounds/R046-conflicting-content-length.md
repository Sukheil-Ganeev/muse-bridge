# R046 — отклонять конфликтующие Content-Length

**Статус:** готово · без commit/push

## Цель

Не запускать Muse или Codex, если HTTP-запрос содержит несколько разных
значений `Content-Length`.

## Проблема

Оба обработчика читают только `headers.get("Content-Length")`. При повторном
заголовке стандартный объект заголовков возвращает одно значение, а конфликт
остаётся незамеченным. Тело может быть принято и передано CLI по одной из
несовпадающих границ.

## Сделано

- Добавлены тесты с двумя разными длинами для обоих мостов; до исправления оба
  обработчика отвечали `200` и вызывали подменённый CLI.
- Обработчики теперь читают все значения `Content-Length` и отвечают `400`,
  если значения расходятся. Повтор одинакового значения остаётся допустимым.

## Проверка

- `python3 -m unittest discover -s tests -p test_bridge.py -k DuplicateContentLengthTests`
  — до исправления: 2 ошибки (`200 != 400`); после: 2 теста, `OK`.
- Offline-набор bridge без HTTP-тестов, которым нужен loopback: 36 тестов,
  `OK`.
- Полный `python3 -m unittest discover -s tests`: 49 тестов; 13 ошибок при
  создании loopback-сокета (`PermissionError: [Errno 1] Operation not
  permitted` в sandbox), остальные тесты без ошибок.
- `python3 -m py_compile muse_bridge.py codex_bridge.py tests/test_bridge.py`
  — успешно; `git diff --check` — успешно.
