from django.urls import path
from .views import (
    ProjectListCreateView,
    ProjectDetailView,
    ProjectMembersView,
    ProjectMemberDetailView
)

urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project-list-create'),
    path('<uuid:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('<uuid:pk>/members/', ProjectMembersView.as_view(), name='project-members'),
    path('<uuid:pk>/members/<int:membership_id>/', ProjectMemberDetailView.as_view(), name='project-member-detail'),
]