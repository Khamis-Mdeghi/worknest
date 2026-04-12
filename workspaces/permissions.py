from rest_framework.permissions import BasePermission
from .models import Membership


class IsWorkspaceOwner(BasePermission):
    """Only workspace owner can perform this action"""
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsWorkspaceAdminOrOwner(BasePermission):
    """Only owner or admin can perform this action"""
    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(
            workspace=obj,
            user=request.user,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN]
        ).exists()


class IsWorkspaceMember(BasePermission):
    """Any workspace member can perform this action"""
    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(
            workspace=obj,
            user=request.user
        ).exists()
