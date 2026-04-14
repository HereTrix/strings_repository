import hashlib
import hmac
import json
import logging
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _render_template(template: str, context: dict) -> str:
    """Simple {{key}} substitution for message templates."""
    result = template
    for key, value in context.items():
        result = result.replace(f'{{{{{key}}}}}', str(value) if value is not None else '')
    return result


def _send_webhook(endpoint_id: int, event_type: str, payload: dict):
    """Executed in a background thread. Delivers payload and logs the result."""
    from api.crypto import decrypt
    from api.models.webhook import WebhookDeliveryLog, WebhookEndpoint

    try:
        endpoint = WebhookEndpoint.objects.get(pk=endpoint_id, is_active=True)
    except WebhookEndpoint.DoesNotExist:
        return

    body = json.dumps(payload).encode('utf-8')
    signature = hmac.new(endpoint.signing_secret.encode(), body, hashlib.sha256).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-Signature': f'sha256={signature}',
    }

    if endpoint.auth_token:
        try:
            headers['Authorization'] = f'Bearer {decrypt(endpoint.auth_token)}'
        except Exception:
            pass

    url = decrypt(endpoint.url)
    log = WebhookDeliveryLog(endpoint=endpoint, event_type=event_type, payload_sent=payload)

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.status_code = resp.status
    except urllib.error.HTTPError as e:
        log.status_code = e.code
        log.error = str(e)
    except Exception as e:
        log.error = str(e)
        logger.warning('Webhook delivery failed for endpoint %s: %s', endpoint_id, e)
    finally:
        log.save()


def dispatch_event(project_id: int, event_type: str, payload: dict, actor: str = None):
    """
    Find all active webhook endpoints for the project subscribed to event_type
    and deliver the event in background threads.
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

        threading.Thread(
            target=_send_webhook,
            args=(endpoint.pk, event_type, send_payload),
            daemon=True,
        ).start()
