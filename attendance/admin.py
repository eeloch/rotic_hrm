from django.contrib import admin

from .models import (
    Shift,
    ShiftAssignment,
    BiometricDevice,
    AttendanceEvent,
    DailyAttendance,
    AttendanceException,
)


admin.site.register(Shift)
admin.site.register(ShiftAssignment)
admin.site.register(BiometricDevice)
admin.site.register(AttendanceEvent)
admin.site.register(DailyAttendance)
admin.site.register(AttendanceException)