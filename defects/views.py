from __future__ import annotations

import csv
import io

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from openpyxl import Workbook

from .forms import AttachmentForm, CommentForm, DefectForm, ProjectStageForm
from .models import Defect, Project, ProjectStage
from .permissions import is_customer, is_engineer, is_manager
from .services import log_defect_event


User = get_user_model()


class RoleQuerysetMixin:
	"""Ограничение queryset в зависимости от роли пользователя."""

	def filter_defects_for_user(self, queryset):
		user = self.request.user
		if is_manager(user) or is_customer(user):
			return queryset
		if is_engineer(user):
			return queryset.filter(executor=user)
		return queryset.none()

	def filter_projects_for_user(self, queryset):
		user = self.request.user
		# Проекты доступны для просмотра всем аутентифицированным ролям.
		# Ограничения на CRUD остаются в соответствующих CBV (manager-only).
		if user.is_authenticated:
			return queryset
		return queryset.none()


class DashboardView(LoginRequiredMixin, RoleQuerysetMixin, ListView):
	template_name = 'defects/dashboard.html'
	model = Defect
	context_object_name = 'defects'
	paginate_by = 20

	def get_queryset(self):
		qs = Defect.objects.select_related('project', 'executor').all()
		qs = self.filter_defects_for_user(qs)

		status = self.request.GET.get('status')
		priority = self.request.GET.get('priority')
		executor = self.request.GET.get('executor')
		query = (self.request.GET.get('q') or '').strip()
		sort = (self.request.GET.get('sort') or '-created_at').strip()

		if status:
			qs = qs.filter(status=status)
		if priority:
			qs = qs.filter(priority=priority)
		# Инженер не может фильтровать по чужому исполнителю
		if executor and is_manager(self.request.user):
			qs = qs.filter(executor_id=executor)
		if query:
			qs = qs.filter(
				Q(title__icontains=query)
				| Q(description__icontains=query)
				| Q(project__name__icontains=query)
				| Q(project__address__icontains=query)
			)

		allowed_sorts = {
			'created_at',
			'-created_at',
			'deadline',
			'-deadline',
			'priority',
			'-priority',
			'status',
			'-status',
		}
		if sort not in allowed_sorts:
			sort = '-created_at'
		qs = qs.order_by(sort)

		return qs

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		ctx['statuses'] = Defect.Status.choices
		ctx['priorities'] = Defect.Priority.choices
		ctx['executors'] = User.objects.filter(is_active=True).order_by('username')
		ctx['filters'] = {
			'status': self.request.GET.get('status', ''),
			'priority': self.request.GET.get('priority', ''),
			'executor': self.request.GET.get('executor', ''),
			'q': self.request.GET.get('q', ''),
			'sort': self.request.GET.get('sort', '-created_at'),
		}
		return ctx


class DefectDetailView(LoginRequiredMixin, RoleQuerysetMixin, DetailView):
	template_name = 'defects/defect_detail.html'
	model = Defect
	context_object_name = 'defect'

	def get_queryset(self):
		qs = Defect.objects.select_related('project', 'executor').prefetch_related(
			'attachments',
			'comments__author',
			'history__changed_by',
		)
		return self.filter_defects_for_user(qs)

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		ctx['comment_form'] = CommentForm()
		ctx['attachment_form'] = AttachmentForm()
		ctx['next_statuses'] = self.object.allowed_next_statuses_for(self.request.user)
		ctx['can_edit'] = self.object.can_edit(self.request.user)
		ctx['can_upload'] = ctx['can_edit'] or is_manager(self.request.user)
		ctx['can_delete'] = is_manager(self.request.user)
		ctx['history'] = self.object.history.all()
		return ctx


class DefectCreateView(CreateView):
	template_name = 'defects/defect_form.html'
	model = Defect
	form_class = DefectForm

	def dispatch(self, request, *args, **kwargs):
		if not request.user.is_authenticated:
			return redirect('login')
		if is_customer(request.user):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		# Инженер создаёт дефекты только на себя (исполнитель = текущий пользователь)
		if is_engineer(self.request.user):
			form.fields.pop('executor', None)
		return form

	def form_valid(self, form):
		defect: Defect = form.save(commit=False)
		if is_engineer(self.request.user):
			defect.executor = self.request.user
		defect.full_clean()
		defect.save()
		log_defect_event(
			defect=defect,
			user=self.request.user,
			action='created',
			changes={
				'title': {'to': defect.title},
				'project': {'to': getattr(defect.project, 'name', '')},
				'priority': {'to': defect.get_priority_display()},
				'status': {'to': defect.get_status_display()},
				'deadline': {'to': defect.deadline.isoformat() if defect.deadline else ''},
				'executor': {'to': getattr(defect.executor, 'username', '')},
			},
		)
		messages.success(self.request, 'Дефект создан.')
		return redirect('defect_detail', pk=defect.pk)


class DefectUpdateView(RoleQuerysetMixin, UpdateView):
	template_name = 'defects/defect_form.html'
	model = Defect
	form_class = DefectForm

	def get_queryset(self):
		qs = Defect.objects.select_related('project', 'executor')
		return self.filter_defects_for_user(qs)

	def dispatch(self, request, *args, **kwargs):
		response = super().dispatch(request, *args, **kwargs)
		if hasattr(self, 'object') and self.object and not self.object.can_edit(request.user):
			raise PermissionDenied
		return response

	def get_form(self, form_class=None):
		form = super().get_form(form_class)
		# Инженер не может переназначать исполнителя
		if is_engineer(self.request.user):
			form.fields.pop('executor', None)
		return form

	def form_valid(self, form):
		old = Defect.objects.select_related('project', 'executor').get(pk=self.get_object().pk)
		defect: Defect = form.save(commit=False)
		if is_engineer(self.request.user):
			# На всякий случай фиксируем, что инженер не меняет исполнителя
			defect.executor = self.request.user
		defect.full_clean()
		defect.save()

		changes = {}
		pairs = [
			('title', old.title, defect.title),
			('description', old.description, defect.description),
			('priority', old.get_priority_display(), defect.get_priority_display()),
			('deadline', old.deadline.isoformat() if old.deadline else '', defect.deadline.isoformat() if defect.deadline else ''),
			('project', getattr(old.project, 'name', ''), getattr(defect.project, 'name', '')),
			('executor', getattr(old.executor, 'username', ''), getattr(defect.executor, 'username', '')),
		]
		for field, before, after in pairs:
			if before != after:
				changes[field] = {'from': before, 'to': after}
		if changes:
			log_defect_event(defect=defect, user=self.request.user, action='updated', changes=changes)

		messages.success(self.request, 'Дефект обновлён.')
		return redirect('defect_detail', pk=defect.pk)


class DefectDeleteView(DeleteView):
	template_name = 'defects/confirm_delete.html'
	model = Defect
	success_url = reverse_lazy('dashboard')

	def dispatch(self, request, *args, **kwargs):
		if not is_manager(request.user):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)


class ProjectListView(LoginRequiredMixin, RoleQuerysetMixin, ListView):
	template_name = 'projects/project_list.html'
	model = Project
	context_object_name = 'projects'

	def get_queryset(self):
		qs = Project.objects.all().order_by('-start_date', 'name')
		return self.filter_projects_for_user(qs)


class ProjectDetailView(LoginRequiredMixin, RoleQuerysetMixin, DetailView):
	template_name = 'projects/project_detail.html'
	model = Project
	context_object_name = 'project'

	def get_queryset(self):
		qs = Project.objects.all()
		return self.filter_projects_for_user(qs)

	def get_context_data(self, **kwargs):
		ctx = super().get_context_data(**kwargs)
		# Показываем дефекты проекта с учётом роли
		defects_qs = Defect.objects.select_related('executor', 'project').filter(project=self.object)
		ctx['defects'] = self.filter_defects_for_user(defects_qs)
		ctx['stages'] = self.object.stages.all()
		return ctx


class ProjectStageCreateView(CreateView):
	template_name = 'projects/project_stage_form.html'
	model = ProjectStage
	form_class = ProjectStageForm

	def dispatch(self, request, *args, **kwargs):
		if not is_manager(request.user):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)

	def get_project(self) -> Project:
		return get_object_or_404(Project, pk=self.kwargs['project_pk'])

	def form_valid(self, form):
		stage: ProjectStage = form.save(commit=False)
		stage.project = self.get_project()
		stage.save()
		messages.success(self.request, 'Этап проекта добавлен.')
		return redirect('project_detail', pk=stage.project_id)


class ProjectStageUpdateView(ProjectStageCreateView, UpdateView):
	def get_queryset(self):
		return ProjectStage.objects.select_related('project')

	def get_project(self) -> Project:
		stage = self.get_object()
		return stage.project


class ProjectStageDeleteView(DeleteView):
	template_name = 'defects/confirm_delete.html'
	model = ProjectStage

	def dispatch(self, request, *args, **kwargs):
		if not is_manager(request.user):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)

	def get_success_url(self):
		return reverse('project_detail', kwargs={'pk': self.object.project_id})


class ProjectCreateView(CreateView):
	template_name = 'projects/project_form.html'
	model = Project
	fields = ('name', 'address', 'start_date', 'end_date')

	def dispatch(self, request, *args, **kwargs):
		if not is_manager(request.user):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)

	def get_success_url(self):
		return reverse('project_detail', kwargs={'pk': self.object.pk})


class ProjectUpdateView(ProjectCreateView, UpdateView):
	pass


class ProjectDeleteView(DeleteView):
	template_name = 'defects/confirm_delete.html'
	model = Project
	success_url = reverse_lazy('project_list')

	def dispatch(self, request, *args, **kwargs):
		if not is_manager(request.user):
			raise PermissionDenied
		return super().dispatch(request, *args, **kwargs)


@login_required
@require_POST
def defect_change_status(request: HttpRequest, pk: int) -> HttpResponse:
	defect = get_object_or_404(Defect.objects.select_related('executor', 'project'), pk=pk)
	if not defect.can_view(request.user):
		raise PermissionDenied

	old_status = defect.get_status_display()

	new_status = request.POST.get('status')
	if not new_status:
		raise PermissionDenied

	if new_status not in defect.allowed_next_statuses_for(request.user):
		raise PermissionDenied

	defect.status = new_status
	defect.full_clean()
	defect.save(update_fields=['status', 'updated_at'])
	log_defect_event(
		defect=defect,
		user=request.user,
		action='status_changed',
		changes={'status': {'from': old_status, 'to': defect.get_status_display()}},
	)
	messages.success(request, 'Статус обновлён.')
	return redirect('defect_detail', pk=defect.pk)


@login_required
@require_POST
def defect_add_comment(request: HttpRequest, pk: int) -> HttpResponse:
	defect = get_object_or_404(Defect, pk=pk)
	if not defect.can_view(request.user):
		raise PermissionDenied

	form = CommentForm(request.POST)
	if form.is_valid():
		comment = form.save(commit=False)
		comment.defect = defect
		comment.author = request.user
		comment.save()
		log_defect_event(
			defect=defect,
			user=request.user,
			action='comment_added',
			changes={'comment': {'to': comment.text}},
		)
		messages.success(request, 'Комментарий добавлен.')
	else:
		messages.error(request, 'Не удалось добавить комментарий.')
	return redirect('defect_detail', pk=defect.pk)


@login_required
@require_POST
def defect_add_attachment(request: HttpRequest, pk: int) -> HttpResponse:
	defect = get_object_or_404(Defect, pk=pk)
	if not defect.can_edit(request.user) and not is_manager(request.user):
		raise PermissionDenied

	form = AttachmentForm(request.POST, request.FILES)
	if form.is_valid():
		attachment = form.save(commit=False)
		attachment.defect = defect
		attachment.save()
		log_defect_event(
			defect=defect,
			user=request.user,
			action='attachment_added',
			changes={'file': {'to': attachment.file.name}},
		)
		messages.success(request, 'Вложение загружено.')
	else:
		messages.error(request, 'Не удалось загрузить файл.')
	return redirect('defect_detail', pk=defect.pk)


@login_required
def export_defects_csv(request: HttpRequest) -> HttpResponse:
	qs = Defect.objects.select_related('project', 'executor')
	if is_engineer(request.user):
		qs = qs.filter(executor=request.user)

	response = HttpResponse(content_type='text/csv; charset=utf-8')
	response['Content-Disposition'] = 'attachment; filename="defects.csv"'
	response.write('\ufeff')

	writer = csv.writer(response, delimiter=';')
	writer.writerow(['ID', 'Проект', 'Заголовок', 'Приоритет', 'Статус', 'Исполнитель', 'Deadline', 'Создано'])
	for d in qs.order_by('-created_at'):
		writer.writerow(
			[
				d.pk,
				d.project.name,
				d.title,
				d.get_priority_display(),
				d.get_status_display(),
				getattr(d.executor, 'username', ''),
				d.deadline.isoformat(),
				d.created_at.strftime('%Y-%m-%d %H:%M'),
			]
		)

	return response


@login_required
def export_defects_xlsx(request: HttpRequest) -> HttpResponse:
	qs = Defect.objects.select_related('project', 'executor')
	if is_engineer(request.user):
		qs = qs.filter(executor=request.user)

	wb = Workbook()
	ws = wb.active
	ws.title = 'Defects'

	ws.append(['ID', 'Проект', 'Заголовок', 'Описание', 'Приоритет', 'Статус', 'Исполнитель', 'Deadline', 'Создано'])
	for d in qs.order_by('-created_at'):
		ws.append(
			[
				d.pk,
				d.project.name,
				d.title,
				d.description,
				d.get_priority_display(),
				d.get_status_display(),
				getattr(d.executor, 'username', ''),
				d.deadline.isoformat(),
				d.created_at.strftime('%Y-%m-%d %H:%M'),
			]
		)

	bio = io.BytesIO()
	wb.save(bio)
	bio.seek(0)

	response = HttpResponse(
		bio.getvalue(),
		content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
	)
	response['Content-Disposition'] = 'attachment; filename="defects.xlsx"'
	return response


@login_required
def analytics_view(request: HttpRequest) -> HttpResponse:
	# Аналитика доступна менеджеру и руководителю
	if not (is_manager(request.user) or is_customer(request.user)):
		raise PermissionDenied

	stats = (
		Defect.objects.values('status')
		.annotate(total=Count('id'))
		.order_by('status')
	)
	# Преобразуем в удобный вид для шаблона
	by_status = {row['status']: row['total'] for row in stats}
	status_labels = [label for _, label in Defect.Status.choices]
	status_keys = [key for key, _ in Defect.Status.choices]
	status_values = [by_status.get(key, 0) for key in status_keys]

	return render(
		request,
		'defects/analytics.html',
		{
			'status_labels': status_labels,
			'status_values': status_values,
			'rows': [(label, by_status.get(key, 0)) for key, label in Defect.Status.choices],
		},
	)


def safe_redirect_to_next(request: HttpRequest, default_name: str = 'dashboard') -> HttpResponse:
	"""Безопасный редирект на next (если передан), иначе на default."""

	nxt = request.GET.get('next') or request.POST.get('next')
	if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
		return redirect(nxt)
	return redirect(default_name)
