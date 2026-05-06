"""
Shared test helpers: user/project/language/token factories.
"""
from django.contrib.auth.models import User
from rest_framework.test import APIClient

import secrets

from api.models.language import Language
from api.models.project import Project, ProjectRole, ProjectAccessToken
from api.models.translations import StringToken, Translation
from api.models.tag import Tag


def make_user(username='user', password='pass1234X'):
    return User.objects.create_user(username=username, password=password)


def make_project(name='TestProject', owner=None, require_2fa=False):
    project = Project.objects.create(name=name, description='desc', require_2fa=require_2fa)
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


def make_access_token(project, user, permission=ProjectAccessToken.AccessTokenPermissions.write):
    return ProjectAccessToken.objects.create(
        token=secrets.token_hex(8),
        permission=permission,
        expiration=None,
        user=user,
        project=project,
    )


from api.models.glossary import GlossaryTerm, GlossaryTranslation, GlossaryExtractionJob


def make_glossary_term(project, term='Submit', definition='', case_sensitive=False, owner=None):
    return GlossaryTerm.objects.create(
        project=project,
        term=term,
        definition=definition,
        case_sensitive=case_sensitive,
        created_by=owner,
    )


def make_glossary_translation(term, language_code='DE', preferred_translation='Absenden', user=None):
    return GlossaryTranslation.objects.create(
        term=term,
        language_code=language_code.upper(),
        preferred_translation=preferred_translation,
        updated_by=user,
    )


def make_extraction_job(project, user=None, status='complete', suggestions=None):
    return GlossaryExtractionJob.objects.create(
        project=project,
        created_by=user,
        status=status,
        suggestions=suggestions or [],
    )
