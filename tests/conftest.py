import datetime as dt

import pytest

from defects.models import Defect, Project


@pytest.fixture
def manager(django_user_model):
    u = django_user_model.objects.create_user(username='manager', password='pass', role='manager')
    return u


@pytest.fixture
def engineer(django_user_model):
    u = django_user_model.objects.create_user(username='engineer', password='pass', role='engineer')
    return u


@pytest.fixture
def customer(django_user_model):
    u = django_user_model.objects.create_user(username='customer', password='pass', role='customer')
    return u


@pytest.fixture
def project():
    return Project.objects.create(
        name='ЖК Северный',
        address='Москва, ул. Примерная, 1',
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 12, 31),
    )


@pytest.fixture
def defect(project, engineer):
    return Defect.objects.create(
        project=project,
        title='Трещина в стене',
        description='Обнаружена трещина в несущей стене.',
        priority=Defect.Priority.HIGH,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 6, 1),
        executor=engineer,
    )
