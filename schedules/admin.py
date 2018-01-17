from django.contrib import admin

# Register your models here.
from .models import Stapher, Shift

admin.site.register(Stapher)
admin.site.register(Shift)
