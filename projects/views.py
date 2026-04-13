from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import Project, ProjectMembership
from .serializers import ProjectSerializer, ProjectMemberSerializer, AddProjectMemberSerializer
from workspaces.models import Workspace, Membership


def is_workspace_admin_or_owner(user, workspace):
    return Membership.objects.filter(
        workspace=workspace,
        user=user,
        role__in=['owner', 'admin']
    ).exists()


def is_project_member(user, project):
    return ProjectMembership.objects.filter(
        project=project,
        user=user
    ).exists()


class ProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_pk):
        workspace = get_object_or_404(Workspace, pk=workspace_pk)

        # must be workspace member to view projects
        if not Membership.objects.filter(workspace=workspace, user=request.user).exists():
            return Response(
                {"detail": "You are not a member of this workspace."},
                status=status.HTTP_403_FORBIDDEN
            )

        # members only see projects they belong to
        # admins and owners see all projects
        if is_workspace_admin_or_owner(request.user, workspace):
            projects = Project.objects.filter(workspace=workspace)
        else:
            projects = Project.objects.filter(
                workspace=workspace,
                members=request.user
            )

        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)

    def post(self, request, workspace_pk):
        workspace = get_object_or_404(Workspace, pk=workspace_pk)
        data = request.data.copy()
        data['workspace'] = str(workspace_pk)
        serializer = ProjectSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            project = serializer.save()
            return Response(
                ProjectSerializer(project, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        return get_object_or_404(Project, pk=pk)

    def get(self, request, workspace_pk, pk):
        project = self.get_object(pk)

        if not is_project_member(request.user, project) and \
           not is_workspace_admin_or_owner(request.user, project.workspace):
            return Response(
                {"detail": "You don't have access to this project."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProjectSerializer(project)
        return Response(serializer.data)

    def patch(self, request, workspace_pk, pk):
        project = self.get_object(pk)

        if not is_workspace_admin_or_owner(request.user, project.workspace):
            return Response(
                {"detail": "Only admins and owners can update projects."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProjectSerializer(project, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, workspace_pk, pk):
        project = self.get_object(pk)

        if not is_workspace_admin_or_owner(request.user, project.workspace):
            return Response(
                {"detail": "Only admins and owners can delete projects."},
                status=status.HTTP_403_FORBIDDEN
            )

        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_pk, pk):
        project = get_object_or_404(Project, pk=pk)

        if not is_project_member(request.user, project) and \
           not is_workspace_admin_or_owner(request.user, project.workspace):
            return Response(
                {"detail": "You don't have access to this project."},
                status=status.HTTP_403_FORBIDDEN
            )

        memberships = project.project_memberships.select_related('user')
        serializer = ProjectMemberSerializer(memberships, many=True)
        return Response(serializer.data)

    def post(self, request, workspace_pk, pk):
        project = get_object_or_404(Project, pk=pk)

        if not is_workspace_admin_or_owner(request.user, project.workspace):
            return Response(
                {"detail": "Only admins and owners can add project members."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AddProjectMemberSerializer(
            data=request.data,
            context={'request': request, 'project': project}
        )
        if serializer.is_valid():
            membership = ProjectMembership.objects.create(
                user=serializer.validated_data['user'],
                project=project
            )
            return Response(
                ProjectMemberSerializer(membership).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectMemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, workspace_pk, pk, membership_id):
        project = get_object_or_404(Project, pk=pk)
        membership = get_object_or_404(ProjectMembership, pk=membership_id, project=project)

        # admin/owner can remove anyone, members can remove themselves
        if not is_workspace_admin_or_owner(request.user, project.workspace) and \
           membership.user != request.user:
            return Response(
                {"detail": "You don't have permission to remove this member."},
                status=status.HTTP_403_FORBIDDEN
            )

        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
