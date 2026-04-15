from django.db import transaction
from django.http import HttpResponse, JsonResponse
from rest_framework import generics, permissions, status

from api.file_processors.compare_file import CompareFileWriter
from api.file_processors.export_file_type import ExportFile
from api.file_processors.file_processor import FileProcessor
from api.models.bundle import TranslationBundle, TranslationBundleMap
from api.models.language import Language
from api.models.project import Project, ProjectRole
from api.models.string_token import StringToken
from api.models.translations import Translation
from api.models.transport_models import TranslationModel
from api.views.helper import error_response


def _get_project_for_member(pk, user):
    """Any project member may read bundle data."""
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
    ).first()


def _get_project_for_editor(pk, user):
    """Owner, admin, or editor may create bundles."""
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_token_roles,
    ).first()


def _get_project_for_admin(pk, user):
    """Owner or admin may activate/deactivate/delete bundles."""
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_participants_roles,
    ).first()


def _next_version_name(project):
    count = TranslationBundle.objects.filter(project=project).count()
    return f"v{count + 1}"


def _serialize_bundle(bundle):
    return {
        'id': bundle.id,
        'version_name': bundle.version_name,
        'is_active': bundle.is_active,
        'created_at': bundle.created_at.isoformat(),
        'created_by': bundle.created_by.username if bundle.created_by else None,
        'translation_count': bundle.maps.exclude(value='').count(),
    }


RESERVED_VERSION_NAMES = {'active', 'live'}


class BundleListCreateAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        project = _get_project_for_member(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        bundles = TranslationBundle.objects.filter(
            project=project
        ).order_by('-created_at')
        return JsonResponse([_serialize_bundle(b) for b in bundles], safe=False)

    def post(self, request, pk):
        project = _get_project_for_editor(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        version_name = request.data.get('version_name') or _next_version_name(project)

        if version_name.lower() in RESERVED_VERSION_NAMES:
            return error_response(
                f"'{version_name}' is a reserved name. Choose a different version name.",
                status.HTTP_400_BAD_REQUEST,
            )

        if TranslationBundle.objects.filter(project=project, version_name=version_name).exists():
            return error_response(
                f"Bundle '{version_name}' already exists for this project.",
                status.HTTP_409_CONFLICT,
            )

        tokens = list(StringToken.objects.filter(project=project))
        languages = list(Language.objects.filter(project=project))

        translation_lookup = {
            (t.token_id, t.language_id): t
            for t in Translation.objects.filter(token__project=project)
        }

        with transaction.atomic():
            bundle = TranslationBundle.objects.create(
                project=project,
                version_name=version_name,
                created_by=request.user,
            )
            maps = []
            for token in tokens:
                for lang in languages:
                    t = translation_lookup.get((token.id, lang.id))
                    maps.append(TranslationBundleMap(
                        bundle=bundle,
                        token=token,
                        token_name=token.token,
                        translation=t,
                        language=lang,
                        value=t.translation if t else '',
                    ))
            TranslationBundleMap.objects.bulk_create(maps, batch_size=500)

        return JsonResponse(_serialize_bundle(bundle), status=status.HTTP_201_CREATED)


class BundleDetailAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_bundle(self, pk, bundle_id, user, admin_only=False):
        getter = _get_project_for_admin if admin_only else _get_project_for_member
        project = getter(pk, user)
        if not project:
            return None, error_response('Not found', status.HTTP_404_NOT_FOUND)

        try:
            bundle = TranslationBundle.objects.get(id=bundle_id, project=project)
        except TranslationBundle.DoesNotExist:
            return None, error_response('Bundle not found', status.HTTP_404_NOT_FOUND)

        return bundle, None

    def get(self, request, pk, bundle_id):
        bundle, err = self._get_bundle(pk, bundle_id, request.user)
        if err:
            return err
        return JsonResponse(_serialize_bundle(bundle))

    def delete(self, request, pk, bundle_id):
        bundle, err = self._get_bundle(pk, bundle_id, request.user, admin_only=True)
        if err:
            return err

        if bundle.is_active:
            return error_response(
                'Cannot delete the active bundle. Deactivate it first.',
                status.HTTP_409_CONFLICT,
            )

        bundle.delete()
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)


class BundleActivateAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, bundle_id):
        project = _get_project_for_admin(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        try:
            bundle = TranslationBundle.objects.get(id=bundle_id, project=project)
        except TranslationBundle.DoesNotExist:
            return error_response('Bundle not found', status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            TranslationBundle.objects.filter(project=project, is_active=True).update(is_active=False)
            bundle.is_active = True
            bundle.save(update_fields=['is_active'])

        return JsonResponse(_serialize_bundle(bundle))


class BundleDeactivateAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, bundle_id):
        project = _get_project_for_admin(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        try:
            bundle = TranslationBundle.objects.get(id=bundle_id, project=project)
        except TranslationBundle.DoesNotExist:
            return error_response('Bundle not found', status.HTTP_404_NOT_FOUND)

        bundle.is_active = False
        bundle.save(update_fields=['is_active'])
        return JsonResponse(_serialize_bundle(bundle))


class BundleCompareAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        project = _get_project_for_member(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        from_id = request.GET.get('from')
        to_id = request.GET.get('to')

        if not from_id or not to_id:
            return error_response(
                "Both 'from' and 'to' query parameters are required. Use a bundle id or 'live'.",
                status.HTTP_400_BAD_REQUEST,
            )

        diff, err = _compute_compare_diff(project, from_id, to_id)
        if err:
            return error_response(err, status.HTTP_404_NOT_FOUND)

        return JsonResponse(diff)


class BundleCompareExportAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        project = _get_project_for_member(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        from_id = request.GET.get('from')
        to_id = request.GET.get('to')
        mode = request.GET.get('mode', 'diff')

        if not from_id or not to_id:
            return error_response(
                "Both 'from' and 'to' query parameters are required.",
                status.HTTP_400_BAD_REQUEST,
            )

        if mode not in ('diff', 'changes'):
            return error_response(
                "mode must be 'diff' or 'changes'.",
                status.HTTP_400_BAD_REQUEST,
            )

        diff, err = _compute_compare_diff(project, from_id, to_id)
        if err:
            return error_response(err, status.HTTP_404_NOT_FOUND)

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        CompareFileWriter(diff=diff, mode=mode).write(response)
        return response


def _compute_compare_diff(project, from_id, to_id):
    """
    Returns (diff_dict, error_string).
    diff_dict keys: added, removed, changed, unchanged_count, new_tokens, deleted_tokens.
    """
    from_data, err = _build_compare_dict(project, from_id)
    if err:
        return None, f"'from': {err}"

    to_data, err = _build_compare_dict(project, to_id)
    if err:
        return None, f"'to': {err}"

    added = []
    removed = []
    changed = []
    unchanged = 0

    for key in set(from_data) | set(to_data):
        token_key, lang_code = key
        in_from = key in from_data
        in_to = key in to_data

        if in_from and not in_to:
            removed.append({'token': token_key, 'language': lang_code, 'from': from_data[key]})
        elif not in_from and in_to:
            added.append({'token': token_key, 'language': lang_code, 'value': to_data[key]})
        elif from_data[key] != to_data[key]:
            changed.append({
                'token': token_key,
                'language': lang_code,
                'from': from_data[key],
                'to': to_data[key],
            })
        else:
            unchanged += 1

    new_tokens = []
    deleted_tokens = []

    from_bundle = None if from_id == 'live' else TranslationBundle.objects.filter(
        id=int(from_id), project=project).first()
    to_bundle = None if to_id == 'live' else TranslationBundle.objects.filter(
        id=int(to_id), project=project).first()

    if from_bundle is not None and to_id == 'live':
        from_token_names = set(
            from_bundle.maps.exclude(token_name='').values_list('token_name', flat=True).distinct()
        )
        live_token_names = set(
            StringToken.objects.filter(project=project).values_list('token', flat=True)
        )
        new_tokens = sorted(live_token_names - from_token_names)
        deleted_tokens = sorted(from_token_names - live_token_names)

    elif to_bundle is not None and from_id == 'live':
        to_token_names = set(
            to_bundle.maps.exclude(token_name='').values_list('token_name', flat=True).distinct()
        )
        live_token_names = set(
            StringToken.objects.filter(project=project).values_list('token', flat=True)
        )
        new_tokens = sorted(to_token_names - live_token_names)
        deleted_tokens = sorted(live_token_names - to_token_names)

    return {
        'added': added,
        'removed': removed,
        'changed': changed,
        'unchanged_count': unchanged,
        'new_tokens': new_tokens,
        'deleted_tokens': deleted_tokens,
    }, None


def _build_compare_dict(project, source):
    """
    Returns ({(token_key, lang_code): value}, error_string).
    source is either 'live' or a bundle id (string or int).
    Only includes pairs with a non-empty value.
    """
    if source == 'live':
        translations = (
            Translation.objects
            .filter(token__project=project)
            .select_related('token', 'language')
        )
        return {(t.token.token, t.language.code.lower()): t.translation
                for t in translations if t.translation}, None

    try:
        bundle = TranslationBundle.objects.get(id=int(source), project=project)
    except (TranslationBundle.DoesNotExist, ValueError):
        return None, f"Bundle '{source}' not found."

    maps = bundle.maps.select_related('language').all()
    return {(m.token_name, m.language.code.lower()): m.value
            for m in maps if m.value and m.token_name}, None


class BundleExportAPI(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, bundle_id):
        project = _get_project_for_member(pk, request.user)
        if not project:
            return error_response('Not found', status.HTTP_404_NOT_FOUND)

        try:
            bundle = TranslationBundle.objects.get(id=bundle_id, project=project)
        except TranslationBundle.DoesNotExist:
            return error_response('Bundle not found', status.HTTP_404_NOT_FOUND)

        export_type = request.GET.get('type')
        codes_param = request.GET.get('codes')

        try:
            file_type = ExportFile(export_type)
        except ValueError:
            return error_response('Unsupported file type', status.HTTP_400_BAD_REQUEST)

        if codes_param:
            lang_codes = [c.strip().upper() for c in codes_param.split(',')]
        else:
            lang_codes = list(
                Language.objects.filter(project=project).values_list('code', flat=True)
            )

        maps = (
            bundle.maps
            .select_related('token', 'language')
            .prefetch_related('token__tags')
            .filter(language__code__in=lang_codes, token__isnull=False)
            .exclude(value='')
        )

        # Group maps by language code
        by_language = {}
        for m in maps:
            code = m.language.code.lower()
            by_language.setdefault(code, []).append(m)

        processor = FileProcessor(type=file_type)
        for code, bundle_maps in by_language.items():
            records = [TranslationModel.from_bundle_map(m) for m in bundle_maps]
            try:
                processor.append(records=records, code=code)
            except Exception as e:
                return error_response(str(e), status.HTTP_400_BAD_REQUEST)

        return processor.http_response()
