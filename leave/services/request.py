"""Service-layer validation and creation for employee leave requests."""

from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction

from leave.models import LeaveDuration, LeaveRequest, LeaveStatus
from leave.services.balance import LeaveBalanceService


class LeaveRequestService:
    """Create pending leave requests after applying all leave policy rules."""

    @classmethod
    def validate_request(
        cls,
        *,
        employee,
        leave_type,
        start_date,
        end_date,
        total_days,
        duration_type=LeaveDuration.FULL_DAY,
        return_date=None,
        reason="",
        as_of=None,
    ):
        """Return a structured validation result without writing a request."""
        errors = {}
        normalized_total_days = cls._normalize_total_days(total_days, errors)

        cls._validate_dates(start_date, end_date, return_date, errors)
        cls._validate_duration(
            start_date,
            end_date,
            normalized_total_days,
            duration_type,
            errors,
        )

        if not str(reason).strip():
            errors["reason"] = "A reason for leave is required."

        balance = None
        if not errors:
            balance = LeaveBalanceService.get_balance(
                employee,
                leave_type,
                year=start_date.year,
                as_of=as_of or start_date,
            )

            if balance["matched_policy"] is None:
                errors["leave_type"] = (
                    "No active leave policy matches this employee's employment "
                    "eligibility and years of service."
                )
            elif normalized_total_days > balance["remaining_days"]:
                errors["total_days"] = "The employee does not have enough remaining leave balance."

            if cls.has_overlapping_leave(employee, start_date, end_date):
                errors["date_range"] = (
                    "A pending or approved leave request already overlaps these dates."
                )

        return {
            "is_valid": not errors,
            "errors": errors,
            "total_days": normalized_total_days,
            "balance": balance,
            "matched_policy": balance["matched_policy"] if balance else None,
        }

    @classmethod
    def create_request(
        cls,
        *,
        employee,
        leave_type,
        start_date,
        end_date,
        total_days,
        duration_type=LeaveDuration.FULL_DAY,
        return_date=None,
        reason="",
        requested_by=None,
        as_of=None,
    ):
        """Validate and create a pending request, returning a structured result."""
        validation = cls.validate_request(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            total_days=total_days,
            duration_type=duration_type,
            return_date=return_date,
            reason=reason,
            as_of=as_of,
        )

        if not validation["is_valid"]:
            return {
                "success": False,
                "leave_request": None,
                **validation,
            }

        leave_request = cls._create_with_request_number(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            return_date=return_date,
            duration_type=duration_type,
            total_days=validation["total_days"],
            reason=str(reason).strip(),
            requested_by=requested_by,
        )

        return {
            "success": True,
            "leave_request": leave_request,
            "errors": {},
            "total_days": validation["total_days"],
            "balance": validation["balance"],
            "matched_policy": validation["matched_policy"],
        }

    @staticmethod
    def calculate_leave_days(start_date, end_date, duration_type):
        """Return the duration-aware leave amount for a continuous date range."""
        if start_date > end_date:
            raise ValueError("The approved start date cannot be after the approved end date.")

        if duration_type in {LeaveDuration.FIRST_HALF, LeaveDuration.SECOND_HALF}:
            if start_date != end_date:
                raise ValueError("Half-day leave must start and end on the same date.")
            return Decimal("0.5")

        return Decimal((end_date - start_date).days + 1)

    @staticmethod
    def has_overlapping_leave(employee, start_date, end_date):
        """Return whether pending or approved leave intersects the supplied dates."""
        return LeaveRequest.objects.filter(
            employee=employee,
            status__in=[LeaveStatus.PENDING, LeaveStatus.APPROVED],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).exists()

    @classmethod
    def _create_with_request_number(cls, **request_data):
        """Create a request with a unique, yearly sequential reference number."""
        year = request_data["start_date"].year

        for _ in range(3):
            try:
                with transaction.atomic():
                    return LeaveRequest.objects.create(
                        request_number=cls._next_request_number(year),
                        status=LeaveStatus.PENDING,
                        **request_data,
                    )
            except IntegrityError:
                # A concurrent request claimed the same sequence; retry it.
                continue

        raise IntegrityError("Unable to allocate a unique leave request number.")

    @staticmethod
    def _next_request_number(year):
        prefix = f"LV-{year}-"
        latest_request = (
            LeaveRequest.objects.select_for_update()
            .filter(request_number__startswith=prefix)
            .order_by("-request_number")
            .first()
        )
        sequence = (
            int(latest_request.request_number.rsplit("-", 1)[-1]) + 1
            if latest_request
            else 1
        )
        return f"{prefix}{sequence:06d}"

    @staticmethod
    def _normalize_total_days(total_days, errors):
        try:
            normalized_total_days = Decimal(str(total_days))
        except (InvalidOperation, TypeError, ValueError):
            errors["total_days"] = "Total leave days must be a valid number."
            return None

        if normalized_total_days <= 0:
            errors["total_days"] = "Total leave days must be greater than zero."

        return normalized_total_days

    @staticmethod
    def _validate_dates(start_date, end_date, return_date, errors):
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            errors["date_range"] = "A valid start date and end date are required."
            return

        if start_date > end_date:
            errors["date_range"] = "The leave start date cannot be after the end date."

        if return_date is not None:
            if not isinstance(return_date, date):
                errors["return_date"] = "Return date must be a valid date."
            elif return_date <= end_date:
                errors["return_date"] = "Return date must be after the leave end date."

    @staticmethod
    def _validate_duration(
        start_date,
        end_date,
        total_days,
        duration_type,
        errors,
    ):
        valid_durations = {choice for choice, _ in LeaveDuration.choices}
        if duration_type not in valid_durations:
            errors["duration_type"] = "Select a valid leave duration."
            return

        if duration_type in {LeaveDuration.FIRST_HALF, LeaveDuration.SECOND_HALF}:
            if start_date != end_date:
                errors["duration_type"] = "Half-day leave must start and end on the same date."
            elif total_days != Decimal("0.5"):
                errors["total_days"] = "Half-day leave must be requested as 0.5 days."
