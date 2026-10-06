# Очередь раундов

| Раунд | Тема | Статус |
|---|---|---|
| R366 | POST: отклонять нетекстовые части content вместо тихой потери | ✅ локально, без commit/push |
| R356 | Windows: Codex `.cmd/.bat` запускать через `cmd /c` | ✅ локально, без commit/push |
| R346 | POST: отклонять неизвестные роли сообщений в Muse и Codex | ✅ локально, без commit/push |
| R336 | codex: явно отклонять stream=true, пока SSE не поддерживается | ✅ локально, без commit/push |
| R326 | HTTP: закрывать соединение при раннем отказе до чтения тела | ✅ локально, без commit/push |
| R316 | codex: сохранять пробелы и форматирование ответа | ✅ локально, без commit/push |
| R306 | CODEX_BRIDGE_EXE: не переключаться на другую команду при неверном пути | ✅ локально, без commit/push |
| R296 | MUSE_BRIDGE_EXE: не переключаться на другой бинарник при неверном пути | ✅ локально, без commit/push |
| R286 | HTTP: отвечать на Expect: 100-continue в обоих мостах | ✅ локально, без commit/push |
| R276 | stream: ждать завершения активного keepalive перед концом ответа | ✅ локально, без commit/push |
| R266 | HTTP: проверка Origin и Host на локальных маршрутах | ✅ локально, без commit/push |
| R256 | HTTP: абсолютный срок строки запроса и заголовков | ✅ локально, без commit/push |
| R246 | HTTP: idle timeout строки запроса и заголовков | ✅ локально, без commit/push |
| R236 | POST: общий срок чтения тела в Muse и Codex | ✅ локально, без commit/push |
| R226 | codex: content:null не даёт текст «None» | ✅ локально, без commit/push |
| R216 | stream: cleanup после сбоя запуска watchdog | ✅ локально, без commit/push |
| R196 | macOS plist: отклонять управляющие символы в пути | ✅ локально, без commit/push |
| R186 | stream: failed без причины не должен принимать частичный текст | ✅ локально, без commit/push |
| R176 | muse: terminal failure не маскируется готовым текстом | ✅ локально, без commit/push |
| R166 | Linux autostart: отклонять управляющие символы в пути | ✅ локально, без commit/push |
| R156 | stream: закрывать stderr temp-файл при обрыве клиента | ✅ локально, без commit/push |
| R146 | temp prompt: cleanup при ошибке UTF-8-записи | ✅ локально, без commit/push |
| R136 | Linux installer: экранирование пути для desktop Exec | ✅ локально, без commit/push |
| R126 | stream: останавливать CLI после разрыва SSE-клиента | ✅ локально, без commit/push |
| R116 | macOS installer: XML-экранирование пути в LaunchAgent plist | ✅ локально, без commit/push |
| R106 | stream: ненулевой код выхода CLI не маскируется частичным текстом | ✅ локально, без commit/push |
| R096 | stream: ошибка terminal.failed не теряется после частичного текста | ✅ локально, без commit/push |
| R086 | POST: отклонять Transfer-Encoding, который мост не декодирует | ✅ локально, без commit/push |
| R015 | codex: числовой text-парт в content сводится к строке | ✅ [#17](https://github.com/Sukheil-Ganeev/muse-bridge/pull/17) |
| R014 | codex: уникальный temp-файл ответа на запрос (не общий) | ✅ [#17](https://github.com/Sukheil-Ganeev/muse-bridge/pull/17) |
| R013 | Проверка формы JSON-тела в POST /v1/chat/completions | ✅ [#16](https://github.com/Sukheil-Ganeev/muse-bridge/pull/16) |
| R012 | PORT env: мусорное значение = warn + дефолт | ✅ [#15](https://github.com/Sukheil-Ganeev/muse-bridge/pull/15) |
| R011 | terminal-failed с reason в исключении | ✅ [#14](https://github.com/Sukheil-Ganeev/muse-bridge/pull/14) |
| R010 | content:null не даёт текст «None» | ✅ [#13](https://github.com/Sukheil-Ganeev/muse-bridge/pull/13) |
| R009 | Content-Length: только ASCII-цифры | ✅ [#12](https://github.com/Sukheil-Ganeev/muse-bridge/pull/12) |
| R008 | stream: очистка временных файлов при ошибке запуска exec | 🟡 локальная проверка; HTTP-тесты заблокированы sandbox |
| R007 | stream: только булево true включает SSE | ✅ этот PR |
| R006 | reasoning как строка = значение усилия (fix crash) | ✅ [#9](https://github.com/Sukheil-Ganeev/muse-bridge/pull/9) |
| R004 | Проверка формы JSON-тела в POST | ✅ bf212c1 (прямой коммит, ошибка процесса — без PR) |
| R003 | Лимит и строгий разбор Content-Length в POST | ✅ [#5](https://github.com/Sukheil-Ganeev/muse-bridge/pull/5) |
| R002 | Отмена exec при обрыве клиента + уборка temp-файла | ✅ [#3](https://github.com/Sukheil-Ganeev/muse-bridge/pull/3) |
| R001 | Падение POST при единственной модели + контрактные тесты | ✅ [#1](https://github.com/Sukheil-Ganeev/muse-bridge/pull/1) |
