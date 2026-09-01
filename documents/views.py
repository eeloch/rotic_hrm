from rest_framework import generics, permissions
from django.db import transaction

from .models import EmployeeDocument
from .serializers import EmployeeDocumentSerializer
from audit.models import AuditSeverity
from audit.services import AuditService


class EmployeeDocumentListCreateAPIView(
    generics.ListCreateAPIView
):
    """
    GET -> List documents

    POST -> Upload document
    """

    serializer_class = EmployeeDocumentSerializer

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def get_queryset(self):
        queryset = (
            EmployeeDocument.objects
            .select_related(
                "employee",
                "uploaded_by",
            )
        )

        employee = self.request.query_params.get(
            "employee"
        )

        if employee:
            queryset = queryset.filter(
                employee_id=employee
            )

        return queryset

    def perform_create(
        self,
        serializer,
    ):
        user = (
            self.request.user
            if self.request.user.is_authenticated
            else None
        )

        document = serializer.save(
            uploaded_by=user
        )

        AuditService.log(
            event_type="document.uploaded",
            module="documents",
            employee=document.employee,
            actor=user,
            object=document,
            severity=AuditSeverity.SUCCESS,
            title="Document uploaded",
            description=f"{document.title} was uploaded for {document.employee.full_name}.",
            metadata={
                "document_type": document.document_type,
                "document_id": document.pk,
            },
        )


class EmployeeDocumentDetailAPIView(
    generics.RetrieveDestroyAPIView
):
    """
    GET -> Retrieve document

    DELETE -> Delete document and file
    """

    queryset = (
        EmployeeDocument.objects
        .select_related(
            "employee",
            "uploaded_by",
        )
    )

    serializer_class = (
        EmployeeDocumentSerializer
    )

    permission_classes = [
        permissions.IsAuthenticated,
    ]

    def perform_destroy(
        self,
        instance,
    ):
        if instance.file:
            instance.file.delete(
                save=False
            )

        with transaction.atomic():
            AuditService.log(
                event_type="document.deleted",
                module="documents",
                employee=instance.employee,
                actor=self.request.user,
                object=instance,
                severity=AuditSeverity.SUCCESS,
                title="Document deleted",
                description=f"{instance.title} was deleted for {instance.employee.full_name}.",
                metadata={
                    "document_type": instance.document_type,
                    "document_id": instance.pk,
                },
            )
            instance.delete()
