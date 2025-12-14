from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import RegistrationForm


def register_view(request):
	"""Регистрация нового пользователя.

	Безопасность:
	- пользователь не выбирает роль (иначе можно повысить привилегии);
	- создаём роль "Инженер".
	"""

	if request.user.is_authenticated:
		return redirect('dashboard')

	if request.method == 'POST':
		form = RegistrationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			messages.success(request, 'Регистрация успешна. Добро пожаловать!')
			return redirect('dashboard')
	else:
		form = RegistrationForm()

	return render(request, 'registration/register.html', {'form': form})
