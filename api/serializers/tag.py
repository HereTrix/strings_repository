# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from rest_framework import serializers

from api.models.tag import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['tag']
