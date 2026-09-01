from django.urls import path
from .views import (
    EmployeeDocumentListCreateAPIView,
    EmployeeDocumentDetailAPIView,
)

from .views import (
    EmployeeDocumentListCreateAPIView,
)

urlpatterns = [

    path(
        "",
        EmployeeDocumentListCreateAPIView.as_view(),
        name="documents",
    ),

    path(
        "<int:pk>/",
        EmployeeDocumentDetailAPIView.as_view(),
        name="document-detail",
    ),

]
