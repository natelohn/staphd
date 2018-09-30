from django.contrib import admin

# Register your models here.
from .models import Flag, SignUp, Stapher, Shift, Qualification, Staphing, Schedule, Parameter, Settings, Master, ShiftSet, ShiftPreference

admin.site.register(Flag)
admin.site.register(Stapher)
admin.site.register(Shift)
admin.site.register(Qualification)
admin.site.register(Staphing)
admin.site.register(Schedule)
admin.site.register(Parameter)
admin.site.register(Settings)
admin.site.register(Master)
admin.site.register(ShiftSet)
admin.site.register(ShiftPreference)
admin.site.register(SignUp)
