from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import File
from .serializers import FileSerializer
from projects.models import Project, ProjectMembership
from workspaces.models import Membership


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


class FileListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # needed for file uploads

    def get(self, request, workspace_pk, project_pk):
        project = get_object_or_404(Project, pk=project_pk, workspace__pk=workspace_pk)

        if not is_project_member(request.user, project) and \
           not is_workspace_admin_or_owner(request.user, project.workspace):
            return Response(
                {"detail": "You don't have access to this project."},
                status=status.HTTP_403_FORBIDDEN
            )

        # filter by file type if provided
        file_type = request.query_params.get('type', None)
        files = File.objects.filter(project=project)
        if file_type:
            files = files.filter(file_type=file_type)

        serializer = FileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, workspace_pk, project_pk):
        project = get_object_or_404(Project, pk=project_pk, workspace__pk=workspace_pk)

        if not is_project_member(request.user, project) and \
           not is_workspace_admin_or_owner(request.user, project.workspace):
            return Response(
                {"detail": "You don't have access to this project."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = FileSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(project=project, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, workspace_pk, project_pk):
        return get_object_or_404(
            File,
            pk=pk,
            project__pk=project_pk,
            project__workspace__pk=workspace_pk
        )

    def get(self, request, workspace_pk, project_pk, pk):
        file = self.get_object(pk, workspace_pk, project_pk)

        if not is_project_member(request.user, file.project) and \
           not is_workspace_admin_or_owner(request.user, file.project.workspace):
            return Response(
                {"detail": "You don't have access to this file."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = FileSerializer(file, context={'request': request})
        return Response(serializer.data)

    def delete(self, request, workspace_pk, project_pk, pk):
        file = self.get_object(pk, workspace_pk, project_pk)

        # only uploader or admin/owner can delete
        if file.uploaded_by != request.user and \
           not is_workspace_admin_or_owner(request.user, file.project.workspace):
            return Response(
                {"detail": "You don't have permission to delete this file."},
                status=status.HTTP_403_FORBIDDEN
            )

        file.file.delete(save=False)  # delete from storage
        file.delete()  # delete from database
        return Response(status=status.HTTP_204_NO_CONTENT)
