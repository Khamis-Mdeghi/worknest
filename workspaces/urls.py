from django.urls import path
from .views import (
    WorkspaceListCreateView,
    WorkspaceDetailView,
    WorkspaceMembersView,
    WorkspaceMemberDetailView
)

urlpatterns = [
    path('', WorkspaceListCreateView.as_view(), name='workspace-list-create'),
    path('<uuid:pk>/', WorkspaceDetailView.as_view(), name='workspace-detail'),
    path('<uuid:pk>/members/', WorkspaceMembersView.as_view(), name='workspace-members'),
    path('<uuid:pk>/members/<int:membership_id>/', WorkspaceMemberDetailView.as_view(), name='workspace-member-detail'),
]