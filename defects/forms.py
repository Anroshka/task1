from __future__ import annotations

from django import forms

from .models import Attachment, Comment, Defect, ProjectStage


class DefectForm(forms.ModelForm):
    """Форма создания/редактирования дефекта.

    Для инженера часть полей может быть скрыта/заполнена во view.
    """

    class Meta:
        model = Defect
        fields = (
            'project',
            'title',
            'description',
            'priority',
            'deadline',
            'executor',
        )
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ('file',)


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Введите комментарий...'}),
        }


class ProjectStageForm(forms.ModelForm):
    class Meta:
        model = ProjectStage
        fields = ('name', 'order', 'start_date', 'end_date')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
