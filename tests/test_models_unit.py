import datetime as dt

import pytest
from django.core.exceptions import ValidationError

from defects.models import Defect, Project


@pytest.mark.django_db
def test_defect_str_contains_title_and_status(defect):
    s = str(defect)
    assert defect.title in s
    assert defect.get_status_display() in s


@pytest.mark.django_db
def test_project_str_is_name(project):
    assert str(project) == project.name


@pytest.mark.django_db
def test_deadline_validation_not_after_project_end(engineer):
    project = Project.objects.create(
        name='Проект A',
        address='Адрес',
        start_date=dt.date(2025, 1, 1),
        end_date=dt.date(2025, 2, 1),
    )
    defect = Defect(
        project=project,
        title='Test',
        description='Desc',
        priority=Defect.Priority.LOW,
        status=Defect.Status.NEW,
        deadline=dt.date(2025, 3, 1),
        executor=engineer,
    )
    with pytest.raises(ValidationError):
        defect.full_clean()


@pytest.mark.django_db
def test_workflow_transitions_basic():
    transitions = Defect.workflow_transitions()
    assert Defect.Status.IN_PROGRESS in transitions[Defect.Status.NEW]
    assert Defect.Status.CANCELLED in transitions[Defect.Status.NEW]
    assert transitions[Defect.Status.CLOSED] == set()


@pytest.mark.django_db
def test_engineer_can_view_only_own(engineer, manager, defect):
    assert defect.can_view(engineer) is True
    assert defect.can_view(manager) is True


@pytest.mark.django_db
def test_allowed_next_statuses_for_engineer(defect, engineer):
    nxt = defect.allowed_next_statuses_for(engineer)
    # Из NEW инженер может перевести только в IN_PROGRESS
    assert nxt == [Defect.Status.IN_PROGRESS]


@pytest.mark.django_db
def test_allowed_next_statuses_for_customer(defect, customer):
    assert defect.allowed_next_statuses_for(customer) == []
