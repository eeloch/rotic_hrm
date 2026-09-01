from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from .models import (
    AttendanceEvent,
    DailyAttendance,
    AttendanceException,
    ShiftAssignment,
)
from audit.models import AuditSeverity
from audit.services import AuditService


from django.db.models import Q


def get_active_shift_assignment(employee, work_date):
    return (
        ShiftAssignment.objects
        .filter(
            employee=employee,
            start_date__lte=work_date,
        )
        .filter(
            Q(end_date__isnull=True) |
            Q(end_date__gte=work_date)
        )
        .select_related("shift")
        .order_by("-start_date")
        .first()
    )


def combine_date_and_time(work_date, shift_time):
    naive_dt = datetime.combine(work_date, shift_time)
    return timezone.make_aware(
        naive_dt,
        timezone.get_current_timezone(),
    )


def calculate_minute_rate(employee, working_days=26):
    """
    Basic salary / working days / 12 hours / 60 minutes
    """
    if employee.basic_salary <= 0:
        return Decimal("0.00")

    daily_rate = employee.basic_salary / Decimal(working_days)
    minute_rate = daily_rate / Decimal(720)

    return minute_rate.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def calculate_proposed_deduction(employee, minutes):
    minute_rate = calculate_minute_rate(employee)

    deduction = minute_rate * Decimal(minutes)

    return deduction.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def process_employee_attendance(employee, work_date):
    assignment = get_active_shift_assignment(
        employee,
        work_date,
    )

    if not assignment:
        return None

    shift = assignment.shift

    scheduled_start = combine_date_and_time(
        work_date,
        shift.start_time,
    )

    scheduled_end_date = work_date

    if shift.is_overnight:
        scheduled_end_date = work_date + timedelta(days=1)

    scheduled_end = combine_date_and_time(
        scheduled_end_date,
        shift.end_time,
    )

    window_start = scheduled_start - timedelta(hours=3)
    window_end = scheduled_end + timedelta(hours=3)

    events = (
        AttendanceEvent.objects
        .filter(
            employee=employee,
            timestamp__gte=window_start,
            timestamp__lte=window_end,
        )
        .order_by("timestamp")
    )

    daily_attendance, created = DailyAttendance.objects.get_or_create(
        employee=employee,
        date=work_date,
        defaults={
            "shift": shift,
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
        },
    )

    previous_clock_in = daily_attendance.actual_clock_in
    previous_clock_out = daily_attendance.actual_clock_out
    previous_status = daily_attendance.status
    previous_late_minutes = daily_attendance.late_minutes

    daily_attendance.shift = shift
    daily_attendance.scheduled_start = scheduled_start
    daily_attendance.scheduled_end = scheduled_end

    if not events.exists():
        daily_attendance.actual_clock_in = None
        daily_attendance.actual_clock_out = None
        daily_attendance.late_minutes = 0
        daily_attendance.early_departure_minutes = 0
        daily_attendance.worked_minutes = 0
        daily_attendance.overtime_minutes = 0
        daily_attendance.status = "absent"
        daily_attendance.save()

        AttendanceException.objects.get_or_create(
            attendance=daily_attendance,
            exception_type="absence",
            defaults={
                "minutes_affected": 720,
                "proposed_deduction": calculate_proposed_deduction(
                    employee,
                    720,
                ),
            },
        )

        return daily_attendance

    first_event = events.first()
    last_event = events.last()

    actual_clock_in = first_event.timestamp
    actual_clock_out = last_event.timestamp

    late_minutes = max(
        0,
        int(
            (
                actual_clock_in - scheduled_start
            ).total_seconds() // 60
        ),
    )

    early_departure_minutes = max(
        0,
        int(
            (
                scheduled_end - actual_clock_out
            ).total_seconds() // 60
        ),
    )

    worked_minutes = max(
        0,
        int(
            (
                actual_clock_out - actual_clock_in
            ).total_seconds() // 60
        ),
    )

    overtime_minutes = max(
        0,
        int(
            (
                actual_clock_out - scheduled_end
            ).total_seconds() // 60
        ),
    )

    daily_attendance.actual_clock_in = actual_clock_in
    daily_attendance.actual_clock_out = actual_clock_out
    daily_attendance.late_minutes = late_minutes
    daily_attendance.early_departure_minutes = early_departure_minutes
    daily_attendance.worked_minutes = worked_minutes
    daily_attendance.overtime_minutes = overtime_minutes

    if late_minutes > 0:
        daily_attendance.status = "late"
    else:
        daily_attendance.status = "present"

    daily_attendance.save()

    if created or previous_clock_in != actual_clock_in:
        AuditService.log(
            event_type="attendance.clock_in",
            module="attendance",
            employee=employee,
            object=daily_attendance,
            severity=AuditSeverity.SUCCESS,
            title="Clock in recorded",
            description=f"Clock in recorded for {employee.full_name}.",
            metadata={
                "attendance_date": work_date.isoformat(),
                "clock_in": actual_clock_in.isoformat(),
            },
        )

    if created or previous_clock_out != actual_clock_out:
        AuditService.log(
            event_type="attendance.clock_out",
            module="attendance",
            employee=employee,
            object=daily_attendance,
            severity=AuditSeverity.SUCCESS,
            title="Clock out recorded",
            description=f"Clock out recorded for {employee.full_name}.",
            metadata={
                "attendance_date": work_date.isoformat(),
                "clock_out": actual_clock_out.isoformat(),
            },
        )

    if late_minutes > 0 and (
        created
        or previous_status != "late"
        or previous_late_minutes != late_minutes
    ):
        AuditService.log(
            event_type="attendance.late",
            module="attendance",
            employee=employee,
            object=daily_attendance,
            severity=AuditSeverity.WARNING,
            title="Late arrival recorded",
            description=f"{employee.full_name} arrived late.",
            metadata={
                "attendance_date": work_date.isoformat(),
                "late_minutes": late_minutes,
            },
        )

    if late_minutes > 0:
        AttendanceException.objects.get_or_create(
            attendance=daily_attendance,
            exception_type="late",
            defaults={
                "minutes_affected": late_minutes,
                "proposed_deduction": calculate_proposed_deduction(
                    employee,
                    late_minutes,
                ),
            },
        )

    if early_departure_minutes > 0:
        AttendanceException.objects.get_or_create(
            attendance=daily_attendance,
            exception_type="early_departure",
            defaults={
                "minutes_affected": early_departure_minutes,
                "proposed_deduction": calculate_proposed_deduction(
                    employee,
                    early_departure_minutes,
                ),
            },
        )

    return daily_attendance
