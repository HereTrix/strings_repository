import json
import logging

from rest_framework.views import APIView
from rest_framework.response import Response

from api.views.plugin import AccessTokenAuth
from .schemas import TOOLS
from . import tools_project, tools_tokens, tools_ai

logger = logging.getLogger(__name__)

_HANDLERS = {
    'get_project': tools_project.get_project,
    'get_languages': tools_project.get_languages,
    'list_tokens': tools_tokens.list_tokens,
    'get_token': tools_tokens.get_token,
    'create_token': tools_tokens.create_token,
    'set_translation': tools_tokens.set_translation,
    'batch_create_tokens': tools_tokens.batch_create_tokens,
    'search_similar_tokens': tools_ai.search_similar_tokens,
    'suggest_token_key': tools_ai.suggest_token_key,
    'get_token_naming_patterns': tools_ai.get_token_naming_patterns,
    'check_glossary': tools_ai.check_glossary,
    'suggest_translation': tools_ai.suggest_translation,
    'verify_string': tools_ai.verify_string,
}


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
        return Response({"jsonrpc": "2.0", "id": id_, "result": {"tools": TOOLS}})

    def _tools_call(self, id_, params, access):
        name = params.get('name')
        args = params.get('arguments') or {}

        handler = _HANDLERS.get(name)
        if not handler:
            return self._error(id_, -32601, f"Unknown tool: {name}")

        try:
            result = handler(args, access)
        except tools_ai.NotFoundException as e:
            logger.exception(e)
            return self._error(id_, -32603, "Item not found")
        except tools_ai.AIProviderNotConfigured as e:
            logger.exception(e)
            return self._error(id_, -32603, "No AI provider configured")
        except Exception:
            logger.exception("Unhandled exception while executing MCP tool '%s'", name)
            return self._error(id_, -32603, "Internal server error.")

        return Response({
            "jsonrpc": "2.0", "id": id_,
            "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
        })

    def _error(self, id_, code, message):
        return Response({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}})
