from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Workspace, Membership

User = get_user_model()


class MemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = Membership
        fields = ['id', 'email', 'full_name', 'avatar', 'role', 'joined_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'logo', 'owner_email', 'members_count', 'created_at']
        read_only_fields = ['id', 'owner_email', 'created_at']

    def get_members_count(self, obj):
        return obj.memberships.count()

    def create(self, validated_data):
        user = self.context['request'].user
        workspace = Workspace.objects.create(owner=user, **validated_data)
        # auto add owner as member with owner role
        Membership.objects.create(
            user=user,
            workspace=workspace,
            role=Membership.Role.OWNER
        )
        return workspace


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=['admin', 'member'], default='member')

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email")
        return value


class UpdateMemberRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ['role']