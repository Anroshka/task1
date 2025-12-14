# Резервное копирование БД (ежедневно)

## SQLite (локально)
Команда создаёт копию `db.sqlite3` в папку `backups/`:

- `python manage.py backup_db`

Автоматизация (Windows Task Scheduler):
- Создать задачу 1 раз в сутки
- Действие: запуск `C:\Users\...\task\.venv\Scripts\python.exe`
- Аргументы: `manage.py backup_db`
- Рабочая папка: корень проекта

## PostgreSQL (Docker)
Вариант A (рекомендуется): запуск `pg_dump` внутри контейнера `db`:
- `docker compose exec db pg_dump -U $POSTGRES_USER -d $POSTGRES_DB --format=custom --file /tmp/backup.dump`
- затем скопировать файл наружу: `docker compose cp db:/tmp/backup.dump backups/pg_YYYYMMDD.dump`

Вариант B: попытка из хоста через `python manage.py backup_db` (требуется `pg_dump` в PATH).
