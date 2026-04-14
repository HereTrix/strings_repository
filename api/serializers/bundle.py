from rest_framework import serializers

from api.models.bundle import TranslationBundle


class TranslationBundleSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = TranslationBundle
        fields = ['id', 'name', 'description', 'created_at', 'created_by']

    def get_created_by(self, obj):
        return f'{obj.created_by.first_name} {obj.created_by.last_name}'
