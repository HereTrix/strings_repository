from rest_framework import serializers
from api.models.glossary import GlossaryTerm, GlossaryTranslation, GlossaryExtractionJob


class GlossaryTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlossaryTranslation
        fields = ['language_code', 'preferred_translation', 'updated_at']
        read_only_fields = ['updated_at']


class GlossaryTermSerializer(serializers.ModelSerializer):
    translations = GlossaryTranslationSerializer(many=True, read_only=True)
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = GlossaryTerm
        fields = ['id', 'term', 'definition', 'case_sensitive', 'translations', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_created_by(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'Deleted user'


class GlossaryExtractionJobSerializer(serializers.ModelSerializer):
    suggestion_count = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = GlossaryExtractionJob
        fields = ['id', 'status', 'created_by', 'created_at', 'completed_at', 'error_message', 'suggestion_count']
        read_only_fields = ['id', 'status', 'created_by', 'created_at', 'completed_at', 'error_message', 'suggestion_count']

    def get_suggestion_count(self, obj):
        if obj.suggestions is None:
            return 0
        return len(obj.suggestions)

    def get_created_by(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'Deleted user'
