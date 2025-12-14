from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
	help = 'Создаёт резервную копию БД в папку backups/ (SQLite: копирование файла, Postgres: pg_dump если доступен).'

	def add_arguments(self, parser):
		parser.add_argument(
			'--out-dir',
			default=str(Path(settings.BASE_DIR) / 'backups'),
			help='Папка для бэкапов (по умолчанию: backups/ в корне проекта).',
		)

	def handle(self, *args, **options):
		out_dir = Path(options['out_dir']).resolve()
		out_dir.mkdir(parents=True, exist_ok=True)

		db = settings.DATABASES['default']
		engine = db.get('ENGINE', '')
		now = datetime.now().strftime('%Y%m%d_%H%M%S')

		if 'sqlite3' in engine:
			src = Path(db['NAME']).resolve()
			if not src.exists():
				raise CommandError(f'SQLite DB file not found: {src}')
			dst = out_dir / f'db_{now}.sqlite3'
			shutil.copy2(src, dst)
			self.stdout.write(self.style.SUCCESS(f'Backup created: {dst}'))
			return

		if 'postgresql' in engine:
			# Пытаемся использовать pg_dump, если он есть в PATH.
			dst = out_dir / f'pg_{now}.dump'
			cmd = [
				'pg_dump',
				'--format=custom',
				'--file',
				str(dst),
				'--host',
				str(db.get('HOST') or 'localhost'),
				'--port',
				str(db.get('PORT') or 5432),
				'--username',
				str(db.get('USER') or ''),
				str(db.get('NAME') or ''),
			]

			env = os.environ.copy()
			pwd = db.get('PASSWORD')
			if pwd:
				env['PGPASSWORD'] = str(pwd)

			try:
				proc = subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
			except FileNotFoundError as exc:
				raise CommandError(
					'pg_dump не найден. Для Postgres бэкапа установите PostgreSQL client tools '
					'или используйте pg_dump внутри контейнера (см. docs/backup.md).'
				) from exc

			if proc.returncode != 0:
				raise CommandError(f'pg_dump failed: {proc.stderr.strip() or proc.stdout.strip()}')

			self.stdout.write(self.style.SUCCESS(f'Backup created: {dst}'))
			return

		raise CommandError(f'Unsupported DB engine: {engine}')
