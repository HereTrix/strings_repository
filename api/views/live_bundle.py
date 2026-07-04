# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import hashlib
import io
import os
import secrets
import tempfile
from pathlib import Path
from urllib.parse import quote

from django.conf import settings as django_settings
from django.http import FileResponse
from rest_framework import generics, status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response

from api.file_processors.export_file_type import ExportFile
from api.file_processors.file_processor import FileProcessor, WRITER_MAP
from api.models.bundle import TranslationBundle
from api.models.language import Language
from api.models.live_bundle import LiveBundleSettings
from api.models.project import ProjectRole
from api.models.transport_models import TranslationModel
from api.views.helper import error_response, get_project_any_role, get_project_admin


def generate_token(length=16):
    return secrets.token_urlsafe(length)


def _serialize_live_bundle_settings(settings_obj, include_token):
    enabled = bool(settings_obj and settings_obj.token)
    return {
        'enabled': enabled,
        'token': settings_obj.token if (enabled and include_token) else None,
    }


class LiveBundleSettingsAPI(generics.GenericAPIView):

    def get(self, request, pk):
        project = get_project_any_role(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        role = project.roles.get(user=request.user).role
        include_token = role in ProjectRole.change_token_roles
        settings_obj = LiveBundleSettings.objects.filter(project=project).first()
        return Response(_serialize_live_bundle_settings(settings_obj, include_token))

    def post(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        settings_obj, _ = LiveBundleSettings.objects.get_or_create(project=project)
        if settings_obj.token:
            return error_response(
                'Live bundle serving is already enabled.', status.HTTP_409_CONFLICT)

        settings_obj.token = generate_token()
        settings_obj.save(update_fields=['token', 'updated_at'])
        return Response(_serialize_live_bundle_settings(settings_obj, include_token=True))

    def delete(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        settings_obj = LiveBundleSettings.objects.filter(project=project).first()
        if settings_obj and settings_obj.token:
            settings_obj.token = None
            settings_obj.save(update_fields=['token', 'updated_at'])
        return Response(_serialize_live_bundle_settings(settings_obj, include_token=True))


class LiveBundleRegenerateAPI(generics.GenericAPIView):

    def post(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        settings_obj = LiveBundleSettings.objects.filter(project=project).first()
        if not settings_obj or not settings_obj.token:
            return error_response(
                'Live bundle serving is not enabled.', status.HTTP_409_CONFLICT)

        settings_obj.token = generate_token()
        settings_obj.save(update_fields=['token', 'updated_at'])
        return Response(_serialize_live_bundle_settings(settings_obj, include_token=True))


class LiveBundleTokenAuth(BaseAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_ACCESS_TOKEN')

        if not token:
            return None

        try:
            settings_obj = LiveBundleSettings.objects.select_related('project').get(token=token)
        except LiveBundleSettings.DoesNotExist:
            raise AuthenticationFailed('No access')

        return (None, settings_obj)


class LiveBundleVersionAPI(generics.GenericAPIView):
    authentication_classes = [LiveBundleTokenAuth]
    permission_classes = []

    def get(self, request):
        access = request.auth
        if not access:
            return error_response('Not found', status.HTTP_403_FORBIDDEN)

        bundle = TranslationBundle.objects.filter(
            project=access.project, is_active=True).first()
        if not bundle:
            return Response({})

        return Response({
            'version_name': bundle.version_name,
            'created_at': bundle.created_at.isoformat(),
        })


def _cache_key(export_type, tags, scope_id, codes):
    canonical = (
        f"{export_type}|{','.join(sorted(tags))}|"
        f"{scope_id if scope_id is not None else ''}|{','.join(sorted(codes))}"
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cache_path(project_id, bundle_id, cache_key, extension):
    return (
        Path(django_settings.LIVE_BUNDLE_CACHE_ROOT)
        / str(project_id) / str(bundle_id) / f"{cache_key}{extension}"
    )


def _write_cache_atomic(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except FileExistsError:
        pass
    fd, tmp_path = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise


def _build_content(bundle, export_type, tags, scope_id, codes):
    maps = (
        bundle.maps
        .select_related('token', 'language')
        .prefetch_related('token__tags')
        .filter(language__code__in=codes, token__isnull=False)
        .exclude(value='')
        .order_by('language__code', 'token__token')
    )

    if scope_id is not None:
        maps = maps.filter(token__scopes__id=scope_id)

    for tag in tags:
        maps = maps.filter(token__tags__tag=tag)

    by_language = {}
    for m in maps:
        code = m.language.code.lower()
        by_language.setdefault(code, []).append(m)

    processor = FileProcessor(type=export_type)
    for code, bundle_maps in by_language.items():
        records = [TranslationModel.from_bundle_map(m) for m in bundle_maps]
        processor.append(records=records, code=code)

    buf = io.BytesIO()
    processor.writer.write(buf)
    buf.seek(0)
    return buf.read()


class LiveBundleContentAPI(generics.GenericAPIView):
    authentication_classes = [LiveBundleTokenAuth]
    permission_classes = []

    def get(self, request):
        access = request.auth
        if not access:
            return error_response('Not found', status.HTTP_403_FORBIDDEN)

        project = access.project
        bundle = TranslationBundle.objects.filter(project=project, is_active=True).first()
        if not bundle:
            return error_response('No live bundle available.', status.HTTP_404_NOT_FOUND)

        requested_version = request.GET.get('version_name')
        if requested_version == bundle.version_name:
            return Response(status=status.HTTP_204_NO_CONTENT)

        export_type_param = request.GET.get('type', 'json')
        try:
            export_type = ExportFile(export_type_param)
        except ValueError:
            return error_response('Unsupported file type', status.HTTP_400_BAD_REQUEST)

        codes_param = request.GET.get('codes')
        if codes_param:
            codes = [c.strip().upper() for c in codes_param.split(',')]
        else:
            codes = list(Language.objects.filter(
                project=project).values_list('code', flat=True))

        tags_param = request.GET.get('tags')
        tags = [t.strip() for t in tags_param.split(',') if t.strip()] if tags_param else []

        scope_param = request.GET.get('scope')
        scope_id = None
        if scope_param:
            try:
                scope_id = int(scope_param)
            except ValueError:
                # Invalid scope -> empty result set, not an error.
                scope_id = -1

        cache_key = _cache_key(export_type.value, tags, scope_id, codes)
        cache_path = _cache_path(project.id, bundle.id, cache_key, export_type.file_extension())
        content_type = WRITER_MAP[export_type].content_type

        if not cache_path.exists():
            content = _build_content(bundle, export_type, tags, scope_id, codes)
            _write_cache_atomic(cache_path, content)

        response = FileResponse(open(cache_path, 'rb'), content_type=content_type)
        # FileResponse auto-sets Content-Disposition from the opened file's name — this is
        # an API response for a client app, not a browser download, so remove it.
        del response['Content-Disposition']
        # version_name is free-form user input (see BundleListCreateAPI) — percent-encode
        # so the header value is always valid; clients must URL-decode it.
        response['X-Bundle-Version'] = quote(bundle.version_name, safe='')
        return response
