from django.urls import include, path

urlpatterns = [
    path('', include('api.urls.auth')),
    path('', include('api.urls.project')),
    path('', include('api.urls.strings')),
    path('', include('api.urls.plugin')),
]
