from rest_framework import serializers

from api.models.history import HistoryRecord


class EditorFieldSerializer(serializers.RelatedField):
    def to_representation(self, value):
        return f'{value.first_name} {value.last_name}'


class HistorySerializer(serializers.ModelSerializer):
    editor = EditorFieldSerializer(read_only=True)

    class Meta:
        model = HistoryRecord
        fields = ['updated_at', 'language', 'token',
                  'status', 'editor', 'old_value', 'new_value']
