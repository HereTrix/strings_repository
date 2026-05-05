from rest_framework import serializers

from api.models.project import ProjectAIProvider
from api.models.verification import VerificationComment, VerificationReport


class VerificationCommentSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = VerificationComment
        fields = ['id', 'token_id', 'token_key', 'plural_form', 'author', 'text', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']

    def get_author(self, obj):
        if obj.author:
            return obj.author.get_full_name() or obj.author.username
        return 'Deleted user'


class VerificationReportListSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()

    class Meta:
        model = VerificationReport
        fields = [
            'id', 'mode', 'status', 'target_language', 'is_readonly',
            'string_count', 'checks', 'created_by', 'created_at',
            'completed_at', 'summary', 'error_message',
        ]

    def get_created_by(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return 'Deleted user'

    def get_summary(self, obj):
        if obj.result and 'summary' in obj.result:
            return obj.result['summary']
        return None


class VerificationReportDetailSerializer(VerificationReportListSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(VerificationReportListSerializer.Meta):
        fields = VerificationReportListSerializer.Meta.fields + ['result', 'comments']

    def get_comments(self, obj):
        comments = obj.comments.select_related('author').all()
        return VerificationCommentSerializer(comments, many=True).data
