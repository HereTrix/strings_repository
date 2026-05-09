# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

import difflib
import random
import re

from django.db.models import Q

from api.models.string_token import StringToken

_TM_FLOOR = 0.60
_TM_MAX_RETURN = 5
_TM_MAX_SCAN = 500
_TM_SOURCE_TRUNCATE = 500


class NotFoundException(Exception):
    ...


class AIProviderNotConfigured(Exception):
    ...


def search_similar_tokens(args, access):
    text = args.get('text', '')
    limit = max(1, min(int(args.get('limit', 10)), 50))

    qs = StringToken.objects.filter(
        project=access.project,
    ).filter(
        Q(token__icontains=text) | Q(translation__translation__icontains=text)
    ).distinct().prefetch_related('translation__language')[:limit]

    return {
        "results": [
            {
                "token": t.token,
                "comment": t.comment,
                "translations": [
                    {"language": tr.language.code, "text": tr.translation}
                    for tr in t.translation.select_related('language').all()
                ],
            }
            for t in qs
        ]
    }


def suggest_token_key(args, access):
    source_text = args.get('source_text', '')
    existing = set(args.get('existing_tokens') or [])

    words = re.sub(r"[^a-z0-9\s]", "", source_text.lower()).split()
    candidate = "_".join(words[:5]) or "key"

    base = candidate
    n = 2
    while candidate in existing:
        candidate = f"{base}_{n}"
        n += 1

    return {"suggested_key": candidate, "rationale": f"First 5 significant words of '{source_text}', underscored"}


def get_token_naming_patterns(args, access):
    sample_size = max(1, min(int(args.get('sample_size', 50)), 200))
    tokens = list(
        StringToken.objects.filter(project=access.project)
        .values_list('token', flat=True)[:sample_size]
    )

    dot_count = sum(1 for t in tokens if '.' in t)
    underscore_count = sum(1 for t in tokens if '_' in t and '.' not in t)
    separator = 'dot' if dot_count >= underscore_count else 'underscore'

    prefixes: dict[str, int] = {}
    for t in tokens:
        parts = re.split(r'[._]', t)
        if parts:
            prefixes[parts[0]] = prefixes.get(parts[0], 0) + 1

    top_prefixes = sorted(prefixes, key=prefixes.__getitem__, reverse=True)[:5]

    return {
        "separator": separator,
        "dot_separator_count": dot_count,
        "underscore_separator_count": underscore_count,
        "common_prefixes": top_prefixes,
        "examples": tokens[:10],
    }


def check_glossary(args, access):
    source_text = args.get('source_text', '')
    if not source_text:
        return {'matches': []}

    language_code = args.get('language_code', '').strip().upper() or None

    try:
        from api.models.glossary import GlossaryTerm
        terms = GlossaryTerm.objects.filter(
            project=access.project
        ).prefetch_related('translations')
    except Exception:
        raise ValueError('Glossary feature not available')

    matches = []
    for term in terms:
        if term.case_sensitive:
            found = term.term in source_text
        else:
            found = term.term.lower() in source_text.lower()

        if not found:
            continue

        preferred_translation = None
        if language_code:
            preferred_translation = next(
                (
                    t.preferred_translation
                    for t in term.translations.all()
                    if t.language_code.upper() == language_code
                ),
                None,
            )

        matches.append({
            'term': term.term,
            'definition': term.definition,
            'case_sensitive': term.case_sensitive,
            'preferred_translation': preferred_translation,
        })

    return {'matches': matches}


def suggest_translation(args, access):
    from django.db.models import OuterRef, Subquery

    from api.models.language import Language
    from api.models.translations import Translation

    source_text = args.get('source_text', '').strip()
    lang_code = args.get('language_code', '').strip().upper()

    if not source_text or not lang_code:
        return {'suggestions': []}

    if not Language.objects.filter(project=access.project, code=lang_code).exists():
        raise NotFoundException(f"Language '{lang_code}' not found in project")

    source_lang = Language.objects.filter(
        project=access.project, is_default=True
    ).first()
    if not source_lang:
        return {'suggestions': []}

    source_subquery = Translation.objects.filter(
        token=OuterRef('token'),
        language=source_lang,
    ).values('translation')[:1]

    candidates_qs = (
        Translation.objects.filter(
            token__project=access.project,
            token__status=StringToken.Status.active,
            language__code=lang_code,
        )
        .select_related('token')
        .annotate(source_text_val=Subquery(source_subquery))
        .order_by('token__token')
    )

    total = candidates_qs.count()
    if total > 2000:
        all_pks = list(candidates_qs.values_list('pk', flat=True))
        sampled_pks = random.sample(all_pks, _TM_MAX_SCAN)
        candidates_qs = candidates_qs.filter(pk__in=sampled_pks)

    current_trunc = source_text[:_TM_SOURCE_TRUNCATE]
    scored = []
    for c in candidates_qs:
        src = (c.source_text_val or '')[:_TM_SOURCE_TRUNCATE]
        if not src:
            continue
        score = difflib.SequenceMatcher(None, current_trunc, src).ratio()
        if score >= _TM_FLOOR:
            scored.append({
                'token_key': c.token.token,
                'source_text': c.source_text_val or '',
                'translation_text': c.translation,
                'similarity_score': round(score, 4),
            })

    scored.sort(key=lambda x: x['similarity_score'], reverse=True)
    return {'suggestions': scored[:_TM_MAX_RETURN]}


def verify_string(args, access):
    from api.verification_providers import get_verification_provider
    from api.views.verification import MODE_CHECKS
    from api.models.verification import VerificationReport

    source_text = args.get('source_text', '').strip()
    translation_text = args.get('translation_text', '').strip()
    lang_code = args.get('language_code', '').strip().upper()

    if not source_text or not translation_text or not lang_code:
        raise ValueError('source_text, translation_text, and language_code are required')

    try:
        ai_provider = access.project.ai_provider
    except Exception:
        raise AIProviderNotConfigured('No AI provider configured for this project')

    all_accuracy_checks = [
        c for c in MODE_CHECKS[VerificationReport.Mode.translation_accuracy]
        if c != 'glossary_compliance'
    ]
    requested = args.get('checks') or []
    if requested:
        effective_checks = [c for c in requested if c in all_accuracy_checks]
        if not effective_checks:
            effective_checks = all_accuracy_checks
    else:
        effective_checks = all_accuracy_checks

    items = [{
        'token_id': 0,
        'token_key': 'mcp_verify',
        'language': lang_code,
        'plural_form': None,
        'source': source_text,
        'current': translation_text,
        'placeholders': [],
    }]

    provider = get_verification_provider(ai_provider)
    results = provider.verify(items, effective_checks, access.project.description or '')

    if not results:
        return {'severity': 'ok', 'suggestion': '', 'reason': 'No issues found.'}

    r = results[0]
    return {
        'severity': r.get('severity', 'ok'),
        'suggestion': r.get('suggestion', ''),
        'reason': r.get('reason', ''),
    }
