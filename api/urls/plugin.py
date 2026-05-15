# Copyright (c) StringsRepository Contributors
# SPDX-License-Identifier: MIT

from django.urls import path
from api.views.plugin import ContextAPI, FetchLanguagesAPI, PluginExportAPI, PullAPI, PushAPI, TagsAPI
from api.views.mcp import McpView

urlpatterns = [
    path('plugin/tags', TagsAPI.as_view()),
    path('plugin/context', ContextAPI.as_view()),
    path('plugin/export', PluginExportAPI.as_view()),
    path('plugin/pull', PullAPI.as_view()),
    path('plugin/push', PushAPI.as_view()),
    path('plugin/languages', FetchLanguagesAPI.as_view()),
    path('mcp', McpView.as_view()),
]
