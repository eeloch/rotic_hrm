from django.urls import path

from .views import (
    TodayAttendanceAPIView,
    AttendanceExceptionListAPIView,
    PendingExceptionAPIView,
    ExceptionDecisionAPIView,
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
]