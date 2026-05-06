
from rest_framework import serializers

from api.models.string_token import StringToken
from api.models.translations import Translation


class StringTokenSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='tag'
    )

    class Meta:
        model = StringToken
        fields = ['id', 'token', 'comment', 'tags', 'status']


class StringTranslationSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='tag'
    )

    translation = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='translation'
    )

    class Meta:
        model = StringToken
        fields = ['token', 'tags', 'translation']


class TranslationSerializer(serializers.ModelSerializer):
    token = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field='token'
    )

    class Meta:
        model = Translation
        fields = ['token', 'translation']


class StringTokenModelSerializer(serializers.Serializer):
    token = serializers.CharField()
    translation = serializers.SerializerMethodField()
    comment = serializers.CharField()
    tags = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    plural_forms = serializers.SerializerMethodField()
    default_translation = serializers.SerializerMethodField()
    glossary_hints = serializers.SerializerMethodField()

    def _get_translation_obj(self, obj):
        code = self.context.get('code', '').upper()
        return obj.translation.filter(language__code=code).first()

    def get_translation(self, obj):
        t = self._get_translation_obj(obj)
        return t.translation if t else ''

    def get_tags(self, obj):
        return [tag.tag for tag in obj.tags.all()]

    def get_status(self, obj):
        t = self._get_translation_obj(obj)
        return t.status if t else Translation.Status.new

    def get_plural_forms(self, obj):
        t = self._get_translation_obj(obj)
        if not t:
            return {}
        return {pf.plural_form: pf.value for pf in t.plural_forms.all()}

    def get_default_translation(self, obj):
        code = self.context.get('code', '').upper()
        default_code = self.context.get('default_code', '')
        if not default_code or default_code == code:
            return None
        t = obj.translation.filter(language__code=default_code).first()
        return t.translation if t else None

    def get_glossary_hints(self, obj):
        glossary_terms = self.context.get('glossary_terms', [])
        if not glossary_terms:
            return []
        source = self.get_default_translation(obj) or obj.token
        hints = []
        for gt in glossary_terms:
            term = gt['term']
            if gt['case_sensitive']:
                found = term in source
            else:
                found = term.lower() in source.lower()
            if found:
                hints.append({
                    'term': term,
                    'definition': gt['definition'],
                    'preferred_translation': gt['preferred_translation'],
                })
        return hints


class SimplifiedStringTokenSerializer(serializers.Serializer):
    token = serializers.CharField(source='token')
    translation = serializers.SerializerMethodField()

    def get_translation(self, obj):
        code = self.context.get('code', '').upper()
        translation = obj.translation.filter(language__code=code).first()
        return translation.translation if translation else ''
