from django.urls import path

from .views import (
    EmployeeDocumentListCreateAPIView,
)

urlpatterns = [

    path(
        "",
        EmployeeDocumentListCreateAPIView.as_view(),
        name="documents",
    ),

]
