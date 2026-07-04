# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from django.db import models
from api.models.project import Project


class LiveBundleSettings(models.Model):
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='live_bundle_settings')
    token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'LiveBundleSettings({self.project_id})'
