import hashlib
import secrets as _secrets

from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, related_name='profile', unique=True, on_delete=models.CASCADE)


class TwoFAVerification(models.Model):
    """Tracks which Knox token keys have completed the 2FA login step."""
    token_key = models.CharField(max_length=8, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class BackupCode(models.Model):
    """Single-use hashed backup codes for TOTP 2FA recovery."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='backup_codes')
    code_hash = models.CharField(max_length=64)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    @staticmethod
    def generate(user, count=10):
        """Generate `count` fresh backup codes. Returns list of plaintext codes."""
        BackupCode.objects.filter(user=user).delete()
        codes = []
        for _ in range(count):
            plaintext = _secrets.token_urlsafe(8)
            code_hash = hashlib.sha256(plaintext.encode()).hexdigest()
            BackupCode.objects.create(user=user, code_hash=code_hash)
            codes.append(plaintext)
        return codes

    @staticmethod
    def verify_and_consume(user, plaintext_code: str) -> bool:
        """Returns True and marks the code used if valid; False otherwise."""
        code_hash = hashlib.sha256(plaintext_code.encode()).hexdigest()
        code = BackupCode.objects.filter(
            user=user, code_hash=code_hash, used=False
        ).first()
        if code:
            code.used = True
            code.save(update_fields=['used'])
            return True
        return False
