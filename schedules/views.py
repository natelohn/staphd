from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView



class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'pages/home.html'

class StapherView(TemplateView):
	template_name = 'pages/staphers.html'

class ShiftView(TemplateView):
	template_name = 'pages/shifts.html'

