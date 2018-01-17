from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView

from .models import Stapher

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/home.html'

class StapherListView(LoginRequiredMixin,ListView):
	template_name = 'schedules/stapher_list.html'
	def get_queryset(self):
		queryset = Stapher.objects.all()

class ShiftView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/shifts.html'



