from django.conf import settings
from django.urls import path, re_path
from .views import index
from django.views.static import serve

urlpatterns = [
    re_path(r"^(?!api).*", index),
    re_path(r'^static/(?P<path>.*)$', serve,
            {'document_root': settings.STATIC_ROOT})
]
