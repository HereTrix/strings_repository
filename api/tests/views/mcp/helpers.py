import json

from api.crypto import encrypt
from api.models.project import ProjectAIProvider


def mcp_call(client, token, tool_name, arguments):
    return client.post(
        '/api/mcp',
        data=json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }),
        content_type='application/json',
        HTTP_ACCESS_TOKEN=token.token,
    )


def get_result(response):
    return json.loads(response.json()['result']['content'][0]['text'])


def get_error(response):
    return response.json().get('error', {}).get('message', '')


def make_ai_provider(project):
    return ProjectAIProvider.objects.create(
        project=project,
        provider_type='openai',
        model_name='gpt-4o-mini',
        endpoint_url='',
        api_key=encrypt('sk-test'),
    )
