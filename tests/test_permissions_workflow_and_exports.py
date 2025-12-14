import datetime as dt

import pytest
from django.urls import reverse

from defects.models import Defect, Project
from defects.models import DefectHistory
from users.models import User


@pytest.mark.django_db
def test_engineer_does_not_see_other_engineer_defects_on_dashboard(client, engineer, manager, project):
    other = User.objects.create_user(username='eng2', password='pass', role=User.Role.ENGINEER)

    Defect.objects.create(
        project=project,
        title='Мой дефект',
        description='...',
        priority=Defect.Priority.LOW,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 1),
        executor=engineer,
    )
    Defect.objects.create(
        project=project,
        title='Чужой дефект',
        description='...',
        priority=Defect.Priority.LOW,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 2),
        executor=other,
    )

    client.force_login(engineer)
    resp = client.get(reverse('dashboard'))
    body = resp.content.decode('utf-8')
    assert 'Мой дефект' in body
    assert 'Чужой дефект' not in body


@pytest.mark.django_db
def test_engineer_cannot_open_other_engineer_defect_detail(client, engineer, project):
    other = User.objects.create_user(username='eng2', password='pass', role=User.Role.ENGINEER)
    чужой = Defect.objects.create(
        project=project,
        title='Чужой дефект',
        description='...',
        priority=Defect.Priority.MEDIUM,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 1),
        executor=other,
    )

    client.force_login(engineer)
    resp = client.get(reverse('defect_detail', kwargs={'pk': чужой.id}))
    # DetailView с queryset фильтром отдаст 404
    assert resp.status_code == 404


@pytest.mark.django_db
def test_engineer_cannot_change_status_of_other_defect(client, engineer, project):
    other = User.objects.create_user(username='eng2', password='pass', role=User.Role.ENGINEER)
    чужой = Defect.objects.create(
        project=project,
        title='Чужой дефект',
        description='...',
        priority=Defect.Priority.MEDIUM,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 1),
        executor=other,
    )

    client.force_login(engineer)
    resp = client.post(
        reverse('defect_change_status', kwargs={'pk': чужой.id}),
        data={'status': Defect.Status.IN_PROGRESS},
    )
    assert resp.status_code in (403, 404)


@pytest.mark.django_db
def test_engineer_can_move_own_defect_new_to_in_progress(client, engineer, project):
    d = Defect.objects.create(
        project=project,
        title='Мой дефект',
        description='...',
        priority=Defect.Priority.MEDIUM,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 1),
        executor=engineer,
    )

    client.force_login(engineer)
    resp = client.post(
        reverse('defect_change_status', kwargs={'pk': d.id}),
        data={'status': Defect.Status.IN_PROGRESS},
        follow=True,
    )
    assert resp.status_code == 200
    d.refresh_from_db()
    assert d.status == Defect.Status.IN_PROGRESS


@pytest.mark.django_db
def test_engineer_cannot_close_defect_even_on_review(client, engineer, project):
    d = Defect.objects.create(
        project=project,
        title='Мой дефект',
        description='...',
        priority=Defect.Priority.MEDIUM,
        status=Defect.Status.ON_REVIEW,
        deadline=dt.date(2025, 4, 1),
        executor=engineer,
    )

    client.force_login(engineer)
    resp = client.post(
        reverse('defect_change_status', kwargs={'pk': d.id}),
        data={'status': Defect.Status.CLOSED},
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_manager_can_close_defect_from_on_review(client, manager, engineer, project):
    d = Defect.objects.create(
        project=project,
        title='Дефект',
        description='...',
        priority=Defect.Priority.MEDIUM,
        status=Defect.Status.ON_REVIEW,
        deadline=dt.date(2025, 4, 1),
        executor=engineer,
    )

    client.force_login(manager)
    resp = client.post(
        reverse('defect_change_status', kwargs={'pk': d.id}),
        data={'status': Defect.Status.CLOSED},
        follow=True,
    )
    assert resp.status_code == 200
    d.refresh_from_db()
    assert d.status == Defect.Status.CLOSED


@pytest.mark.django_db
def test_csv_export_requires_login(client):
    resp = client.get(reverse('export_defects_csv'))
    assert resp.status_code == 302
    assert '/login/' in resp['Location']


@pytest.mark.django_db
def test_csv_export_scoped_for_engineer(client, engineer, project):
    other = User.objects.create_user(username='eng2', password='pass', role=User.Role.ENGINEER)

    Defect.objects.create(
        project=project,
        title='Мой дефект',
        description='...',
        priority=Defect.Priority.LOW,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 1),
        executor=engineer,
    )
    Defect.objects.create(
        project=project,
        title='Чужой дефект',
        description='...',
        priority=Defect.Priority.LOW,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 2),
        executor=other,
    )

    client.force_login(engineer)
    resp = client.get(reverse('export_defects_csv'))
    assert resp.status_code == 200

    body = resp.content.decode('utf-8', errors='ignore')
    assert 'Мой дефект' in body
    assert 'Чужой дефект' not in body


@pytest.mark.django_db
def test_xlsx_export_requires_login(client):
    resp = client.get(reverse('export_defects_xlsx'))
    assert resp.status_code == 302
    assert '/login/' in resp['Location']


@pytest.mark.django_db
def test_xlsx_export_scoped_for_engineer(client, engineer, project):
    other = User.objects.create_user(username='eng2', password='pass', role=User.Role.ENGINEER)

    Defect.objects.create(
        project=project,
        title='Мой дефект',
        description='...',
        priority=Defect.Priority.LOW,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 1),
        executor=engineer,
    )
    Defect.objects.create(
        project=project,
        title='Чужой дефект',
        description='...',
        priority=Defect.Priority.LOW,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 2),
        executor=other,
    )

    client.force_login(engineer)
    resp = client.get(reverse('export_defects_xlsx'))
    assert resp.status_code == 200
    assert resp['Content-Type'].startswith('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    # XLSX - это zip, начинается с PK
    assert resp.content[:2] == b'PK'


@pytest.mark.django_db
def test_status_change_writes_history_event(client, engineer, project):
    d = Defect.objects.create(
        project=project,
        title='Мой дефект',
        description='...',
        priority=Defect.Priority.MEDIUM,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 4, 1),
        executor=engineer,
    )

    client.force_login(engineer)
    resp = client.post(
        reverse('defect_change_status', kwargs={'pk': d.id}),
        data={'status': Defect.Status.IN_PROGRESS},
        follow=True,
    )
    assert resp.status_code == 200
    assert DefectHistory.objects.filter(defect=d, action=DefectHistory.Action.STATUS_CHANGED).exists()


@pytest.mark.django_db
def test_register_creates_engineer_role_and_logs_in(client):
    resp = client.post(
        reverse('register'),
        data={
            'username': 'newuser',
            'email': 'a@b.co',
            'password1': 'VeryStrongPass_12345',
            'password2': 'VeryStrongPass_12345',
        },
        follow=True,
    )
    assert resp.status_code == 200
    u = User.objects.get(username='newuser')
    assert u.role == User.Role.ENGINEER

    # После регистрации должен быть доступ к dashboard без редиректа на login
    dash = client.get(reverse('dashboard'))
    assert dash.status_code == 200


@pytest.mark.django_db
def test_manager_can_delete_project(client, manager):
    p = Project.objects.create(
        name='Проект на удаление',
        address='Адрес',
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 12, 31),
    )
    client.force_login(manager)

    resp_get = client.get(reverse('project_delete', kwargs={'pk': p.id}))
    assert resp_get.status_code == 200

    resp_post = client.post(reverse('project_delete', kwargs={'pk': p.id}), follow=True)
    assert resp_post.status_code == 200
    assert not Project.objects.filter(id=p.id).exists()
