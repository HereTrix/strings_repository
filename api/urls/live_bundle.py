# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from django.urls import path
from api.views.live_bundle import LiveBundleVersionAPI, LiveBundleContentAPI

urlpatterns = [
    path('live-bundle/version', LiveBundleVersionAPI.as_view()),
    path('live-bundle/content', LiveBundleContentAPI.as_view()),
]
