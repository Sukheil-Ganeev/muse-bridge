# R001 — single-model-crash + контрактные тесты

**Статус:** done

## Цель
POST /v1/chat/completions не должен падать IndexError, когда
MUSE_BRIDGE_MODELS содержит ровно одну модель (или когда клиент просит
неизвестную модель). Плюс первый набор контрактных тестов моста — у
проекта их не было вообще.

## Дизайн
Баг: `MODELS[1]` в do_POST предполагает ≥2 записи в MODELS — при списке
из одной модели (или пустом, если env-переменная задана пустой строкой)
handler роняет сокет без JSON-ошибки. Чин: дефолтная модель =
`MODELS[1] if len(MODELS) > 1 else MODELS[0]`; пустой список после парсинга
env → откат к DEFAULT_MODELS. Тесты — unittest на чистых функциях
(extract_effort, build_prompt, дефолт модели, парсинг MODELS) и
http-уровне с заглушкой muse exec (подмена run_muse/stream_muse через
monkeypatch на атрибуты модуля — без сети, без muse CLI).

## Приёмка
- tests/test_bridge.py: дефолт модели при 1 и 2+ записях; effort-map
  границы; build_prompt роли/пустое/список-частей; POST /v1/chat/completions
  возвращает 200 с JSON при заглушенном exec (список из 1 модели — без
  IndexError); неизвестная модель → дефолтная, не падение.
- Гейт: `python3 -m unittest discover -s tests -v` — всё PASS, офлайн.

## Гейт
CHECK: python3 -m unittest discover -s tests -v
EXPECT: все тесты PASS
EVIDENCE: «Ran 15 tests in 2.540s / OK» (2026-10-02, ветка
devin/…-r001-single-model-crash). До чина 2 падения:
ERROR test_unknown_model_falls_back_not_crash (IndexError → обрыв сокета),
FAIL test_empty_env_falls_back_to_defaults (MODELS=[] без отката).
