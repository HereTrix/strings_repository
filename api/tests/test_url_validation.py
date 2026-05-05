import socket
from unittest.mock import patch
from django.test import TestCase

from api.url_validation import validate_url_for_outbound


def _mock_addr(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, '', (ip, 0))]


def _mock_addr6(ip):
    return [(socket.AF_INET6, socket.SOCK_STREAM, 0, '', (ip, 0, 0, 0))]


class UrlValidationTest(TestCase):

    def test_http_public_url_passes(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr('8.8.8.8')):
            validate_url_for_outbound('http://example.com/path')

    def test_https_public_url_passes(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr('8.8.8.8')):
            validate_url_for_outbound('https://example.com/path')

    def test_file_scheme_raises(self):
        with self.assertRaises(ValueError) as ctx:
            validate_url_for_outbound('file:///etc/passwd')
        self.assertIn('Disallowed URL scheme', str(ctx.exception))

    def test_ftp_scheme_raises(self):
        with self.assertRaises(ValueError) as ctx:
            validate_url_for_outbound('ftp://example.com')
        self.assertIn('Disallowed URL scheme', str(ctx.exception))

    def test_no_hostname_raises(self):
        with self.assertRaises(ValueError) as ctx:
            validate_url_for_outbound('http://')
        self.assertIn('hostname', str(ctx.exception))

    def test_dns_failure_raises(self):
        with patch('socket.getaddrinfo', side_effect=socket.gaierror('nxdomain')):
            with self.assertRaises(ValueError) as ctx:
                validate_url_for_outbound('http://nonexistent.invalid')
        self.assertIn('Cannot resolve hostname', str(ctx.exception))

    def test_loopback_127_raises(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr('127.0.0.1')):
            with self.assertRaises(ValueError):
                validate_url_for_outbound('http://localhost')

    def test_private_10_raises(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr('10.0.1.50')):
            with self.assertRaises(ValueError):
                validate_url_for_outbound('http://internal.corp')

    def test_link_local_169_raises(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr('169.254.169.254')):
            with self.assertRaises(ValueError):
                validate_url_for_outbound('http://metadata.aws')

    def test_ipv6_loopback_raises(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr6('::1')):
            with self.assertRaises(ValueError):
                validate_url_for_outbound('http://localhost6')

    def test_ipv6_ula_raises(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr6('fc00::1')):
            with self.assertRaises(ValueError):
                validate_url_for_outbound('http://ula.host')

    def test_ipv6_link_local_raises(self):
        with patch('socket.getaddrinfo', return_value=_mock_addr6('fe80::1')):
            with self.assertRaises(ValueError):
                validate_url_for_outbound('http://linklocal.host')

    def test_round_robin_one_private_raises(self):
        mixed = _mock_addr('8.8.8.8') + _mock_addr('192.168.1.1')
        with patch('socket.getaddrinfo', return_value=mixed):
            with self.assertRaises(ValueError):
                validate_url_for_outbound('http://roundrobin.example.com')
