from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import *
from .transport_models import *


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
    class Meta:
        model = Project
        fields = ['id', 'name', 'description']


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
        fields = ['id', 'token', 'comment', 'tags']


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


class StringTokenModelSerializer:

    def __init__(self, token, code) -> None:
        self.token = token
        self.code = code

    def toJson(self):

        translation = self.token.translation.filter(
            language__code=self.code.upper()).first()
        if translation:
            text = translation.translation
        else:
            text = ''

        return {
            'token': self.token.token,
            'translation': text,
            'comment': self.token.comment,
            'tags': [tag.tag for tag in self.token.tags.all()]
        }

    def toSimplifiedJson(self):
        translation = self.token.translation.filter(
            language__code=self.code.upper()).first()
        if translation:
            text = translation.translation
        else:
            text = ''
        return {
            'token': self.token.token,
            'translation': text,
        }


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
