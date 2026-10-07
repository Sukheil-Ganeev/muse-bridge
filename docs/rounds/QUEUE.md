# Очередь раундов

| Раунд | Тема | Статус |
|---|---|---|
| R466 | POST: требовать однозначный `application/json` Content-Type | ✅ merged · PR #60 |
| R456 | except → return/continue/break — подавленная ошибка ведёт в журнал | ✅ [#58](https://github.com/Sukheil-Ganeev/muse-bridge/pull/58) |
| R446 | tests: очередь не показывает ✅ при незавершённом статусе спеки | ✅ [#56](https://github.com/Sukheil-Ganeev/muse-bridge/pull/56) |
| R436 | tests: AST-гейт учитывает новые неигнорируемые Python-файлы до git add | ✅ [#56](https://github.com/Sukheil-Ganeev/muse-bridge/pull/56) |
| R426 | tests: timeout на subprocess-вызовах + AST-гейт | ✅ [#54](https://github.com/Sukheil-Ganeev/muse-bridge/pull/54) |
| R416 | install: путь с %VAR% в Windows-автозапуске отклоняется | ✅ [#52](https://github.com/Sukheil-Ganeev/muse-bridge/pull/52) |
| R406 | POST: отклонять одиночные Unicode-суррогаты до запуска CLI | ✅ [#50](https://github.com/Sukheil-Ganeev/muse-bridge/pull/50) |
| R396 | HTTP: отклонять повторные Host и Origin | ✅ [#49](https://github.com/Sukheil-Ganeev/muse-bridge/pull/49) |
| R386 | stream: закрывать соединение после ошибки потока | ✅ [#48](https://github.com/Sukheil-Ganeev/muse-bridge/pull/48) |
| R376 | HTTP JSON: принимать только UTF-8-тело | ✅ [#48](https://github.com/Sukheil-Ganeev/muse-bridge/pull/48) |
| R366 | POST: отклонять нетекстовые части content вместо тихой потери | ✅ [#47](https://github.com/Sukheil-Ganeev/muse-bridge/pull/47) |
| R356 | Windows: Codex `.cmd/.bat` запускать через `cmd /c` | ✅ [#46](https://github.com/Sukheil-Ganeev/muse-bridge/pull/46) |
| R346 | POST: отклонять неизвестные роли сообщений в Muse и Codex | ✅ [#46](https://github.com/Sukheil-Ganeev/muse-bridge/pull/46) |
| R336 | codex: явно отклонять stream=true, пока SSE не поддерживается | ✅ [#45](https://github.com/Sukheil-Ganeev/muse-bridge/pull/45) |
| R326 | HTTP: закрывать соединение при раннем отказе до чтения тела | ✅ [#44](https://github.com/Sukheil-Ganeev/muse-bridge/pull/44) |
| R316 | codex: сохранять пробелы и форматирование ответа | ✅ [#43](https://github.com/Sukheil-Ganeev/muse-bridge/pull/43) |
| R306 | CODEX_BRIDGE_EXE: не переключаться на другую команду при неверном пути | ✅ [#42](https://github.com/Sukheil-Ganeev/muse-bridge/pull/42) |
| R296 | MUSE_BRIDGE_EXE: не переключаться на другой бинарник при неверном пути | ✅ [#41](https://github.com/Sukheil-Ganeev/muse-bridge/pull/41) |
| R286 | HTTP: отвечать на Expect: 100-continue в обоих мостах | ✅ [#39](https://github.com/Sukheil-Ganeev/muse-bridge/pull/39) |
| R276 | stream: ждать завершения активного keepalive перед концом ответа | ✅ [#38](https://github.com/Sukheil-Ganeev/muse-bridge/pull/38) |
| R266 | HTTP: проверка Origin и Host на локальных маршрутах | ✅ [#38](https://github.com/Sukheil-Ganeev/muse-bridge/pull/38) |
| R256 | HTTP: абсолютный срок строки запроса и заголовков | ✅ [#36](https://github.com/Sukheil-Ganeev/muse-bridge/pull/36) |
| R246 | HTTP: idle timeout строки запроса и заголовков | ✅ [#35](https://github.com/Sukheil-Ganeev/muse-bridge/pull/35) |
| R236 | POST: общий срок чтения тела в Muse и Codex | ✅ [#35](https://github.com/Sukheil-Ganeev/muse-bridge/pull/35) |
| R226 | codex: content:null не даёт текст «None» | ✅ [#34](https://github.com/Sukheil-Ganeev/muse-bridge/pull/34) |
| R216 | stream: cleanup после сбоя запуска watchdog | ✅ [#33](https://github.com/Sukheil-Ganeev/muse-bridge/pull/33) |
| R196 | macOS plist: отклонять управляющие символы в пути | ✅ [#31](https://github.com/Sukheil-Ganeev/muse-bridge/pull/31) |
| R186 | stream: failed без причины не должен принимать частичный текст | ✅ [#31](https://github.com/Sukheil-Ganeev/muse-bridge/pull/31) |
| R176 | muse: terminal failure не маскируется готовым текстом | ✅ [#30](https://github.com/Sukheil-Ganeev/muse-bridge/pull/30) |
| R166 | Linux autostart: отклонять управляющие символы в пути | ✅ [#29](https://github.com/Sukheil-Ganeev/muse-bridge/pull/29) |
| R156 | stream: закрывать stderr temp-файл при обрыве клиента | ✅ [#28](https://github.com/Sukheil-Ganeev/muse-bridge/pull/28) |
| R146 | temp prompt: cleanup при ошибке UTF-8-записи | ✅ [#28](https://github.com/Sukheil-Ganeev/muse-bridge/pull/28) |
| R136 | Linux installer: экранирование пути для desktop Exec | ✅ [#27](https://github.com/Sukheil-Ganeev/muse-bridge/pull/27) |
| R126 | stream: останавливать CLI после разрыва SSE-клиента | ✅ [#27](https://github.com/Sukheil-Ganeev/muse-bridge/pull/27) |
| R116 | macOS installer: XML-экранирование пути в LaunchAgent plist | ✅ [#26](https://github.com/Sukheil-Ganeev/muse-bridge/pull/26) |
| R106 | stream: ненулевой код выхода CLI не маскируется частичным текстом | ✅ [#25](https://github.com/Sukheil-Ganeev/muse-bridge/pull/25) |
| R096 | stream: ошибка terminal.failed не теряется после частичного текста | ✅ [#25](https://github.com/Sukheil-Ganeev/muse-bridge/pull/25) |
| R086 | POST: отклонять Transfer-Encoding, который мост не декодирует | ✅ [#24](https://github.com/Sukheil-Ganeev/muse-bridge/pull/24) |
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
