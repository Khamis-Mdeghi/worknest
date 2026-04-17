from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .serializers import NotificationSerializer


def send_notification(recipient, sender, notification_type, title, message, workspace=None, project=None):
    """Create notification in DB and push it via WebSocket"""

    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        title=title,
        message=message,
        workspace=workspace,
        project=project
    )

    # push to websocket
    channel_layer = get_channel_layer()
    group_name = f'notifications_{recipient.id}'

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'send_notification',
            'data': NotificationSerializer(notification).data
        }
    )

    return notification


def notify_workspace_members(workspace, sender, notification_type, title, message, exclude_user=None):
    """Send notification to all workspace members"""
    memberships = workspace.memberships.select_related('user').all()

    for membership in memberships:
        if exclude_user and membership.user == exclude_user:
            continue
        send_notification(
            recipient=membership.user,
            sender=sender,
            notification_type=notification_type,
            title=title,
            message=message,
            workspace=workspace
        )