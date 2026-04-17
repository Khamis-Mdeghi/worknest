from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from notifications.utils import send_notification, notify_workspace_members
from notifications.models import Notification

from .models import Workspace, Membership
from .serializers import (
    WorkspaceSerializer, MemberSerializer,
    InviteMemberSerializer, UpdateMemberRoleSerializer
)
from .permissions import IsWorkspaceOwner, IsWorkspaceAdminOrOwner, IsWorkspaceMember

User = get_user_model()


class WorkspaceListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # only return workspaces the user belongs to
        workspaces = Workspace.objects.filter(members=request.user)
        serializer = WorkspaceSerializer(workspaces, many=True)
        return Response(serializer.data)

    def post(self, request):
        # check workspace limit based on plan
        subscription = getattr(request.user, 'subscription', None)
        plan_limit = subscription.limits['workspaces'] if subscription else 1
        
        if plan_limit != -1:  # -1 means unlimited
            current_count = request.user.owned_workspaces.count()
        if current_count >= plan_limit:
            return Response(
                {"detail": f"Your {subscription.plan} plan allows {plan_limit} workspace(s). Upgrade to create more."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = WorkspaceSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceDetailView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_object(self, pk, request):
        workspace = get_object_or_404(Workspace, pk=pk)
        self.check_object_permissions(request, workspace)
        return workspace

    def get(self, request, pk):
        workspace = self.get_object(pk, request)
        serializer = WorkspaceSerializer(workspace)
        return Response(serializer.data)

    def patch(self, request, pk):
        workspace = self.get_object(pk, request)
        self.check_object_permissions(request, workspace)
        # only owner or admin can update
        if not Membership.objects.filter(
            workspace=workspace, user=request.user,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN]
        ).exists():
            return Response({"detail": "You don't have permission to update this workspace."}, status=status.HTTP_403_FORBIDDEN)
        serializer = WorkspaceSerializer(workspace, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        workspace = self.get_object(pk, request)
        # only owner can delete
        if workspace.owner != request.user:
            return Response({"detail": "Only the owner can delete this workspace."}, status=status.HTTP_403_FORBIDDEN)
        workspace.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkspaceMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        workspace = get_object_or_404(Workspace, pk=pk)
        # must be a member to see members
        if not Membership.objects.filter(workspace=workspace, user=request.user).exists():
            return Response({"detail": "You are not a member of this workspace."}, status=status.HTTP_403_FORBIDDEN)
        memberships = workspace.memberships.select_related('user')
        serializer = MemberSerializer(memberships, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        workspace = get_object_or_404(Workspace, pk=pk)
        # only owner or admin can invite
        if not Membership.objects.filter(
            workspace=workspace, user=request.user,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN]
        ).exists():
            return Response({"detail": "You don't have permission to invite members."}, status=status.HTTP_403_FORBIDDEN)

        serializer = InviteMemberSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.get(email=serializer.validated_data['email'])
            if Membership.objects.filter(workspace=workspace, user=user).exists():
                return Response({"detail": "User is already a member."}, status=status.HTTP_400_BAD_REQUEST)
            membership = Membership.objects.create(
                user=user,
                workspace=workspace,
                role=serializer.validated_data['role']
            )
            send_notification(
                recipient=user,
                sender=request.user,
                notification_type=Notification.Type.MEMBER_JOINED,
                title='You were added to a workspace',
                message=f'{request.user.full_name} added you to {workspace.name}',
                workspace=workspace
            )
            return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkspaceMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk, membership_id):
        workspace = get_object_or_404(Workspace, pk=pk)
        membership = get_object_or_404(Membership, pk=membership_id, workspace=workspace)
        # only owner can change roles
        if workspace.owner != request.user:
            return Response({"detail": "Only the owner can change member roles."}, status=status.HTTP_403_FORBIDDEN)
        serializer = UpdateMemberRoleSerializer(membership, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, membership_id):
        workspace = get_object_or_404(Workspace, pk=pk)
        membership = get_object_or_404(Membership, pk=membership_id, workspace=workspace)
        # owner can remove anyone, members can remove themselves
        if workspace.owner != request.user and membership.user != request.user:
            return Response({"detail": "You don't have permission to remove this member."}, status=status.HTTP_403_FORBIDDEN)
        # prevent owner from removing themselves
        if membership.user == workspace.owner:
            return Response({"detail": "Owner cannot be removed."}, status=status.HTTP_400_BAD_REQUEST)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)