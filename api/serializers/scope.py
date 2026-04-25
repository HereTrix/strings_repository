from rest_framework import serializers
from api.models.scope import Scope, ScopeImage


class ScopeImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    class Meta:
        model = ScopeImage
        fields = ['id', 'url', 'created_at']


class ScopeSerializer(serializers.ModelSerializer):
    images = ScopeImageSerializer(many=True, read_only=True)
    token_count = serializers.SerializerMethodField()
    token_ids = serializers.SerializerMethodField()

    def get_token_count(self, obj):
        return obj.tokens.count()

    def get_token_ids(self, obj):
        return list(obj.tokens.values_list('id', flat=True))

    class Meta:
        model = Scope
        fields = ['id', 'name', 'description', 'images', 'token_count', 'token_ids', 'created_at']
