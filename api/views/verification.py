import logging

from django.db import transaction
from django.http import JsonResponse
from django_q.tasks import async_task
from rest_framework import generics, status

from api.models.project import Project, ProjectAIProvider, ProjectRole
from api.models.verification import VerificationComment, VerificationReport
from api.serializers.verification import (
    VerificationCommentSerializer,
    VerificationReportDetailSerializer,
    VerificationReportListSerializer,
)

logger = logging.getLogger(__name__)

MODE_CHECKS = {
    VerificationReport.Mode.source_quality: [
        'spelling_grammar',
        'tone_register',
        'punctuation',
        'capitalisation',
        'placeholder_format',
    ],
    VerificationReport.Mode.translation_accuracy: [
        'semantic_accuracy',
        'placeholder_preservation',
        'omissions_additions',
        'grammar_target',
        'tone_match',
    ],
}


def _get_project_any_role(pk: int, user) -> Project | None:
    return Project.objects.filter(pk=pk, roles__user=user).first()


def _get_project_admin(pk: int, user) -> Project | None:
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_participants_roles,
    ).first()


def _get_project_editor_plus(pk: int, user) -> Project | None:
    return Project.objects.filter(
        pk=pk,
        roles__user=user,
        roles__role__in=ProjectRole.change_token_roles,
    ).first()


def _has_active_job(project: Project, mode: str, target_language: str) -> bool:
    active_statuses = [VerificationReport.Status.pending, VerificationReport.Status.running]
    qs = VerificationReport.objects.filter(project=project, status__in=active_statuses, mode=mode)
    if mode == VerificationReport.Mode.translation_accuracy:
        qs = qs.filter(target_language=target_language.upper())
    return qs.exists()


def _build_count_queryset(project: Project, mode: str, target_language: str,
                          scope_id, tags: list[str], new_only: bool):
    from api.models.string_token import StringToken
    from api.models.translations import Translation

    if mode == VerificationReport.Mode.source_quality:
        qs = StringToken.objects.filter(project=project, status=StringToken.Status.active)
        if scope_id:
            qs = qs.filter(scopes__id=scope_id)
        if tags:
            qs = qs.filter(tags__tag__in=tags).distinct()
        return qs.count()
    else:
        qs = Translation.objects.filter(
            token__project=project,
            token__status=StringToken.Status.active,
            language__code=target_language.upper(),
        )
        if scope_id:
            qs = qs.filter(token__scopes__id=scope_id)
        if tags:
            qs = qs.filter(token__tags__tag__in=tags).distinct()
        if new_only:
            qs = qs.filter(status=Translation.Status.new)
        return qs.count()


class VerificationCountAPI(generics.GenericAPIView):

    def get(self, request, pk):
        project = _get_project_admin(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        mode = request.query_params.get('mode', '')
        target_language = request.query_params.get('target_language', '')
        scope_id = request.query_params.get('scope_id') or None
        tags = [t for t in request.query_params.get('tags', '').split(',') if t]
        new_only = request.query_params.get('new_only', '').lower() in ('true', '1')

        if mode not in dict(VerificationReport.Mode.choices):
            return JsonResponse({'error': 'Invalid mode'}, status=status.HTTP_400_BAD_REQUEST)

        count = _build_count_queryset(project, mode, target_language, scope_id, tags, new_only)
        return JsonResponse({'count': count})


class VerificationListCreateAPI(generics.GenericAPIView):

    def get(self, request, pk):
        project = _get_project_any_role(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if not ProjectAIProvider.objects.filter(project=project).exists():
            return JsonResponse({'error': 'No AI provider configured'}, status=status.HTTP_404_NOT_FOUND)

        reports = VerificationReport.objects.filter(project=project).select_related('created_by')
        serializer = VerificationReportListSerializer(reports, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self, request, pk):
        project = _get_project_admin(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        if not ProjectAIProvider.objects.filter(project=project).exists():
            return JsonResponse({'error': 'No AI provider configured'}, status=status.HTTP_400_BAD_REQUEST)

        mode = request.data.get('mode', '')
        target_language = request.data.get('target_language', '').strip().upper()
        scope_id = request.data.get('scope_id') or None
        tags = request.data.get('tags', [])
        new_only = bool(request.data.get('new_only', False))
        checks = request.data.get('checks', [])

        if mode not in dict(VerificationReport.Mode.choices):
            return JsonResponse({'error': 'Invalid mode'}, status=status.HTTP_400_BAD_REQUEST)
        if mode == VerificationReport.Mode.translation_accuracy and not target_language:
            return JsonResponse(
                {'error': 'target_language is required for translation_accuracy mode'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not checks:
            return JsonResponse({'error': 'At least one check must be selected'}, status=status.HTTP_400_BAD_REQUEST)

        valid_checks = MODE_CHECKS.get(mode, [])
        invalid = [c for c in checks if c not in valid_checks]
        if invalid:
            return JsonResponse({'error': f'Invalid checks: {invalid}'}, status=status.HTTP_400_BAD_REQUEST)

        if _has_active_job(project, mode, target_language):
            return JsonResponse(
                {'error': 'A verification job is already running for this configuration'},
                status=status.HTTP_409_CONFLICT
            )

        scope = None
        if scope_id:
            from api.models.scope import Scope
            try:
                scope = Scope.objects.get(pk=scope_id, project=project)
            except Scope.DoesNotExist:
                return JsonResponse({'error': 'Scope not found'}, status=status.HTTP_404_NOT_FOUND)

        report = VerificationReport.objects.create(
            project=project,
            created_by=request.user,
            mode=mode,
            target_language=target_language,
            scope=scope,
            tags=tags,
            new_only=new_only,
            checks=checks,
        )

        async_task('api.tasks.run_verification_job', report.pk)

        serializer = VerificationReportListSerializer(report)
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)


class VerificationDetailAPI(generics.GenericAPIView):

    def _get_report(self, pk: int, report_id: int, user, require_admin: bool = False):
        if require_admin:
            project = _get_project_admin(pk, user)
        else:
            project = _get_project_any_role(pk, user)
        if not project:
            return None, JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            report = VerificationReport.objects.select_related(
                'project', 'created_by', 'scope'
            ).get(pk=report_id, project=project)
            return report, None
        except VerificationReport.DoesNotExist:
            return None, JsonResponse({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk, report_id):
        report, err = self._get_report(pk, report_id, request.user)
        if err:
            return err
        serializer = VerificationReportDetailSerializer(report)
        return JsonResponse(serializer.data)

    def delete(self, request, pk, report_id):
        report, err = self._get_report(pk, report_id, request.user, require_admin=True)
        if err:
            return err
        report.delete()
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)


class VerificationApplyAPI(generics.GenericAPIView):

    def post(self, request, pk, report_id):
        project = _get_project_editor_plus(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        try:
            report = VerificationReport.objects.get(pk=report_id, project=project)
        except VerificationReport.DoesNotExist:
            return JsonResponse({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

        if report.status != VerificationReport.Status.complete:
            return JsonResponse({'error': 'Report is not complete'}, status=status.HTTP_400_BAD_REQUEST)

        suggestions = request.data.get('suggestions', [])
        if not suggestions:
            return JsonResponse({'error': 'No suggestions provided'}, status=status.HTTP_400_BAD_REQUEST)

        from api.models.string_token import StringToken
        from api.models.translations import Translation, PluralTranslation

        applied = 0
        errors = []

        for suggestion in suggestions:
            token_id = suggestion.get('token_id')
            plural_form = suggestion.get('plural_form')
            text = suggestion.get('text', '')

            try:
                token = StringToken.objects.get(pk=token_id, project=project)
            except StringToken.DoesNotExist:
                errors.append(f'Token {token_id} not found')
                continue

            lang_code = report.target_language if report.mode == VerificationReport.Mode.translation_accuracy else None

            if plural_form:
                try:
                    if lang_code:
                        tr = Translation.objects.get(token=token, language__code=lang_code.upper())
                    else:
                        from api.models.language import Language
                        default_lang = Language.objects.filter(project=project, is_default=True).first()
                        tr = Translation.objects.get(token=token, language=default_lang)
                    pf_obj, _ = PluralTranslation.objects.get_or_create(
                        translation=tr, plural_form=plural_form
                    )
                    pf_obj.value = text
                    pf_obj.save()
                    applied += 1
                except Exception as e:
                    errors.append(f'Token {token_id} plural {plural_form}: {e}')
            else:
                try:
                    code = lang_code or ''
                    if not code:
                        from api.models.language import Language
                        default_lang = Language.objects.filter(project=project, is_default=True).first()
                        code = default_lang.code if default_lang else ''
                    Translation.create_or_update_translation(
                        user=request.user,
                        token=token,
                        code=code,
                        project_id=project.pk,
                        text=text,
                    )
                    applied += 1
                except Exception as e:
                    errors.append(f'Token {token_id}: {e}')

        report.is_readonly = True
        report.save(update_fields=['is_readonly'])

        return JsonResponse({'applied': applied, 'errors': errors})


class VerificationCommentAPI(generics.GenericAPIView):

    def post(self, request, pk, report_id):
        project = _get_project_any_role(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            report = VerificationReport.objects.get(pk=report_id, project=project)
        except VerificationReport.DoesNotExist:
            return JsonResponse({'error': 'Report not found'}, status=status.HTTP_404_NOT_FOUND)

        token_id = request.data.get('token_id')
        token_key = request.data.get('token_key', '')
        plural_form = request.data.get('plural_form', '')
        text = request.data.get('text', '').strip()

        if not token_id:
            return JsonResponse({'error': 'token_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not text:
            return JsonResponse({'error': 'text is required'}, status=status.HTTP_400_BAD_REQUEST)

        comment = VerificationComment.objects.create(
            report=report,
            token_id=token_id,
            token_key=token_key,
            plural_form=plural_form,
            author=request.user,
            text=text,
        )

        serializer = VerificationCommentSerializer(comment)
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
