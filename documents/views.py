from rest_framework import generics, permissions

from .models import EmployeeDocument
from .serializers import EmployeeDocumentSerializer


class EmployeeDocumentListCreateAPIView(
    generics.ListCreateAPIView
):
    """
    GET  -> List documents

    POST -> Upload document
    """

    serializer_class = EmployeeDocumentSerializer
    permission_classes = [
       permissions.IsAuthenticated,
    ]

    queryset = (
        EmployeeDocument.objects
        .select_related(
            "employee",
            "uploaded_by",
        )
    )

    def perform_create(self, serializer):

        user = (
            self.request.user
            if self.request.user.is_authenticated
            else None
        )

        serializer.save(
            uploaded_by=user
        )