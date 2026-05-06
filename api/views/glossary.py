import csv
import io
import random
from datetime import datetime, timezone

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django_q.tasks import async_task
from rest_framework import generics, status

from api.models.glossary import GlossaryExtractionJob, GlossaryTerm, GlossaryTranslation
from api.models.project import ProjectAIProvider
from api.serializers.glossary import GlossaryExtractionJobSerializer, GlossaryTermSerializer
from api.throttles import AICallRateThrottle
from api.views.helper import get_project_admin, get_project_any_role


class GlossaryTermListCreateAPI(generics.GenericAPIView):

    def get(self, request, pk):
        project = get_project_any_role(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        terms = GlossaryTerm.objects.filter(
            project=project).prefetch_related('translations')
        serializer = GlossaryTermSerializer(terms, many=True)
        return JsonResponse(serializer.data, safe=False)

    def post(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        term_value = request.data.get('term', '').strip()
        if not term_value:
            return JsonResponse({'error': 'term is required'}, status=status.HTTP_400_BAD_REQUEST)

        if GlossaryTerm.objects.filter(project=project, term__iexact=term_value).exists():
            return JsonResponse({'error': 'A term with this name already exists'}, status=status.HTTP_409_CONFLICT)

        definition = request.data.get('definition', '')
        case_sensitive = bool(request.data.get('case_sensitive', False))
        translations_data = request.data.get('translations', [])

        with transaction.atomic():
            term = GlossaryTerm.objects.create(
                project=project,
                term=term_value,
                definition=definition,
                case_sensitive=case_sensitive,
                created_by=request.user,
            )
            _save_translations(term, translations_data, request.user, project)

        term.refresh_from_db()
        serializer = GlossaryTermSerializer(
            GlossaryTerm.objects.prefetch_related(
                'translations').get(pk=term.pk)
        )
        return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)


class GlossaryTermDetailAPI(generics.GenericAPIView):

    def _get_term(self, request, pk, term_id, require_admin=False):
        if require_admin:
            project = get_project_admin(pk, request.user)
            if not project:
                return None, None, JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        else:
            project = get_project_any_role(pk, request.user)
            if not project:
                return None, None, JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        try:
            term = GlossaryTerm.objects.prefetch_related(
                'translations').get(pk=term_id, project=project)
            return project, term, None
        except GlossaryTerm.DoesNotExist:
            return None, None, JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    def get(self, request, pk, term_id):
        _, term, err = self._get_term(request, pk, term_id)
        if err:
            return err
        return JsonResponse(GlossaryTermSerializer(term).data)

    def put(self, request, pk, term_id):
        project, term, err = self._get_term(
            request, pk, term_id, require_admin=True)
        if err:
            return err

        new_term_value = request.data.get('term', term.term).strip()
        if new_term_value != term.term:
            conflict = GlossaryTerm.objects.filter(
                project=project, term__iexact=new_term_value
            ).exclude(pk=term.pk).exists()
            if conflict:
                return JsonResponse({'error': 'A term with this name already exists'}, status=status.HTTP_409_CONFLICT)

        with transaction.atomic():
            term.term = new_term_value
            term.definition = request.data.get('definition', term.definition)
            term.case_sensitive = bool(request.data.get(
                'case_sensitive', term.case_sensitive))
            term.save()
            translations_data = request.data.get('translations')
            if translations_data is not None:
                term.translations.all().delete()
                _save_translations(term, translations_data,
                                   request.user, project)

        serializer = GlossaryTermSerializer(
            GlossaryTerm.objects.prefetch_related(
                'translations').get(pk=term.pk)
        )
        return JsonResponse(serializer.data)

    def delete(self, request, pk, term_id):
        _, term, err = self._get_term(request, pk, term_id, require_admin=True)
        if err:
            return err
        term.delete()
        return JsonResponse({}, status=status.HTTP_204_NO_CONTENT)


def _save_translations(term, translations_data, user, project):
    from api.models.language import Language
    valid_codes = set(
        Language.objects.filter(project=project).values_list('code', flat=True)
    )
    to_create = []
    seen_codes = set()
    for td in translations_data:
        code = td.get('language_code', '').strip().upper()
        preferred = td.get('preferred_translation', '').strip()
        if not code or not preferred:
            continue
        if code not in valid_codes:
            continue
        if code in seen_codes:
            continue
        seen_codes.add(code)
        to_create.append(GlossaryTranslation(
            term=term,
            language_code=code,
            preferred_translation=preferred,
            updated_by=user,
        ))
    if to_create:
        GlossaryTranslation.objects.bulk_create(to_create)


class GlossaryExportAPI(generics.GenericAPIView):

    def get(self, request, pk):
        project = get_project_any_role(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        terms = GlossaryTerm.objects.filter(
            project=project).prefetch_related('translations').order_by('term')

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['term', 'definition', 'case_sensitive',
                        'language_code', 'preferred_translation'])

        for term in terms:
            translations = list(term.translations.all())
            if translations:
                for tr in translations:
                    writer.writerow([term.term, term.definition, str(term.case_sensitive).lower(),
                                     tr.language_code, tr.preferred_translation])
            else:
                writer.writerow([term.term, term.definition, str(
                    term.case_sensitive).lower(), '', ''])

        safe_name = ''.join(
            c if c.isalnum() or c in '-_' else '_' for c in project.name)
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="glossary-{safe_name}.csv"'
        return response


class GlossaryImportAPI(generics.GenericAPIView):

    def post(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        uploaded = request.FILES.get('file')
        if not uploaded:
            return JsonResponse({'error': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)

        from api.models.language import Language
        valid_codes = set(Language.objects.filter(
            project=project).values_list('code', flat=True))

        try:
            decoded = uploaded.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))
        except Exception as e:
            return JsonResponse({'error': f'Could not parse CSV: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        imported = 0
        updated = 0
        skipped = 0
        warnings = []

        term_rows: dict[str, dict] = {}
        for row in reader:
            raw_term = (row.get('term') or '').strip()
            if not raw_term:
                skipped += 1
                continue
            key = raw_term.lower()
            if key not in term_rows:
                cs_val = (row.get('case_sensitive') or 'false').strip().lower()
                term_rows[key] = {
                    'term': raw_term,
                    'definition': (row.get('definition') or '').strip(),
                    'case_sensitive': cs_val in ('true', '1', 'yes'),
                    'translations': [],
                }
            lang = (row.get('language_code') or '').strip().upper()
            preferred = (row.get('preferred_translation') or '').strip()
            if lang and preferred:
                if lang not in valid_codes:
                    warnings.append(
                        f'Language "{lang}" not in project — skipped for term "{raw_term}"')
                else:
                    term_rows[key]['translations'].append(
                        {'language_code': lang, 'preferred_translation': preferred})

        with transaction.atomic():
            for key, data in term_rows.items():
                existing = GlossaryTerm.objects.filter(
                    project=project, term__iexact=data['term']).first()
                if existing:
                    existing.definition = data['definition']
                    existing.case_sensitive = data['case_sensitive']
                    existing.save(
                        update_fields=['definition', 'case_sensitive', 'updated_at'])
                    existing.translations.all().delete()
                    _save_translations(
                        existing, data['translations'], request.user, project)
                    updated += 1
                else:
                    term_obj = GlossaryTerm.objects.create(
                        project=project,
                        term=data['term'],
                        definition=data['definition'],
                        case_sensitive=data['case_sensitive'],
                        created_by=request.user,
                    )
                    _save_translations(
                        term_obj, data['translations'], request.user, project)
                    imported += 1

        return JsonResponse({'imported': imported, 'updated': updated, 'skipped': skipped, 'warnings': warnings})


class GlossaryExtractionAPI(generics.GenericAPIView):
    throttle_classes = [AICallRateThrottle]

    def get(self, request, pk):
        project = get_project_any_role(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        job = GlossaryExtractionJob.objects.filter(project=project).first()
        if not job:
            return JsonResponse({'error': 'No extraction job found'}, status=status.HTTP_404_NOT_FOUND)
        return JsonResponse(GlossaryExtractionJobSerializer(job).data)

    def post(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        if not ProjectAIProvider.objects.filter(project=project).exists():
            return JsonResponse({'error': 'No AI provider configured'}, status=status.HTTP_400_BAD_REQUEST)

        active = GlossaryExtractionJob.objects.filter(
            project=project,
            status__in=[GlossaryExtractionJob.Status.pending,
                        GlossaryExtractionJob.Status.running]
        ).exists()
        if active:
            return JsonResponse(
                {'error': 'An extraction job is already running'},
                status=status.HTTP_409_CONFLICT
            )

        job = GlossaryExtractionJob.objects.create(
            project=project, created_by=request.user)
        async_task('api.tasks.run_glossary_extraction_job', job.pk)
        return JsonResponse(GlossaryExtractionJobSerializer(job).data, status=status.HTTP_201_CREATED)


class GlossarySuggestionsAPI(generics.GenericAPIView):
    throttle_classes = [AICallRateThrottle]

    def get(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        job = GlossaryExtractionJob.objects.filter(
            project=project, status=GlossaryExtractionJob.Status.complete
        ).first()
        if not job or not job.suggestions:
            return JsonResponse([], safe=False)
        return JsonResponse(job.suggestions, safe=False)

    def patch(self, request, pk):
        project = get_project_admin(pk, request.user)
        if not project:
            return JsonResponse({'error': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)

        job = GlossaryExtractionJob.objects.filter(
            project=project, status=GlossaryExtractionJob.Status.complete
        ).select_for_update().first()
        if not job or not job.suggestions:
            return JsonResponse({'error': 'No completed extraction job with suggestions'}, status=status.HTTP_404_NOT_FOUND)

        index = request.data.get('index')
        action = request.data.get('action')
        if index is None or action not in ('accept', 'reject'):
            return JsonResponse({'error': 'index and action (accept|reject) are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            index = int(index)
            suggestion = job.suggestions[index]
        except (IndexError, TypeError, ValueError):
            return JsonResponse({'error': 'Invalid index'}, status=status.HTTP_400_BAD_REQUEST)

        if suggestion.get('status') in ('accepted', 'rejected'):
            return JsonResponse({'error': 'Suggestion already reviewed'}, status=status.HTTP_409_CONFLICT)

        if action == 'reject':
            job.suggestions[index]['status'] = 'rejected'
            job.save(update_fields=['suggestions'])
            return JsonResponse({'suggestion': job.suggestions[index]})

        term_value = (request.data.get('term')
                      or suggestion.get('term', '')).strip()
        definition = request.data.get(
            'definition', suggestion.get('definition', ''))
        translations_data = request.data.get(
            'translations', suggestion.get('translations', []))

        if not term_value:
            return JsonResponse({'error': 'term is required'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            existing = GlossaryTerm.objects.filter(
                project=project, term__iexact=term_value).first()
            if existing:
                existing.definition = definition
                existing.save(update_fields=['definition', 'updated_at'])
                existing.translations.all().delete()
                _save_translations(
                    existing, translations_data, request.user, project)
            else:
                new_term = GlossaryTerm.objects.create(
                    project=project,
                    term=term_value,
                    definition=definition,
                    case_sensitive=False,
                    created_by=request.user,
                )
                _save_translations(
                    new_term, translations_data, request.user, project)
            job.suggestions[index]['status'] = 'accepted'
            job.save(update_fields=['suggestions'])

        return JsonResponse({'suggestion': job.suggestions[index]})
