from django.utils import timezone
from rest_framework import serializers

from .models import (
    AttendanceException,
    DailyAttendance,
)


class DailyAttendanceSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(
        source="employee.employee_id",
        read_only=True,
    )

    employee_name = serializers.CharField(
        source="employee.full_name",
        read_only=True,
    )

    shift_name = serializers.CharField(
        source="shift.name",
        read_only=True,
    )

    class Meta:
        model = DailyAttendance

        fields = [
            "id",
            "employee_id",
            "employee_name",
            "date",
            "shift_name",
            "scheduled_start",
            "scheduled_end",
            "actual_clock_in",
            "actual_clock_out",
            "late_minutes",
            "early_departure_minutes",
            "worked_minutes",
            "overtime_minutes",
            "status",
        ]


class AttendanceExceptionSerializer(serializers.ModelSerializer):
    employee_id = serializers.CharField(
        source="attendance.employee.employee_id",
        read_only=True,
    )

    employee_name = serializers.CharField(
        source="attendance.employee.full_name",
        read_only=True,
    )

    department = serializers.CharField(
        source="attendance.employee.department.name",
        read_only=True,
        allow_null=True,
    )

    attendance_date = serializers.DateField(
        source="attendance.date",
        read_only=True,
    )

    shift_name = serializers.CharField(
        source="attendance.shift.name",
        read_only=True,
        allow_null=True,
    )

    scheduled_start = serializers.DateTimeField(
        source="attendance.scheduled_start",
        read_only=True,
    )

    actual_clock_in = serializers.DateTimeField(
        source="attendance.actual_clock_in",
        read_only=True,
    )

    scheduled_end = serializers.DateTimeField(
        source="attendance.scheduled_end",
        read_only=True,
    )

    actual_clock_out = serializers.DateTimeField(
        source="attendance.actual_clock_out",
        read_only=True,
    )

    class Meta:
        model = AttendanceException

        fields = [
            "id",

            "employee_id",
            "employee_name",
            "department",

            "attendance_date",
            "shift_name",

            "scheduled_start",
            "actual_clock_in",
            "scheduled_end",
            "actual_clock_out",

            "exception_type",
            "minutes_affected",
            "proposed_deduction",

            "status",

            "employee_reason",
            "supervisor_comment",
            "admin_comment",

            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]

        read_only_fields = [
            "status",
            "reviewed_by",
            "reviewed_at",
        ]


class ExceptionDecisionSerializer(serializers.Serializer):

    DECISIONS = [
        ("approved", "Approve Deduction"),
        ("waived", "Waive Deduction"),
        ("held", "Hold / Investigate"),
    ]

    decision = serializers.ChoiceField(
        choices=DECISIONS,
    )

    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate(self, attrs):
        decision = attrs["decision"]
        comment = attrs.get("comment", "").strip()

        if decision in ["waived", "held"] and not comment:
            raise serializers.ValidationError({
                "comment":
                    "A reason is required when waiving or holding an exception."
            })

        return attrs

    def update(self, instance, validated_data):

        decision = validated_data["decision"]
        comment = validated_data.get(
            "comment",
            "",
        )

        request = self.context["request"]

        instance.status = decision
        instance.admin_comment = comment
        instance.reviewed_at = timezone.now()

        if request.user.get_full_name():
            instance.reviewed_by = request.user.get_full_name()
        else:
            instance.reviewed_by = request.user.username

        instance.save()

        return instance

    def create(self, validated_data):
        raise NotImplementedError