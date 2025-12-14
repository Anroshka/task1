from django.contrib import admin

from .models import Attachment, Comment, Defect, DefectHistory, Project, ProjectStage


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'address', 'start_date', 'end_date')
	search_fields = ('name', 'address')


@admin.register(ProjectStage)
class ProjectStageAdmin(admin.ModelAdmin):
	list_display = ('project', 'name', 'order', 'start_date', 'end_date')
	list_filter = ('project',)
	search_fields = ('name', 'project__name')


class AttachmentInline(admin.TabularInline):
	model = Attachment
	extra = 0


class CommentInline(admin.TabularInline):
	model = Comment
	extra = 0


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
	list_display = ('title', 'project', 'priority', 'status', 'executor', 'deadline', 'created_at')
	list_filter = ('status', 'priority', 'project')
	search_fields = ('title', 'description')
	autocomplete_fields = ('executor',)
	inlines = (AttachmentInline, CommentInline)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
	list_display = ('defect', 'file', 'uploaded_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
	list_display = ('defect', 'author', 'created_at')
	search_fields = ('text',)


@admin.register(DefectHistory)
class DefectHistoryAdmin(admin.ModelAdmin):
	list_display = ('defect', 'action', 'changed_by', 'created_at')
	list_filter = ('action', 'created_at')
	search_fields = ('defect__title', 'changed_by__username')
