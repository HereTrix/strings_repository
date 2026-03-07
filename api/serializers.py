from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import *
from .transport_models import *
from api.languages.langcoder import Langcoder


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError('Incorrect Credentials Passed.')


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


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['code']


class StringTokenSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='tag'
    )

    class Meta:
        model = StringToken
        fields = ['id', 'token', 'comment', 'tags', 'status']


class StringTranslationSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='tag'
    )

    translation = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='translation'
    )

    class Meta:
        model = StringToken
        fields = ['token', 'tags', 'translation']


class TranslationSerializer(serializers.ModelSerializer):
    token = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field='token'
    )

    class Meta:
        model = Translation
        fields = ['token', 'translation']


class StringTokenModelSerializer(serializers.Serializer):
    token = serializers.CharField()
    translation = serializers.SerializerMethodField()
    comment = serializers.CharField()
    tags = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def _get_translation_obj(self, obj):
        code = self.context.get('code', '').upper()
        return obj.translation.filter(language__code=code).first()

    def get_translation(self, obj):
        t = self._get_translation_obj(obj)
        return t.translation if t else ''

    def get_tags(self, obj):
        return [tag.tag for tag in obj.tags.all()]

    def get_status(self, obj):
        t = self._get_translation_obj(obj)
        return t.status if t else Translation.Status.new


class SimplifiedStringTokenSerializer(serializers.Serializer):
    token = serializers.CharField(source='token')
    translation = serializers.SerializerMethodField()

    def get_translation(self, obj):
        code = self.context.get('code', '').upper()
        translation = obj.translation.filter(language__code=code).first()
        return translation.translation if translation else ''


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag']


class EditorFieldSerializer(serializers.RelatedField):
    def to_representation(self, value):
        return f'{value.first_name} {value.last_name}'


class HistorySerializer(serializers.ModelSerializer):
    editor = EditorFieldSerializer(read_only=True)

    class Meta:
        model = HistoryRecord
        fields = ['updated_at', 'language', 'token',
                  'status', 'editor', 'old_value', 'new_value']


class ProjectAccessTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectAccessToken
        fields = ['token', 'permission', 'expiration']


class TranslationBundleSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = TranslationBundle
        fields = ['id', 'name', 'description', 'created_at', 'created_by']

    def get_created_by(self, obj):
        return f'{obj.created_by.first_name} {obj.created_by.last_name}'


class LanguageSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return Langcoder.language(obj.code)

    class Meta:
        model = Language
        fields = ['code', 'name']


class AvailableLanguageSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class CreateProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['name', 'description']


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
