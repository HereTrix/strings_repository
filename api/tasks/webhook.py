import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request

from api.url_validation import validate_url_for_outbound

logger = logging.getLogger(__name__)


def send_webhook(endpoint_id: int, event_type: str, payload: dict):
    """Django Q task: deliver a webhook payload and log the result."""
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
    try:
        validate_url_for_outbound(url)
    except ValueError as e:
        logger.warning('Webhook endpoint %s blocked by SSRF guard: %s', endpoint_id, e)
        return

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
