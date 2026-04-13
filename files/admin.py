from django.contrib import admin
from .models import File

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['name', 'file_type', 'file_size_display', 'project', 'uploaded_by', 'created_at']
    list_filter = ['file_type']
    search_fields = ['name', 'project__name']
