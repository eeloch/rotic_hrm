from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [

    path(
        "admin/",
        admin.site.urls,
    ),

    path(
        "api/auth/login/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    path(
        "api/auth/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    path(
        "api/attendance/",
        include("attendance.urls"),
    ),

    path(
        "api/employees/",
        include("employees.urls"),
    ),

    path(
        "api/documents/",
        include("documents.urls"),
    ),

    path(
        "api/leave/",
        include("leave.urls"),
    ),

    path(
        "api/workflow/",
        include("workflow.urls"),
    ),

    path(
        "api/audit/",
        include("audit.urls"),
    ),

    path(
        "api/notifications/",
        include("notifications.urls"),
    ),

    
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
