from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import AttendanceException
from attendance.serializers import (
    AttendanceExceptionSerializer,
    ExceptionDecisionSerializer,
)


class AttendanceExceptionListAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        queryset = (
            AttendanceException.objects
            .select_related(
                "attendance",
                "attendance__employee",
                "attendance__employee__department",
                "attendance__shift",
            )
            .order_by(
                "-created_at",
            )
        )

        exception_status = request.query_params.get(
            "status"
        )

        exception_type = request.query_params.get(
            "type"
        )

        if exception_status:
            queryset = queryset.filter(
                status=exception_status
            )

        if exception_type:
            queryset = queryset.filter(
                exception_type=exception_type
            )

        serializer = AttendanceExceptionSerializer(
            queryset,
            many=True,
        )

        return Response({
            "count": queryset.count(),
            "results": serializer.data,
        })


class PendingExceptionAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        queryset = (
            AttendanceException.objects
            .filter(status="pending")
            .select_related(
                "attendance",
                "attendance__employee",
                "attendance__employee__department",
                "attendance__shift",
            )
            .order_by(
                "attendance__date",
                "attendance__employee__first_name",
            )
        )

        serializer = AttendanceExceptionSerializer(
            queryset,
            many=True,
        )

        total_proposed_deduction = sum(
            item.proposed_deduction
            for item in queryset
        )

        return Response({
            "count": queryset.count(),
            "total_proposed_deduction": total_proposed_deduction,
            "results": serializer.data,
        })


class ExceptionDecisionAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request, exception_id):

        try:
            exception = (
                AttendanceException.objects
                .select_related(
                    "attendance",
                    "attendance__employee",
                )
                .get(id=exception_id)
            )

        except AttendanceException.DoesNotExist:

            return Response(
                {
                    "detail": "Attendance exception not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ExceptionDecisionSerializer(
            exception,
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        serializer.save()

        result = AttendanceExceptionSerializer(
            exception
        )

        return Response({
            "message": "Attendance exception reviewed successfully.",
            "exception": result.data,
        })
