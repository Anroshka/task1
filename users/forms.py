from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegistrationForm(UserCreationForm):
    """Форма регистрации.

    Безопасность:
    - роль не выбирается пользователем (защита от повышения привилегий);
    - создаём только "Инженера".
    """

    email = forms.EmailField(required=False, label='Email')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def save(self, commit: bool = True) -> User:
        user: User = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        user.role = User.Role.ENGINEER
        if commit:
            user.save()
        return user
