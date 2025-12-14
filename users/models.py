from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
	"""Кастомная модель пользователя.

	Роли:
	- Инженер: создаёт дефекты, прикрепляет фото, меняет статус только своих задач.
	- Менеджер: полный CRUD, назначает исполнителей, меняет статусы.
	- Руководитель (Заказчик): только чтение + аналитика.

	Примечание: пароли хешируются встроенными механизмами Django (PBKDF2 по умолчанию).
	"""

	class Role(models.TextChoices):
		ENGINEER = 'engineer', 'Инженер'
		MANAGER = 'manager', 'Менеджер'
		CUSTOMER = 'customer', 'Руководитель (Заказчик)'

	role = models.CharField(
		max_length=32,
		choices=Role.choices,
		default=Role.ENGINEER,
		verbose_name='Роль',
	)

	@property
	def is_engineer(self) -> bool:
		return self.role == self.Role.ENGINEER

	@property
	def is_manager(self) -> bool:
		return self.role == self.Role.MANAGER

	@property
	def is_customer(self) -> bool:
		return self.role == self.Role.CUSTOMER
