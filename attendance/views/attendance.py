from django.utils import timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.models import DailyAttendance
from attendance.serializers import DailyAttendanceSerializer


class TodayAttendanceAPIView(APIView):

    permission_classes = [
        IsAuthenticated,
    ]

    def get(self, request):

        today = timezone.localdate()

        records = (
            DailyAttendance.objects
            .filter(date=today)
            .select_related(
                "employee",
                "employee__department",
                "shift",
            )
            .order_by(
                "employee__first_name",
                "employee__last_name",
            )
        )

        serializer = DailyAttendanceSerializer(
            records,
            many=True,
        )

        return Response({
            "date": today,
            "count": records.count(),
            "results": serializer.data,
        })
