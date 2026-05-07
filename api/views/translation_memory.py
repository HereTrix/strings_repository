import difflib
import random

from django.db.models import OuterRef, Subquery
from rest_framework.response import Response
from rest_framework import generics, status

from api.models.language import Language
from api.models.project import ProjectAIProvider
from api.models.string_token import StringToken
from api.models.translations import Translation
from api.throttles import AICallRateThrottle
from api.verification_providers import get_verification_provider
from api.views.helper import get_project_any_role

MAX_SCAN = 500       # random-sample cap for large projects
TM_RETURN = 5        # max suggestions returned
AI_POOL = 20         # candidates sent to AI for re-ranking
AI_FLOOR = 0.40      # minimum difflib ratio to include in AI pool
MANUAL_FLOOR = 0.60  # minimum difflib ratio for manual-only results
SOURCE_TRUNCATE = 500  # chars used for similarity scoring


class TranslationMemoryAPI(generics.GenericAPIView):
    throttle_classes = [AICallRateThrottle]

    def get(self, request, pk):
        project = get_project_any_role(pk, request.user)
        if not project:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        token_key = request.query_params.get('token', '').strip()
        lang_code = request.query_params.get('language', '').strip().upper()

        if not token_key or not lang_code:
            return Response(
                {'error': 'token and language are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        source_lang = Language.objects.filter(
            project=project, is_default=True).first()
        if not source_lang:
            return Response([])

        # Current token's source text
        current_source = (
            Translation.objects.filter(
                token__token=token_key,
                token__project=project,
                language=source_lang,
            )
            .values_list('translation', flat=True)
            .first()
        ) or ''

        if not current_source.strip():
            return Response([])

        use_ai = ProjectAIProvider.objects.filter(project=project).exists()
        floor = AI_FLOOR if use_ai else MANUAL_FLOOR
        pool_size = AI_POOL if use_ai else TM_RETURN

        # Single query: all target-language translations with annotated source text
        source_subquery = Translation.objects.filter(
            token=OuterRef('token'),
            language=source_lang,
        ).values('translation')[:1]

        candidates_qs = (
            Translation.objects.filter(
                token__project=project,
                token__status=StringToken.Status.active,
                language__code=lang_code,
            )
            .exclude(token__token=token_key)
            .select_related('token')
            .annotate(source_text=Subquery(source_subquery))
            .order_by('token__token')  # deterministic
        )

        # Cap large projects with random sampling
        total = candidates_qs.count()
        if total > 2000:
            all_pks = list(candidates_qs.values_list('pk', flat=True))
            sampled_pks = random.sample(all_pks, MAX_SCAN)
            candidates_qs = candidates_qs.filter(pk__in=sampled_pks)

        # Score with difflib
        current_trunc = current_source[:SOURCE_TRUNCATE]
        scored = []
        for c in candidates_qs:
            src = (c.source_text or '')[:SOURCE_TRUNCATE]
            if not src:
                continue
            score = difflib.SequenceMatcher(None, current_trunc, src).ratio()
            if score >= floor:
                scored.append({
                    'token_key': c.token.token,
                    'source_text': c.source_text or '',
                    'translation_text': c.translation,
                    'similarity_score': round(score, 4),
                })

        # Sort by score descending
        scored.sort(key=lambda x: x['similarity_score'], reverse=True)

        if not scored:
            return Response([])

        # AI re-ranking
        if use_ai:
            pool = scored[:pool_size]
            try:
                ai_provider = project.ai_provider
                provider = get_verification_provider(ai_provider)
                pool = provider.rank_by_similarity(current_source, pool)
            except Exception:
                pass  # silent fallback to difflib order
            scored = pool

        return Response(scored[:TM_RETURN])
