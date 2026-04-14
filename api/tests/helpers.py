"""
Shared test helpers: user/project/language/token factories.
"""
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from api.models.language import Language
from api.models.project import Project, ProjectRole
from api.models.translations import StringToken, Translation
from api.models.tag import Tag


def make_user(username='user', password='pass1234X'):
    return User.objects.create_user(username=username, password=password)


def make_project(name='TestProject', owner=None):
    project = Project.objects.create(name=name, description='desc')
    if owner:
        ProjectRole.objects.create(user=owner, project=project, role=ProjectRole.Role.owner)
    return project


def add_role(user, project, role):
    return ProjectRole.objects.create(user=user, project=project, role=role)


def make_language(project, code='EN'):
    return Language.objects.create(code=code.upper(), project=project)


def make_token(project, key='greeting', comment=''):
    return StringToken.objects.create(token=key, comment=comment, project=project)


def make_translation(token, language, text='Hello', status=None):
    t = Translation.objects.create(
        token=token,
        language=language,
        translation=text,
        status=status or Translation.Status.new,
    )
    return t


def authed_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client
