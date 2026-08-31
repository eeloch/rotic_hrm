from rest_framework import serializers

from .models import EmployeeDocument


class EmployeeDocumentSerializer(serializers.ModelSerializer):

    employee_name = serializers.CharField(
        source="employee.full_name",
        read_only=True,
    )

    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeDocument

        fields = [
            "id",
            "employee",
            "employee_name",
            "document_type",
            "title",
            "file",
            "description",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_at",
            "expiry_date",
            "is_active",
        ]

        read_only_fields = [
            "uploaded_by",
            "uploaded_at",
        ]

    def get_uploaded_by_name(self, obj):

        if obj.uploaded_by:
            return obj.uploaded_by.get_username()

        return None