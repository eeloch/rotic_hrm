from django.urls import path
from .views import (
    AttendanceExceptionListAPIView,
    AttendanceDashboardAPIView,
    ExceptionDecisionAPIView,
    PendingExceptionAPIView,
    TodayAttendanceAPIView,
)


urlpatterns = [
    path(
        "today/",
        TodayAttendanceAPIView.as_view(),
        name="attendance-today",
    ),

    path(
        "exceptions/",
        AttendanceExceptionListAPIView.as_view(),
        name="attendance-exceptions",
    ),

    path(
        "exceptions/pending/",
        PendingExceptionAPIView.as_view(),
        name="attendance-exceptions-pending",
    ),

    path(
        "exceptions/<int:exception_id>/decision/",
        ExceptionDecisionAPIView.as_view(),
        name="attendance-exception-decision",
    ),

    path(
        "dashboard/",
        AttendanceDashboardAPIView.as_view(),
        name="attendance-dashboard",
    ),
]
