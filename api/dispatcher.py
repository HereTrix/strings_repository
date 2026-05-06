import logging
from datetime import datetime, timezone

from django_q.tasks import async_task

logger = logging.getLogger(__name__)


def _render_template(template: str, context: dict) -> str:
    result = template
    for key, value in context.items():
        result = result.replace(f'{{{{{key}}}}}', str(value) if value is not None else '')
    return result


def dispatch_event(project_id: int, event_type: str, payload: dict, actor: str = None):
    """
    Find all active webhook endpoints for the project subscribed to event_type
    and queue delivery via Django Q.
    """
    from api.models.webhook import WebhookEndpoint

    # Fetch active endpoints and filter by subscribed event in Python.
    # JSONField list containment is not reliably supported across all DB backends.
    all_endpoints = WebhookEndpoint.objects.filter(project_id=project_id, is_active=True)
    endpoints = [e for e in all_endpoints if event_type in e.events]

    if not endpoints:
        return

    full_payload = {
        'event': event_type,
        'project_id': project_id,
        'actor': actor,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': payload,
    }

    for endpoint in endpoints:
        if endpoint.template:
            context = {**payload, 'event': event_type, 'actor': actor or ''}
            send_payload = {'text': _render_template(endpoint.template, context)}
        else:
            send_payload = full_payload

        async_task('api.tasks.send_webhook', endpoint.pk, event_type, send_payload)
