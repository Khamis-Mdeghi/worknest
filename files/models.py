from django.db import models
from django.conf import settings
import uuid
import os


def file_upload_path(instance, filename):
    # files/workspace_id/project_id/filename
    return f'files/{instance.project.workspace.id}/{instance.project.id}/{filename}'


class File(models.Model):
    class FileType(models.TextChoices):
        IMAGE = 'image', 'Image'
        DOCUMENT = 'document', 'Document'
        VIDEO = 'video', 'Video'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=file_upload_path)
    file_type = models.CharField(max_length=20, choices=FileType.choices, default=FileType.OTHER)
    file_size = models.PositiveBigIntegerField(help_text='File size in bytes')
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='files'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_files'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.project.name})'

    @property
    def file_size_display(self):
        """Human readable file size"""
        size = self.file_size
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        else:
            return f'{size / (1024 * 1024):.1f} MB'

    def get_file_type(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        document_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt']
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']

        if ext in image_extensions:
            return self.FileType.IMAGE
        elif ext in document_extensions:
            return self.FileType.DOCUMENT
        elif ext in video_extensions:
            return self.FileType.VIDEO
        return self.FileType.OTHER
