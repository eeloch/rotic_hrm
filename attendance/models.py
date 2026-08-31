

# Create your models here.
from django.db import models
from employees.models import Employee


class Shift(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    is_overnight = models.BooleanField(
        default=False,
    )

    active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name


class ShiftAssignment(models.Model):

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="shift_assignments",
    )

    shift = models.ForeignKey(
        Shift,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    start_date = models.DateField()

    end_date = models.DateField(
        null=True,
        blank=True,
    )

    assigned_by = models.CharField(
        max_length=150,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"{self.employee.employee_id} - {self.shift.name}"

class BiometricDevice(models.Model):

    DEVICE_TYPES = [
        ("factory", "Factory"),
        ("hostel", "Hostel"),
        ("office", "Office"),
    ]

    name = models.CharField(
        max_length=100,
    )

    serial_number = models.CharField(
        max_length=100,
        unique=True,
    )

    model = models.CharField(
        max_length=100,
        blank=True,
    )

    location = models.CharField(
        max_length=200,
    )

    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPES,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    is_online = models.BooleanField(
        default=False,
    )

    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.name} - {self.serial_number}"


class AttendanceEvent(models.Model):

    VERIFICATION_TYPES = [
        ("face", "Face"),
        ("fingerprint", "Fingerprint"),
        ("card", "Card"),
        ("manual", "Manual"),
        ("unknown", "Unknown"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="attendance_events",
    )

    device = models.ForeignKey(
        BiometricDevice,
        on_delete=models.SET_NULL,
        null=True,
        related_name="attendance_events",
    )

    timestamp = models.DateTimeField()

    verification_type = models.CharField(
        max_length=20,
        choices=VERIFICATION_TYPES,
        default="unknown",
    )

    external_event_id = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    raw_payload = models.JSONField(
        default=dict,
        blank=True,
    )

    imported_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["timestamp"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "device",
                    "external_event_id",
                ],
                name="unique_device_external_event",
            )
        ]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.timestamp}"  


class DailyAttendance(models.Model):

    STATUS_CHOICES = [
        ("present", "Present"),
        ("late", "Late"),
        ("absent", "Absent"),
        ("leave", "Leave"),
        ("incomplete", "Incomplete"),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="daily_attendance",
    )

    date = models.DateField()

    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
    )

    scheduled_start = models.DateTimeField(
        null=True,
        blank=True,
    )

    scheduled_end = models.DateTimeField(
        null=True,
        blank=True,
    )

    actual_clock_in = models.DateTimeField(
        null=True,
        blank=True,
    )

    actual_clock_out = models.DateTimeField(
        null=True,
        blank=True,
    )

    late_minutes = models.PositiveIntegerField(
        default=0,
    )

    early_departure_minutes = models.PositiveIntegerField(
        default=0,
    )

    worked_minutes = models.PositiveIntegerField(
        default=0,
    )

    overtime_minutes = models.PositiveIntegerField(
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="present",
    )

    processed_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "employee",
                    "date",
                ],
                name="unique_daily_employee_attendance",
            )
        ]

    def __str__(self):
        return f"{self.employee.employee_id} - {self.date}"

class AttendanceException(models.Model):

    EXCEPTION_TYPES = [
        ("late", "Late Arrival"),
        ("early_departure", "Early Departure"),
        ("absence", "Absence"),
        ("missing_clock_in", "Missing Clock In"),
        ("missing_clock_out", "Missing Clock Out"),
        ("hostel_violation", "Hostel During Shift"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("waived", "Waived"),
        ("held", "Held"),
    ]

    attendance = models.ForeignKey(
        DailyAttendance,
        on_delete=models.CASCADE,
        related_name="exceptions",
    )

    exception_type = models.CharField(
        max_length=30,
        choices=EXCEPTION_TYPES,
    )

    minutes_affected = models.PositiveIntegerField(
        default=0,
    )

    proposed_deduction = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    employee_reason = models.TextField(
        blank=True,
    )

    supervisor_comment = models.TextField(
        blank=True,
    )

    admin_comment = models.TextField(
        blank=True,
    )

    reviewed_by = models.CharField(
        max_length=150,
        blank=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"{self.attendance.employee.employee_id} "
            f"- {self.exception_type}"
        )        