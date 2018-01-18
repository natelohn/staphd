from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView

from .models import Stapher
from .forms import StapherCreateForm

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class StapherListView(LoginRequiredMixin,ListView):

	def get_queryset(self):
		queryset = Stapher.objects.filter(user=self.request.user)
		return queryset


class StapherDetailView(LoginRequiredMixin,DetailView):
	queryset = Stapher.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super(StapherDetailView, self).get_context_data(*args, **kwargs)
		return context

class StapherCreateView(LoginRequiredMixin, CreateView):
	form_class = StapherCreateForm
	template_name = 'schedules/schedules_form.html'

	def get_context_data(self, *args, **kwargs):
		context = super(StapherCreateView, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Stapher:'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(StapherCreateView, self).form_valid(form)


class StapherUpdateView(LoginRequiredMixin, UpdateView):
	form_class = StapherCreateForm
	template_name = 'schedules/schedules_form.html'

	def get_context_data(self, *args, **kwargs):
		context = super(StapherUpdateView, self).get_context_data(*args, **kwargs)
		name = self.get_object().first_name + ' ' + self.get_object().last_name
		context['title'] = f'Edit - {name} '
		return context

	def get_queryset(self):
		return Stapher.objects.filter(user=self.request.user)


class ShiftView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/shifts.html'



