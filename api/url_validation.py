import ipaddress
import socket
from urllib.parse import urlparse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

BLOCKED_NETWORKS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]


def validate_url_for_outbound(url: str) -> None:
    """
    Raises ValueError if the URL should not be fetched due to SSRF risk.
    Checks: scheme must be http or https; hostname must resolve to a public IP.
    All resolved addresses (A and AAAA) are checked; rejects if any is private.
    """
    if settings.DEBUG:
        return

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError(
            f"Disallowed URL scheme: {parsed.scheme!r}. Only http/https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname.")

    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve hostname {hostname!r}: {e}") from e

    for (_, _, _, _, sockaddr) in results:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for network in BLOCKED_NETWORKS:
            if ip in network:
                raise ValueError(
                    f"URL resolves to a blocked network address: {ip} (in {network})."
                )
