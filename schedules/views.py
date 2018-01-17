from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, CreateView

from .models import Stapher
from .forms import StapherCreateForm

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/home.html'

class StapherListView(LoginRequiredMixin,ListView):

	def get_queryset(self):
		queryset = Stapher.objects.all()
		return queryset


class StapherDetailView(LoginRequiredMixin,DetailView):
	queryset = Stapher.objects.all()
	
	def get_context_data(self, *args, **kwargs):
		context = super(StapherDetailView, self).get_context_data(*args, **kwargs)
		return context

class StapherCreateView(LoginRequiredMixin, CreateView):
	form_class = StapherCreateForm
	template_name = 'schedules/form.html'
	success_url = '/staphers/'



class ShiftView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/shifts.html'



