from decimal import Decimal

from django.db.models import DecimalField, F, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from leave.models import LeavePolicy, LeaveRequest, LeaveStatus


class LeaveBalanceService:
    """Resolve leave entitlements without creating or updating model records."""

    @staticmethod
    def calculate_years_of_service(employee, as_of=None):
        """Return completed years based on the employee's official employment date."""
        if not employee.employment_date:
            return None

        as_of = as_of or timezone.localdate()
        years = as_of.year - employee.employment_date.year

        if (as_of.month, as_of.day) < (
            employee.employment_date.month,
            employee.employment_date.day,
        ):
            years -= 1

        return years

    @classmethod
    def resolve_policy(cls, employee, leave_type, as_of=None):
        """Return the highest-priority active policy that applies to an employee."""
        years_of_service = cls.calculate_years_of_service(employee, as_of)
        policies = LeavePolicy.objects.filter(
            leave_type=leave_type,
            is_active=True,
        ).select_related(
            "department",
            "position",
        )

        for filters in cls._priority_filters(employee):
            policy = cls._first_matching_policy(
                policies.filter(**filters),
                employee,
                years_of_service,
            )

            if policy:
                return policy

        company_default_policies = policies.filter(
            department__isnull=True,
            position__isnull=True,
            employment_type__isnull=True,
            employment_category__isnull=True,
            gender__isnull=True,
        )

        return cls._first_matching_policy(
            company_default_policies,
            employee,
            years_of_service,
        )

    @staticmethod
    def calculate_used_days(employee, leave_type, year):
        """Return approved leave totals for the requested calendar year."""
        approved_amount = Coalesce(
            "approved_days",
            F("total_days"),
            output_field=DecimalField(max_digits=6, decimal_places=2),
        )
        used_days = (
            LeaveRequest.objects.filter(
                employee=employee,
                leave_type=leave_type,
                status__in=[
                    LeaveStatus.APPROVED,
                    LeaveStatus.PARTIALLY_APPROVED,
                ],
                start_date__year=year,
            ).aggregate(total=Sum(approved_amount))["total"]
            or Decimal("0")
        )

        return used_days

    @classmethod
    def get_balance(cls, employee, leave_type, year=None, as_of=None):
        """Return the calculated allocation, usage, remaining balance, and policy."""
        as_of = as_of or timezone.localdate()
        year = year or as_of.year
        matched_policy = cls.resolve_policy(employee, leave_type, as_of)
        allocated_days = (
            matched_policy.allocated_days
            if matched_policy
            else Decimal("0")
        )
        used_days = cls.calculate_used_days(employee, leave_type, year)

        return {
            "allocated_days": allocated_days,
            "used_days": used_days,
            "remaining_days": allocated_days - used_days,
            "matched_policy": matched_policy,
        }

    @staticmethod
    def _priority_filters(employee):
        """Build only the policy scopes available for the supplied employee."""
        filters = []

        if employee.department_id and employee.position_id:
            filters.append(
                {
                    "department": employee.department,
                    "position": employee.position,
                }
            )

        if employee.department_id and employee.employment_type:
            filters.append(
                {
                    "department": employee.department,
                    "employment_type": employee.employment_type,
                }
            )

        if employee.department_id:
            filters.append({"department": employee.department})

        if employee.position_id:
            filters.append({"position": employee.position})

        if employee.employment_type and employee.employment_category:
            filters.append(
                {
                    "employment_type": employee.employment_type,
                    "employment_category": employee.employment_category,
                }
            )

        if employee.employment_type:
            filters.append({"employment_type": employee.employment_type})

        return filters

    @classmethod
    def _first_matching_policy(cls, policies, employee, years_of_service):
        for policy in policies.order_by("id"):
            if cls._policy_applies(policy, employee, years_of_service):
                return policy

        return None

    @staticmethod
    def _policy_applies(policy, employee, years_of_service):
        """Ensure optional policy criteria do not conflict with employee data."""
        if policy.department_id != (employee.department_id or None) and policy.department_id:
            return False

        if policy.position_id != (employee.position_id or None) and policy.position_id:
            return False

        if policy.employment_type and policy.employment_type != employee.employment_type:
            return False

        if (
            policy.employment_category
            and policy.employment_category != employee.employment_category
        ):
            return False

        employee_gender = getattr(employee, "gender", None)

        if policy.gender and policy.gender != employee_gender:
            return False

        if (
            policy.minimum_years_of_service is not None
            and (years_of_service is None or years_of_service < policy.minimum_years_of_service)
        ):
            return False

        if (
            policy.maximum_years_of_service is not None
            and (years_of_service is None or years_of_service > policy.maximum_years_of_service)
        ):
            return False

        return True
