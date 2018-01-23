from django.contrib import admin

# Register your models here.
from .models import Flag, Stapher, Shift, Qualification

admin.site.register(Flag)
admin.site.register(Stapher)
admin.site.register(Shift)
admin.site.register(Qualification)
