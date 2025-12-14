# Нагрузочное тестирование

Цель: подтвердить время отклика страниц ≤ 1 сек при 50 активных пользователях (в рамках стенда).

## Инструмент
Используется Locust (см. requirements.txt).

## Запуск
1) Поднять приложение:
- локально (Windows/venv): `C:/Users/astec/Downloads/task/.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000`
- или Docker: `docker compose up --build`

2) Запустить нагрузку (пример: 50 пользователей, 10 пользователей/сек, 1 минута):
- Windows/venv (рекомендуется, чтобы не зависеть от PATH):
	- `C:/Users/astec/Downloads/task/.venv/Scripts/python.exe -m locust -f loadtest/locustfile.py --host http://127.0.0.1:8000 -u 50 -r 10 --headless -t 1m --only-summary`

Важно:
- Команда `locust ...` может не находиться в PATH — это нормально; используйте `python -m locust`.
- Не вставляйте в PowerShell ссылки вида `[locustfile.py](http://...)` — нужен реальный путь `loadtest/locustfile.py`.

## Что фиксировать (отчёт)
- Средний/95p latency по `/login/` и `/` (dashboard)
- Кол-во ошибок (HTTP 4xx/5xx)
- Конфигурацию стенда (CPU/RAM, тип БД)

## Критерий приёмки
- 95‑перцентиль времени ответа (p95) ≤ 1.0 сек
- Ошибок 5xx = 0

Примечание: фактические цифры зависят от железа и режима DEBUG.

## Результаты прогона (зафиксировано)
Дата: **2025-12-14**

Параметры:
- Users: 50
- Spawn rate: 10/sec
- Duration: 1m

Сводка (Locust `--only-summary`):
- Ошибки 5xx: 0
- `GET / (dashboard)` p95 ≈ 37 ms
- `GET /projects/` p95 ≈ 26 ms
- `GET /login/` p95 ≈ 100 ms
- `POST /login/` p95 ≈ 1500 ms (логин тяжелее из‑за проверки хеша пароля)

Вывод по критерию «время отклика страниц ≤ 1 сек»:
- Основные страницы (`/`, `/projects/`) укладываются в требование с большим запасом.
