import datetime as dt

import pytest
from django.urls import reverse

from defects.models import Defect, Project
from defects.models import ProjectStage


@pytest.mark.django_db
def test_manager_can_create_defect_via_client(client, manager, project, engineer):
    client.force_login(manager)

    resp = client.post(
        reverse('defect_create'),
        data={
            'project': project.id,
            'title': 'Неровность пола',
            'description': 'Требуется выравнивание.',
            'priority': Defect.Priority.MEDIUM,
            'deadline': dt.date(2025, 5, 1),
            'executor': engineer.id,
        },
        follow=True,
    )
    assert resp.status_code == 200
    created = Defect.objects.get(title='Неровность пола')
    assert created.executor_id == engineer.id
    assert created.status == Defect.Status.NEW


@pytest.mark.django_db
def test_engineer_create_sets_executor_to_self(client, engineer, project):
    client.force_login(engineer)

    resp = client.post(
        reverse('defect_create'),
        data={
            'project': project.id,
            'title': 'Скол плитки',
            'description': 'На лестничной площадке.',
            'priority': Defect.Priority.LOW,
            'deadline': dt.date(2025, 4, 1),
        },
        follow=True,
    )
    assert resp.status_code == 200
    created = Defect.objects.get(title='Скол плитки')
    assert created.executor_id == engineer.id


@pytest.mark.django_db
def test_engineer_cannot_delete_project(client, engineer):
    client.force_login(engineer)
    p = Project.objects.create(
        name='Запрет удаления',
        address='Адрес',
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 12, 31),
    )

    resp = client.get(reverse('project_delete', kwargs={'pk': p.id}))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_anonymous_is_redirected_to_login_for_dashboard(client):
    resp = client.get(reverse('dashboard'))
    assert resp.status_code == 302
    assert '/login/' in resp['Location']


@pytest.mark.django_db
def test_engineer_sees_projects_created_in_admin(client, engineer):
    p = Project.objects.create(
        name='Проект без дефектов',
        address='Адрес',
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 12, 31),
    )
    client.force_login(engineer)

    resp = client.get(reverse('project_list'))
    assert resp.status_code == 200
    assert 'Проект без дефектов' in resp.content.decode('utf-8')

    resp2 = client.get(reverse('project_detail', kwargs={'pk': p.id}))
    assert resp2.status_code == 200


@pytest.mark.django_db
def test_customer_can_view_projects_but_cannot_create_defect(client, customer, project):
    client.force_login(customer)

    resp = client.get(reverse('project_list'))
    assert resp.status_code == 200

    resp2 = client.get(reverse('project_detail', kwargs={'pk': project.id}))
    assert resp2.status_code == 200

    # customer не имеет прав создавать дефект
    resp3 = client.get(reverse('defect_create'))
    assert resp3.status_code == 403


@pytest.mark.django_db
def test_analytics_permissions(client, customer, engineer):
    client.force_login(customer)
    ok = client.get(reverse('analytics'))
    assert ok.status_code == 200

    client.force_login(engineer)
    forbidden = client.get(reverse('analytics'))
    assert forbidden.status_code == 403


@pytest.mark.django_db
def test_manager_can_create_project_stage(client, manager, project):
    client.force_login(manager)
    resp = client.post(
        reverse('project_stage_create', kwargs={'project_pk': project.id}),
        data={'name': 'Фундамент', 'order': 1, 'start_date': dt.date(2025, 1, 2), 'end_date': dt.date(2025, 2, 1)},
        follow=True,
    )
    assert resp.status_code == 200
    assert ProjectStage.objects.filter(project=project, name='Фундамент').exists()
