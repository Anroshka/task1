from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model

from .models import Defect, DefectHistory


User = get_user_model()


def log_defect_event(
	*,
	defect: Defect,
	user: User | None,
	action: str,
	changes: dict[str, Any] | None = None,
) -> DefectHistory:
	"""Создаёт запись в истории дефекта.

	changes хранит diff в виде {field: {from: ..., to: ...}} или произвольные данные.
	"""

	return DefectHistory.objects.create(
		defect=defect,
		changed_by=user if getattr(user, 'is_authenticated', False) else None,
		action=action,
		changes=changes or {},
	)
