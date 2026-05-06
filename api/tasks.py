import logging
import random
import re
from datetime import datetime, timezone

from django.db import transaction

logger = logging.getLogger(__name__)

VERIFY_BATCH_SIZE = 20

PLACEHOLDER_RE = re.compile(
    r'%\d*\$?[sdcfg]'           # %s %d %1$s %2$d etc.
    r'|\{[a-zA-Z_]\w*\}'        # {name}
    r'|\{\{[a-zA-Z_]\w*\}\}'    # {{name}}
    r'|\$[a-zA-Z_]\w*\$'        # $name$
)


def _extract_placeholders(text: str) -> list[str]:
    return list(dict.fromkeys(PLACEHOLDER_RE.findall(text)))


def run_verification_job(report_id: int):
    from api.models.verification import VerificationReport
    from api.models.translations import Translation, PluralTranslation
    from api.models.string_token import StringToken
    from api.models.language import Language
    from api.verification_providers import get_verification_provider
    from api import dispatcher

    try:
        report = VerificationReport.objects.select_related(
            'project', 'project__ai_provider', 'scope', 'created_by'
        ).get(pk=report_id)
    except VerificationReport.DoesNotExist:
        logger.error('VerificationReport %s not found', report_id)
        return

    report.status = VerificationReport.Status.running
    report.save(update_fields=['status'])

    try:
        ai_provider = report.project.ai_provider
    except Exception:
        _fail(report, 'No AI provider configured for this project.')
        _fire_webhook(report)
        return

    source_lang = Language.objects.filter(
        project=report.project, is_default=True
    ).first()
    source_code = source_lang.code.upper() if source_lang else None

    items = []

    if report.mode == VerificationReport.Mode.source_quality:
        qs = StringToken.objects.filter(
            project=report.project,
            status=StringToken.Status.active,
        ).prefetch_related('translation', 'scopes', 'tags')

        if report.scope:
            qs = qs.filter(scopes=report.scope)
        if report.tags:
            qs = qs.filter(tags__tag__in=report.tags).distinct()

        for token in qs:
            source_translation = token.translation.filter(
                language__code=source_code
            ).first() if source_code else None
            source_text = source_translation.translation if source_translation else ''

            items.append({
                'token_id': token.pk,
                'token_key': token.token,
                'language': source_code or '',
                'plural_form': None,
                'source': source_text,
                'current': source_text,
                'placeholders': _extract_placeholders(source_text),
            })

            if source_translation:
                for pf in source_translation.plural_forms.all():
                    items.append({
                        'token_id': token.pk,
                        'token_key': token.token,
                        'language': source_code or '',
                        'plural_form': pf.plural_form,
                        'source': pf.value,
                        'current': pf.value,
                        'placeholders': _extract_placeholders(pf.value),
                    })

    else:
        qs = Translation.objects.filter(
            token__project=report.project,
            token__status=StringToken.Status.active,
            language__code=report.target_language.upper(),
        ).select_related('token', 'language').prefetch_related(
            'plural_forms', 'token__translation', 'token__scopes', 'token__tags'
        )

        if report.scope:
            qs = qs.filter(token__scopes=report.scope)
        if report.tags:
            qs = qs.filter(token__tags__tag__in=report.tags).distinct()
        if report.new_only:
            qs = qs.filter(status=Translation.Status.new)

        for tr in qs:
            source_tr = tr.token.translation.filter(
                language__code=source_code
            ).first() if source_code else None
            source_text = source_tr.translation if source_tr else ''

            items.append({
                'token_id': tr.token.pk,
                'token_key': tr.token.token,
                'language': tr.language.code.upper(),
                'plural_form': None,
                'source': source_text,
                'current': tr.translation,
                'placeholders': _extract_placeholders(source_text),
            })

            for pf in tr.plural_forms.all():
                source_pf = None
                if source_tr:
                    source_pf = source_tr.plural_forms.filter(
                        plural_form=pf.plural_form
                    ).first()
                source_pf_text = source_pf.value if source_pf else source_text

                items.append({
                    'token_id': tr.token.pk,
                    'token_key': tr.token.token,
                    'language': tr.language.code.upper(),
                    'plural_form': pf.plural_form,
                    'source': source_pf_text,
                    'current': pf.value,
                    'placeholders': _extract_placeholders(source_pf_text),
                })

    if not items:
        _fail(report, 'No strings matched the selected filters.')
        _fire_webhook(report)
        return

    report.string_count = len(items)
    report.save(update_fields=['string_count'])

    glossary_terms = []
    if 'glossary_compliance' in report.checks and report.mode == VerificationReport.Mode.translation_accuracy:
        from api.models.glossary import GlossaryTerm
        target_lang = report.target_language.upper()
        for gt in GlossaryTerm.objects.filter(project=report.project).prefetch_related('translations').order_by('term'):
            pref_tr = next(
                (t.preferred_translation for t in gt.translations.all() if t.language_code.upper() == target_lang),
                ''
            )
            glossary_terms.append({
                'term': gt.term,
                'case_sensitive': gt.case_sensitive,
                'preferred_translation': pref_tr,
            })

    try:
        provider = get_verification_provider(ai_provider)
        all_results = []
        for i in range(0, len(items), VERIFY_BATCH_SIZE):
            batch = items[i:i + VERIFY_BATCH_SIZE]
            batch_results = provider.verify(
                batch, report.checks, report.project.description or '',
                glossary_terms=glossary_terms,
            )
            all_results.extend(batch_results)
    except Exception as e:
        logger.exception('Verification job %s failed: %s', report_id, e)
        _fail(report, str(e))
        _fire_webhook(report)
        return

    ok = sum(1 for r in all_results if r.get('severity') == 'ok')
    warning = sum(1 for r in all_results if r.get('severity') == 'warning')
    error = sum(1 for r in all_results if r.get('severity') == 'error')

    items_by_token_form = {
        (item['token_id'], item['plural_form']): item for item in items
    }
    enriched = []
    for r in all_results:
        key = (r.get('token_id'), r.get('plural_form'))
        item = items_by_token_form.get(key, {})
        enriched.append({
            'token_id': r.get('token_id'),
            'token_key': item.get('token_key', ''),
            'language': item.get('language', ''),
            'plural_form': r.get('plural_form'),
            'current': item.get('current', ''),
            'suggestion': r.get('suggestion', ''),
            'severity': r.get('severity', 'ok'),
            'reason': r.get('reason', ''),
        })

    result_payload = {
        'results': enriched,
        'summary': {'ok': ok, 'warning': warning, 'error': error, 'total': len(all_results)},
    }

    with transaction.atomic():
        report.result = result_payload
        report.status = VerificationReport.Status.complete
        report.completed_at = datetime.now(timezone.utc)
        report.save(update_fields=['result', 'status', 'completed_at'])

        _enforce_cap(report.project)

    _fire_webhook(report)


def _fail(report, message: str):
    report.status = report.Status.failed
    report.error_message = message
    report.completed_at = datetime.now(timezone.utc)
    report.save(update_fields=['status', 'error_message', 'completed_at'])


def _enforce_cap(project):
    """Delete oldest reports exceeding project.verification_cap. Must run inside a transaction."""
    from api.models.verification import VerificationReport
    cap = project.verification_cap
    ids = list(
        VerificationReport.objects
        .filter(project=project)
        .order_by('-created_at')
        .values_list('pk', flat=True)
    )
    if len(ids) > cap:
        to_delete = ids[cap:]
        VerificationReport.objects.select_for_update().filter(pk__in=to_delete).delete()


def _fire_webhook(report):
    from api import dispatcher
    summary = {}
    if report.result and 'summary' in report.result:
        summary = report.result['summary']
    actor = report.created_by.email if report.created_by else None
    dispatcher.dispatch_event(
        project_id=report.project_id,
        event_type='verification.completed',
        payload={
            'report_id': report.pk,
            'mode': report.mode,
            'target_language': report.target_language,
            'status': report.status,
            'summary': summary,
        },
        actor=actor,
    )


EXTRACTION_STRING_CAP = 200


def run_glossary_extraction_job(job_id: int):
    from api.models.glossary import GlossaryExtractionJob
    from api.models.string_token import StringToken
    from api.models.translations import Translation
    from api.models.language import Language
    from api.verification_providers import get_verification_provider

    try:
        job = GlossaryExtractionJob.objects.select_related(
            'project', 'project__ai_provider', 'created_by'
        ).get(pk=job_id)
    except GlossaryExtractionJob.DoesNotExist:
        logger.error('GlossaryExtractionJob %s not found', job_id)
        return

    job.status = GlossaryExtractionJob.Status.running
    job.save(update_fields=['status'])

    try:
        ai_provider = job.project.ai_provider
    except Exception:
        _fail_extraction_job(job, 'No AI provider configured for this project.')
        return

    source_lang = Language.objects.filter(project=job.project, is_default=True).first()
    if source_lang:
        qs = Translation.objects.filter(
            token__project=job.project,
            token__status=StringToken.Status.active,
            language=source_lang,
        ).select_related('token').order_by('token__token')
        strings = [tr.translation for tr in qs if tr.translation.strip()]
    else:
        qs = StringToken.objects.filter(
            project=job.project, status=StringToken.Status.active
        ).order_by('token')
        strings = [t.token for t in qs if t.token.strip()]

    if len(strings) > EXTRACTION_STRING_CAP:
        strings = random.sample(strings, EXTRACTION_STRING_CAP)

    if not strings:
        _fail_extraction_job(job, 'No source strings found in project.')
        return

    try:
        provider = get_verification_provider(ai_provider)
        suggestions = provider.extract_glossary(strings, job.project.description or '')
    except Exception as e:
        logger.exception('Glossary extraction job %s failed: %s', job_id, e)
        _fail_extraction_job(job, str(e))
        return

    normalised = []
    for s in suggestions:
        if not isinstance(s, dict) or not s.get('term'):
            continue
        normalised.append({
            'term': str(s.get('term', '')).strip(),
            'definition': str(s.get('definition', '')).strip(),
            'translations': s.get('translations', []),
            'status': 'pending',
        })

    job.suggestions = normalised
    job.status = GlossaryExtractionJob.Status.complete
    job.completed_at = datetime.now(timezone.utc)
    job.save(update_fields=['suggestions', 'status', 'completed_at'])


def _fail_extraction_job(job, message: str):
    job.status = 'failed'
    job.error_message = message
    job.completed_at = datetime.now(timezone.utc)
    job.save(update_fields=['status', 'error_message', 'completed_at'])
