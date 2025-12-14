from __future__ import annotations

from django.core.exceptions import PermissionDenied


def require_role(user, *, manager: bool = False, engineer: bool = False, customer: bool = False) -> None:
    """Проверка роли пользователя.

    Используется в функциях-вьюхах. В CBV предпочтительнее mixin.
    """

    if not user.is_authenticated:
        raise PermissionDenied

    allowed = []
    if manager:
        allowed.append(getattr(user, 'is_manager', False))
    if engineer:
        allowed.append(getattr(user, 'is_engineer', False))
    if customer:
        allowed.append(getattr(user, 'is_customer', False))

    if not any(allowed):
        raise PermissionDenied


def is_manager(user) -> bool:
    return bool(user.is_authenticated and getattr(user, 'is_manager', False))


def is_customer(user) -> bool:
    return bool(user.is_authenticated and getattr(user, 'is_customer', False))


def is_engineer(user) -> bool:
    return bool(user.is_authenticated and getattr(user, 'is_engineer', False))
