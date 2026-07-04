# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from django.urls import include, path

urlpatterns = [
    path('', include('api.urls.auth')),
    path('', include('api.urls.project')),
    path('', include('api.urls.strings')),
    path('', include('api.urls.plugin')),
    path('', include('api.urls.live_bundle')),
]
