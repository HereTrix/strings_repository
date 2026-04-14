from rest_framework import serializers

from api.models.project import Project, ProjectAccessToken, ProjectRole
from api.serializers.language import LanguageSerializer
from api.models.transport_models import APIProject


class CreateProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['name', 'description']


class APIProjectSerializer(serializers.ModelSerializer):
    languages = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='code'
    )

    class Meta:
        model = APIProject
        fields = ['id', 'name', 'description', 'languages']


class ProjectParticipantsSerializer:

    def serialize(roles, user):
        user_role = [role for role in roles if role.user == user][0]
        can_edit = user_role.role == ProjectRole.Role.admin or user_role.role == ProjectRole.Role.owner

        users = [
            {
                'can_edit': can_edit and (user_role.role == ProjectRole.Role.owner or (not role.user.id == user.id and not role.role == ProjectRole.Role.owner)),
                'id': role.user.id,
                'first_name': role.user.first_name,
                'last_name': role.user.last_name,
                'email': role.user.email,
                'role': role.role
            } for role in roles]

        return users


class ProjectSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'role']

    def get_role(self, obj):
        user = self.context.get('user')
        print(user)
        if not user:
            return None
        role_obj = obj.roles.filter(user=user).first()
        return role_obj.role if role_obj else None


class ProjectAccessTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAccessToken
        fields = ['token', 'permission', 'expiration']


class ProjectDetailSerializer(serializers.ModelSerializer):
    languages = LanguageSerializer(many=True, read_only=True)
    role = serializers.SerializerMethodField()

    def get_role(self, obj):
        user = self.context['request'].user
        role = obj.roles.get(user=user)
        return role.role

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'languages', 'role']
