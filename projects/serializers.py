from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, ProjectMembership
from workspaces.models import Membership

User = get_user_model()


class ProjectMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = ProjectMembership
        fields = ['id', 'email', 'full_name', 'avatar', 'joined_at']


class ProjectSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    members_count = serializers.SerializerMethodField()
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'status',
            'workspace', 'workspace_name',
            'created_by_email', 'members_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by_email', 'created_at', 'updated_at']

    def get_members_count(self, obj):
        return obj.project_memberships.count()

    def validate_workspace(self, value):
        request = self.context['request']
        # must be workspace admin or owner to create project
        if not Membership.objects.filter(
            workspace=value,
            user=request.user,
            role__in=['owner', 'admin']
        ).exists():
            raise serializers.ValidationError("You must be an admin or owner to create projects.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        project = Project.objects.create(created_by=user, **validated_data)
        # auto add creator as project member
        ProjectMembership.objects.create(user=user, project=project)
        return project


class AddProjectMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email.")
        return value

    def validate(self, attrs):
        request = self.context['request']
        project = self.context['project']
        user = User.objects.get(email=attrs['email'])

        # user must be a workspace member first
        if not Membership.objects.filter(
            workspace=project.workspace,
            user=user
        ).exists():
            raise serializers.ValidationError(
                "User must be a workspace member before being added to a project."
            )

        # check not already a project member
        if ProjectMembership.objects.filter(project=project, user=user).exists():
            raise serializers.ValidationError("User is already a member of this project.")

        attrs['user'] = user
        return attrs