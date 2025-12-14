from django.urls import path

from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Проекты
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/edit/', views.ProjectUpdateView.as_view(), name='project_edit'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),

    # Этапы проекта
    path('projects/<int:project_pk>/stages/create/', views.ProjectStageCreateView.as_view(), name='project_stage_create'),
    path('project-stages/<int:pk>/edit/', views.ProjectStageUpdateView.as_view(), name='project_stage_edit'),
    path('project-stages/<int:pk>/delete/', views.ProjectStageDeleteView.as_view(), name='project_stage_delete'),

    # Дефекты
    path('defects/create/', views.DefectCreateView.as_view(), name='defect_create'),
    path('defects/<int:pk>/', views.DefectDetailView.as_view(), name='defect_detail'),
    path('defects/<int:pk>/edit/', views.DefectUpdateView.as_view(), name='defect_edit'),
    path('defects/<int:pk>/delete/', views.DefectDeleteView.as_view(), name='defect_delete'),

    # Действия по дефекту
    path('defects/<int:pk>/status/', views.defect_change_status, name='defect_change_status'),
    path('defects/<int:pk>/comment/', views.defect_add_comment, name='defect_add_comment'),
    path('defects/<int:pk>/attachment/', views.defect_add_attachment, name='defect_add_attachment'),

    # Отчётность
    path('export/defects.csv', views.export_defects_csv, name='export_defects_csv'),
    path('export/defects.xlsx', views.export_defects_xlsx, name='export_defects_xlsx'),
    path('analytics/', views.analytics_view, name='analytics'),
]
