from django.urls import path
from api.views.plugin import FetchLanguagesAPI, PluginExportAPI, PullAPI, PushAPI
from api.views.mcp import McpView

urlpatterns = [
    path('plugin/export', PluginExportAPI.as_view()),
    path('plugin/pull', PullAPI.as_view()),
    path('plugin/push', PushAPI.as_view()),
    path('plugin/languages', FetchLanguagesAPI.as_view()),
    path('mcp', McpView.as_view()),
]
