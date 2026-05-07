import logging
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

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
        _fail_extraction_job(
            job, 'No AI provider configured for this project.')
        return

    source_lang = Language.objects.filter(
        project=job.project, is_default=True).first()
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
        suggestions = provider.extract_glossary(
            strings, job.project.description or '')
    except Exception as e:
        logger.exception('Glossary extraction job %s failed: %s', job_id, e)
        _fail_extraction_job(job, 'Extraction job failed')
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
