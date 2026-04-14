from rest_framework import serializers

from api.languages.langcoder import LANGUAGE_FLAG_CODE_KEY, Langcoder
from api.models.language import Language


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['code']


class LanguageSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    img = serializers.SerializerMethodField()

    def get_name(self, obj):
        return Langcoder.language(obj.code)

    def get_img(self, obj):
        return Langcoder.flag(obj.code)

    class Meta:
        model = Language
        fields = ['code', 'name', 'img']


class AvailableLanguageSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    img = serializers.SerializerMethodField()

    def get_img(self, obj):
        flag_code = obj.get(LANGUAGE_FLAG_CODE_KEY)
        return f'/static/flags/{flag_code}.svg' if flag_code else None
