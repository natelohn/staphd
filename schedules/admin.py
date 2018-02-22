from django.contrib import admin

# Register your models here.
from .models import Flag, Stapher, Shift, Qualification, Staphing, Schedule, Parameter, Settings

admin.site.register(Flag)
admin.site.register(Stapher)
admin.site.register(Shift)
admin.site.register(Qualification)
admin.site.register(Staphing)
admin.site.register(Schedule)
admin.site.register(Parameter)
admin.site.register(Settings)
