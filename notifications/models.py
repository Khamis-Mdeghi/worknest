from django.db import models
from django.conf import settings


class Notification(models.Model):
    class Type(models.TextChoices):
        FILE_UPLOADED = 'file_uploaded', 'File Uploaded'
        MEMBER_JOINED = 'member_joined', 'Member Joined'
        MEMBER_REMOVED = 'member_removed', 'Member Removed'
        PROJECT_CREATED = 'project_created', 'Project Created'
        PROJECT_UPDATED = 'project_updated', 'Project Updated'
        ROLE_CHANGED = 'role_changed', 'Role Changed'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_notifications'
    )
    notification_type = models.CharField(max_length=50, choices=Type.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notification_type} → {self.recipient.email}'
