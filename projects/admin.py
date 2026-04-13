from django.contrib import admin
from .models import Project, ProjectMembership

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'workspace', 'status', 'created_by', 'created_at']
    list_filter = ['status']
    search_fields = ['name', 'workspace__name']

@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'project', 'joined_at']
