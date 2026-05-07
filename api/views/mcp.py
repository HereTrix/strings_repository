import difflib
import json
import random
import re

from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response

from api.models.history import HistoryRecord
from api.models.language import Language
from api.models.string_token import StringToken
from api.models.tag import Tag
from api.models.translations import Translation
from api.views.plugin import AccessTokenAuth

_TM_FLOOR = 0.60
_TM_MAX_RETURN = 5
_TM_MAX_SCAN = 500
_TM_SOURCE_TRUNCATE = 500

# Tool schemas

_TOOLS = [
    {
        "name": "get_project",
        "description": "Get the project associated with the configured access token.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_languages",
        "description": "List all language codes configured for the project.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_tokens",
        "description": "List localization keys in the project with optional filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Filter by key name or translation text"},
                "tags": {"type": "string", "description": "Comma-separated tag names to filter by"},
                "limit": {"type": "integer", "default": 50},
                "offset": {"type": "integer", "default": 0},
            },
            "required": [],
        },
    },
    {
        "name": "get_token",
        "description": "Get a localization key with all its translations across every language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_key": {"type": "string", "description": "The key name, e.g. 'onboarding.title'"},
            },
            "required": ["token_key"],
        },
    },
    {
        "name": "create_token",
        "description": "Create a new localization key. Returns an error if the key already exists.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_key": {"type": "string"},
                "comment": {"type": "string", "default": ""},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tag names to attach",
                },
            },
            "required": ["token_key"],
        },
    },
    {
        "name": "set_translation",
        "description": "Create or update a translation for a key in a given language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_key": {"type": "string"},
                "language_code": {"type": "string", "description": "Language code, e.g. 'EN' or 'FR'"},
                "text": {"type": "string"},
            },
            "required": ["token_key", "language_code", "text"],
        },
    },
    # Phase 2
    {
        "name": "search_similar_tokens",
        "description": "Search for existing keys whose name or translations resemble the given text. Use this to avoid creating duplicates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["text"],
        },
    },
    {
        "name": "suggest_token_key",
        "description": "Suggest a key name derived from source text following common naming conventions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {"type": "string"},
                "existing_tokens": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Already-used key names, to avoid collisions",
                },
            },
            "required": ["source_text"],
        },
    },
    {
        "name": "get_token_naming_patterns",
        "description": "Analyse a sample of existing keys to infer this project's naming conventions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sample_size": {"type": "integer", "default": 50},
            },
            "required": [],
        },
    },
    {
        "name": "batch_create_tokens",
        "description": "Create multiple localization keys with default-language translations in one call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "token_key": {"type": "string"},
                            "comment": {"type": "string"},
                            "language_code": {"type": "string"},
                            "text": {"type": "string"},
                        },
                        "required": ["token_key"],
                    },
                },
            },
            "required": ["entries"],
        },
    },
    {
        "name": "check_glossary",
        "description": "Check whether any words or phrases in a source string match project glossary terms. Returns matched terms with their definitions and preferred translations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {
                    "type": "string",
                    "description": "The source string to check against the glossary",
                },
                "language_code": {
                    "type": "string",
                    "description": "Optional target language code (e.g. 'DE'). When provided, includes preferred_translation for that language.",
                },
            },
            "required": ["source_text"],
        },
    },
    {
        "name": "suggest_translation",
        "description": "Return translation memory suggestions: previously-translated strings with source text similar to the given source_text, translated into the specified language.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {"type": "string"},
                "language_code": {
                    "type": "string",
                    "description": "Target language code, e.g. 'DE'",
                },
            },
            "required": ["source_text", "language_code"],
        },
    },
    {
        "name": "verify_string",
        "description": (
            "Run AI quality verification on a single source/translation pair. "
            "Requires the project to have an AI provider configured. "
            "Returns severity ('ok', 'warning', or 'error'), a suggested correction, and the reason. "
            "Note: response time depends on the AI provider (may take several seconds)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {
                    "type": "string",
                    "description": "The source (default-language) string",
                },
                "translation_text": {
                    "type": "string",
                    "description": "The translation to verify",
                },
                "language_code": {
                    "type": "string",
                    "description": "The target language code, e.g. 'DE'",
                },
                "checks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional list of check keys to run. "
                        "Defaults to all translation_accuracy checks. "
                        "Valid values: semantic_accuracy, placeholder_preservation, "
                        "omissions_additions, grammar_target, tone_match."
                    ),
                },
            },
            "required": ["source_text", "translation_text", "language_code"],
        },
    },
]

# View


class McpView(APIView):
    """Single endpoint implementing the MCP Streamable HTTP transport."""
    authentication_classes = [AccessTokenAuth]
    permission_classes = []

    def get(self, request):
        return Response({"name": "strings-repository", "version": "1.0", "protocol": "2024-11-05"})

    def post(self, request):
        access = request.auth

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return self._error(None, -32700, "Parse error")

        id_ = body.get('id')
        method = body.get('method', '')
        params = body.get('params') or {}

        if method == 'initialize':
            return self._initialize(id_)
        if method == 'tools/list':
            return self._tools_list(id_)
        if method == 'tools/call':
            return self._tools_call(id_, params, access)
        if method.startswith('notifications/'):
            return Response({})
        return self._error(id_, -32601, f"Method not found: {method}")

    # Protocol handlers

    def _initialize(self, id_):
        return Response({
            "jsonrpc": "2.0", "id": id_,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "strings-repository", "version": "1.0"},
            },
        })

    def _tools_list(self, id_):
        return Response({"jsonrpc": "2.0", "id": id_, "result": {"tools": _TOOLS}})

    def _tools_call(self, id_, params, access):
        name = params.get('name')
        args = params.get('arguments') or {}

        _handlers = {
            'get_project': self._tool_get_project,
            'get_languages': self._tool_get_languages,
            'list_tokens': self._tool_list_tokens,
            'get_token': self._tool_get_token,
            'create_token': self._tool_create_token,
            'set_translation': self._tool_set_translation,
            'search_similar_tokens': self._tool_search_similar_tokens,
            'suggest_token_key': self._tool_suggest_token_key,
            'get_token_naming_patterns': self._tool_get_token_naming_patterns,
            'batch_create_tokens': self._tool_batch_create_tokens,
            'check_glossary': self._tool_check_glossary,
            'suggest_translation': self._tool_suggest_translation,
            'verify_string': self._tool_verify_string,
        }

        handler = _handlers.get(name)
        if not handler:
            return self._error(id_, -32601, f"Unknown tool: {name}")

        try:
            result = handler(args, access)
        except Exception as exc:
            return self._error(id_, -32603, str(exc))

        return Response({
            "jsonrpc": "2.0", "id": id_,
            "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
        })

    def _error(self, id_, code, message):
        return Response({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})

    # Developer tools

    def _tool_get_project(self, args, access):
        p = access.project
        return {"id": p.id, "name": p.name, "description": p.description}

    def _tool_get_languages(self, args, access):
        codes = list(Language.objects.filter(
            project=access.project).values_list('code', flat=True))
        return {"languages": codes}

    def _tool_list_tokens(self, args, access):
        qs = StringToken.objects.filter(project=access.project)
        q = args.get('search')
        tags = args.get('tags')
        limit = max(1, min(int(args.get('limit', 50)), 200))
        offset = max(0, int(args.get('offset', 0)))

        if q:
            qs = qs.filter(Q(token__icontains=q) | Q(
                translation__translation__icontains=q))
        if tags:
            for tag in tags.split(','):
                qs = qs.filter(tags__tag=tag.strip())

        qs = qs.distinct().prefetch_related('tags')
        total = qs.count()
        page = list(qs[offset:offset + limit])

        return {
            "count": total,
            "results": [
                {
                    "id": t.id,
                    "token": t.token,
                    "comment": t.comment,
                    "status": t.status,
                    "tags": [tag.tag for tag in t.tags.all()],
                }
                for t in page
            ],
        }

    def _tool_get_token(self, args, access):
        token_key = args.get('token_key')
        try:
            token = StringToken.objects.prefetch_related('tags', 'translation__language').get(
                token=token_key, project=access.project
            )
        except StringToken.DoesNotExist:
            raise ValueError(f"Token '{token_key}' not found")

        return {
            "id": token.id,
            "token": token.token,
            "comment": token.comment,
            "status": token.status,
            "tags": [tag.tag for tag in token.tags.all()],
            "translations": [
                {"language": t.language.code,
                    "text": t.translation, "status": t.status}
                for t in token.translation.select_related('language').all()
            ],
        }

    def _tool_create_token(self, args, access):
        if access.permission == access.__class__.AccessTokenPermissions.read:
            raise PermissionError("Write permission required")

        token_key = args.get('token_key', '').strip()
        if not token_key:
            raise ValueError("token_key is required")

        if StringToken.objects.filter(token=token_key, project=access.project).exists():
            raise ValueError(
                f"Token '{token_key}' already exists. Use set_translation to add translations.")

        token = StringToken.objects.create(
            token=token_key,
            comment=args.get('comment', ''),
            project=access.project,
        )

        tag_names = args.get('tags') or []
        for tag_name in tag_names:
            tag, _ = Tag.objects.get_or_create(tag=tag_name)
            token.tags.add(tag)

        HistoryRecord.objects.create(
            project=access.project,
            token=token.token,
            status=HistoryRecord.Status.created,
            editor=access.user,
        )

        return {"id": token.id, "token": token.token, "comment": token.comment, "status": token.status, "tags": tag_names}

    def _tool_set_translation(self, args, access):
        if access.permission == access.__class__.AccessTokenPermissions.read:
            raise PermissionError("Write permission required")

        token_key = args.get('token_key')
        language_code = args.get('language_code', '').upper()
        text = args.get('text', '')

        try:
            token = StringToken.objects.get(
                token=token_key, project=access.project)
        except StringToken.DoesNotExist:
            raise ValueError(
                f"Token '{token_key}' not found. Create it first with create_token.")

        Translation.create_or_update_translation(
            user=access.user,
            token=token,
            code=language_code,
            project_id=access.project.id,
            text=text,
        )
        return {"token": token_key, "language": language_code, "text": text}

    # LLM tools

    def _tool_search_similar_tokens(self, args, access):
        text = args.get('text', '')
        limit = max(1, min(int(args.get('limit', 10)), 50))

        qs = StringToken.objects.filter(
            project=access.project,
        ).filter(
            Q(token__icontains=text) | Q(
                translation__translation__icontains=text)
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

    def _tool_suggest_token_key(self, args, access):
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

    def _tool_get_token_naming_patterns(self, args, access):
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

        top_prefixes = sorted(
            prefixes, key=prefixes.__getitem__, reverse=True)[:5]

        return {
            "separator": separator,
            "dot_separator_count": dot_count,
            "underscore_separator_count": underscore_count,
            "common_prefixes": top_prefixes,
            "examples": tokens[:10],
        }

    def _tool_batch_create_tokens(self, args, access):
        if access.permission == access.__class__.AccessTokenPermissions.read:
            raise PermissionError("Write permission required")

        entries = args.get('entries') or []
        created, skipped, failed = [], [], []

        for entry in entries:
            token_key = entry.get('token_key', '').strip()
            if not token_key:
                failed.append(
                    {"token_key": token_key, "error": "token_key is required"})
                continue

            try:
                if StringToken.objects.filter(token=token_key, project=access.project).exists():
                    skipped.append(token_key)
                    continue

                token = StringToken.objects.create(
                    token=token_key,
                    comment=entry.get('comment', ''),
                    project=access.project,
                )

                language_code = entry.get('language_code', '').upper()
                text = entry.get('text', '')
                if language_code and text:
                    Translation.create_or_update_translation(
                        user=access.user,
                        token=token,
                        code=language_code,
                        project_id=access.project.id,
                        text=text,
                    )

                HistoryRecord.objects.create(
                    project=access.project,
                    token=token.token,
                    status=HistoryRecord.Status.created,
                    editor=access.user,
                )
                created.append(token_key)

            except Exception as exc:
                failed.append({"token_key": token_key, "error": str(exc)})

        return {"created": created, "skipped": skipped, "failed": failed}

    def _tool_check_glossary(self, args, access):
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

    def _tool_suggest_translation(self, args, access):
        from django.db.models import OuterRef, Subquery

        from api.models.language import Language
        from api.models.string_token import StringToken
        from api.models.translations import Translation

        source_text = args.get('source_text', '').strip()
        lang_code = args.get('language_code', '').strip().upper()

        if not source_text or not lang_code:
            return {'suggestions': []}

        if not Language.objects.filter(project=access.project, code=lang_code).exists():
            raise ValueError(f"Language '{lang_code}' not found in project")

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

    def _tool_verify_string(self, args, access):
        from api.verification_providers import get_verification_provider
        from api.views.verification import MODE_CHECKS
        from api.models.verification import VerificationReport

        source_text = args.get('source_text', '').strip()
        translation_text = args.get('translation_text', '').strip()
        lang_code = args.get('language_code', '').strip().upper()

        if not source_text or not translation_text or not lang_code:
            raise ValueError(
                'source_text, translation_text, and language_code are required')

        try:
            ai_provider = access.project.ai_provider
        except Exception:
            raise ValueError('No AI provider configured for this project')

        all_accuracy_checks = [
            c for c in MODE_CHECKS[VerificationReport.Mode.translation_accuracy]
            if c != 'glossary_compliance'
        ]
        requested = args.get('checks') or []
        if requested:
            effective_checks = [
                c for c in requested if c in all_accuracy_checks]
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
        results = provider.verify(
            items, effective_checks, access.project.description or '')

        if not results:
            return {'severity': 'ok', 'suggestion': '', 'reason': 'No issues found.'}

        r = results[0]
        return {
            'severity': r.get('severity', 'ok'),
            'suggestion': r.get('suggestion', ''),
            'reason': r.get('reason', ''),
        }
