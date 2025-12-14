from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Project(models.Model):
	"""Проект (строительный объект)."""

	name = models.CharField(max_length=255, verbose_name='Название')
	address = models.CharField(max_length=500, verbose_name='Адрес')
	start_date = models.DateField(verbose_name='Дата начала')
	end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')

	class Meta:
		verbose_name = 'Проект'
		verbose_name_plural = 'Проекты'

	def __str__(self) -> str:
		return self.name


class ProjectStage(models.Model):
	"""Этап проекта.

	ТЗ требует "управление проектами/объектами и их этапами".
	"""

	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='stages', verbose_name='Проект')
	name = models.CharField(max_length=255, verbose_name='Название этапа')
	start_date = models.DateField(null=True, blank=True, verbose_name='Дата начала')
	end_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
	order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

	class Meta:
		verbose_name = 'Этап проекта'
		verbose_name_plural = 'Этапы проекта'
		ordering = ('order', 'start_date', 'id')
		indexes = [
			models.Index(fields=['project', 'order']),
		]

	def __str__(self) -> str:
		return f"{self.project}: {self.name}"


class Defect(models.Model):
	"""Дефект на объекте.

	Workflow: Новая -> В работе -> На проверке -> Закрыта | Отменена
	"""

	class Priority(models.TextChoices):
		LOW = 'low', 'Low'
		MEDIUM = 'medium', 'Medium'
		HIGH = 'high', 'High'

	class Status(models.TextChoices):
		NEW = 'new', 'Новая'
		IN_PROGRESS = 'in_progress', 'В работе'
		ON_REVIEW = 'on_review', 'На проверке'
		CLOSED = 'closed', 'Закрыта'
		CANCELLED = 'cancelled', 'Отменена'

	title = models.CharField(max_length=255, verbose_name='Заголовок')
	description = models.TextField(verbose_name='Описание')
	priority = models.CharField(
		max_length=16,
		choices=Priority.choices,
		default=Priority.MEDIUM,
		verbose_name='Приоритет',
	)
	status = models.CharField(
		max_length=32,
		choices=Status.choices,
		default=Status.NEW,
		verbose_name='Статус',
	)
	deadline = models.DateField(verbose_name='Срок устранения (Deadline)')

	executor = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='assigned_defects',
		verbose_name='Исполнитель',
	)
	project = models.ForeignKey(
		Project,
		on_delete=models.CASCADE,
		related_name='defects',
		verbose_name='Проект',
	)

	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
	updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

	class Meta:
		verbose_name = 'Дефект'
		verbose_name_plural = 'Дефекты'
		ordering = ('-created_at',)
		indexes = [
			models.Index(fields=['status', 'priority']),
			models.Index(fields=['deadline']),
		]

	def __str__(self) -> str:
		return f"{self.title} ({self.get_status_display()})"

	def clean(self) -> None:
		if self.project and self.project.end_date and self.deadline > self.project.end_date:
			raise ValidationError({'deadline': 'Deadline не должен быть позже даты окончания проекта.'})

	@staticmethod
	def workflow_transitions() -> dict[str, set[str]]:
		"""Разрешённые переходы статусов независимо от роли."""

		return {
			Defect.Status.NEW: {Defect.Status.IN_PROGRESS, Defect.Status.CANCELLED},
			Defect.Status.IN_PROGRESS: {Defect.Status.ON_REVIEW, Defect.Status.CANCELLED},
			Defect.Status.ON_REVIEW: {Defect.Status.CLOSED, Defect.Status.CANCELLED},
			Defect.Status.CLOSED: set(),
			Defect.Status.CANCELLED: set(),
		}

	def allowed_next_statuses_for(self, user) -> list[str]:
		"""Список статусов, на которые пользователь может перевести дефект."""

		allowed_by_workflow = self.workflow_transitions().get(self.status, set())
		if not user.is_authenticated:
			return []

		# Менеджер может переводить в любые допустимые статусы по workflow
		if getattr(user, 'is_manager', False):
			return sorted(allowed_by_workflow)

		# Руководитель только читает
		if getattr(user, 'is_customer', False):
			return []

		# Инженер: только по своим задачам (где он исполнитель)
		if getattr(user, 'is_engineer', False):
			if self.executor_id != user.id:
				return []
			# Инженер не закрывает (закрывает менеджер), и не отменяет
			return [s for s in allowed_by_workflow if s in {Defect.Status.IN_PROGRESS, Defect.Status.ON_REVIEW}]

		return []

	def can_view(self, user) -> bool:
		if not user.is_authenticated:
			return False
		if getattr(user, 'is_manager', False) or getattr(user, 'is_customer', False):
			return True
		# Инженер видит только назначенные ему дефекты
		return getattr(user, 'is_engineer', False) and self.executor_id == user.id

	def can_edit(self, user) -> bool:
		if not user.is_authenticated:
			return False
		if getattr(user, 'is_manager', False):
			return True
		# Инженер может редактировать только свои задачи и только пока они не закрыты/отменены
		if getattr(user, 'is_engineer', False) and self.executor_id == user.id:
			return self.status not in {Defect.Status.CLOSED, Defect.Status.CANCELLED}
		return False


def attachment_upload_to(instance: 'Attachment', filename: str) -> str:
	return f"attachments/defect_{instance.defect_id}/{filename}"


class Attachment(models.Model):
	"""Вложение (фото/документ) к дефекту."""

	defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='attachments', verbose_name='Дефект')
	file = models.FileField(upload_to=attachment_upload_to, verbose_name='Файл')
	uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')

	class Meta:
		verbose_name = 'Вложение'
		verbose_name_plural = 'Вложения'

	def __str__(self) -> str:
		return self.file.name


class Comment(models.Model):
	"""Комментарий к дефекту (история переписки)."""

	defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='comments', verbose_name='Дефект')
	author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Автор')
	text = models.TextField(verbose_name='Комментарий')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

	class Meta:
		verbose_name = 'Комментарий'
		verbose_name_plural = 'Комментарии'
		ordering = ('created_at',)

	def __str__(self) -> str:
		return f"Комментарий #{self.pk}"


class DefectHistory(models.Model):
	"""История изменений по дефекту.

	ТЗ требует "ведение комментариев и истории изменений".
	"""

	class Action(models.TextChoices):
		CREATED = 'created', 'Создан'
		UPDATED = 'updated', 'Изменён'
		STATUS_CHANGED = 'status_changed', 'Изменён статус'
		COMMENT_ADDED = 'comment_added', 'Добавлен комментарий'
		ATTACHMENT_ADDED = 'attachment_added', 'Добавлено вложение'

	defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='history', verbose_name='Дефект')
	changed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='defect_history_events',
		verbose_name='Кто изменил',
	)
	action = models.CharField(max_length=32, choices=Action.choices, verbose_name='Событие')
	changes = models.JSONField(default=dict, blank=True, verbose_name='Изменения (diff)')
	created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата события')

	class Meta:
		verbose_name = 'История дефекта'
		verbose_name_plural = 'История дефекта'
		ordering = ('-created_at', '-id')
		indexes = [
			models.Index(fields=['defect', 'created_at']),
		]

	def __str__(self) -> str:
		return f"Defect#{self.defect_id}: {self.get_action_display()}"
