from rest_framework.throttling import SimpleRateThrottle


class LoginRateThrottle(SimpleRateThrottle):
    """IP-based throttle for the login endpoint."""
    scope = 'login'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class TwoFALoginRateThrottle(SimpleRateThrottle):
    """Per-user throttle for the 2FA login step."""
    scope = 'two_fa_login'

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk,
        }


class PasskeyAuthRateThrottle(SimpleRateThrottle):
    """IP-based throttle for passkey authentication endpoints."""
    scope = 'passkey_auth'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class AICallRateThrottle(SimpleRateThrottle):
    """Per-user throttle for endpoints that call external AI/translation APIs."""
    scope = 'ai_call'

    def get_cache_key(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk,
        }
