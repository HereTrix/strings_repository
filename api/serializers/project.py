from rest_framework import serializers

from api.models.project import Project, ProjectAccessToken, ProjectRole, TranslationIntegration, ProjectAIProvider
from api.serializers.language import LanguageSerializer
from api.models.transport_models import APIProject


class CreateProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['name', 'description', 'require_2fa']


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
        fields = ['id', 'name', 'description', 'role', 'require_2fa']

    def get_role(self, obj):
        user = self.context.get('user')
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
    has_ai_provider = serializers.SerializerMethodField()
    has_glossary_terms = serializers.SerializerMethodField()

    def get_has_ai_provider(self, obj):
        return ProjectAIProvider.objects.filter(project=obj).exists()

    def get_has_glossary_terms(self, obj):
        from api.models.glossary import GlossaryTerm
        return GlossaryTerm.objects.filter(project=obj).exists()

    def get_role(self, obj):
        user = self.context['request'].user
        role = obj.roles.get(user=user)
        return role.role

    def validate_require_2fa(self, value):
        request = self.context.get('request')
        if request and self.instance:
            try:
                role = self.instance.roles.get(user=request.user)
            except Exception:
                raise serializers.ValidationError("Not allowed.")
            if role.role != ProjectRole.Role.owner:
                raise serializers.ValidationError(
                    "Only project owners can change the 2FA requirement."
                )
        return value

    def validate_description(self, value):
        request = self.context.get('request')
        if request and self.instance:
            try:
                role = self.instance.roles.get(user=request.user)
            except Exception:
                raise serializers.ValidationError("Not allowed.")
            if role.role not in [ProjectRole.Role.owner, ProjectRole.Role.admin]:
                raise serializers.ValidationError(
                    "Only project admins and owners can change the description."
                )
        return value

    class Meta:
        model = Project
        fields = ['id', 'name', 'description',
                  'languages', 'role', 'require_2fa', 'has_ai_provider', 'has_glossary_terms']


class IntegrationSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(write_only=True)

    class Meta:
        model = TranslationIntegration
        fields = ['provider', 'api_key', 'endpoint_url',
                  'payload_template', 'response_path', 'auth_header']
