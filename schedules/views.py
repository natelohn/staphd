from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models.functions import Lower
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Stapher
from .forms import StapherCreateForm

class Home(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class StapherList(LoginRequiredMixin,ListView):
	template_name = 'schedules/list.html'
	def get_queryset(self):
		queryset = Stapher.objects.filter(user=self.request.user).order_by(Lower('first_name'), Lower('last_name'))
		query = self.request.GET.get('q')
		if query:
			if query.lower() in 'returner':
				queryset = queryset.filter(summers_worked__gt=0)
			elif query.lower() in 'new':
				queryset = queryset.filter(summers_worked__iexact=0)
			else:
				queryset = queryset.filter(
					Q(first_name__icontains=query) |
					Q(last_name__icontains=query) |
					Q(title__iexact=query) |
					Q(gender__iexact=query) |
					Q(age__iexact=query) |
					Q(class_year__iexact=query)
				)
		return queryset

	def get_context_data(self, *args, **kwargs):
		context = super(StapherList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Staphers'
		context['link'] = 'schedules:stapher-create'
		return context

class StapherDetail(LoginRequiredMixin,DetailView):
	queryset = Stapher.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super(StapherDetail, self).get_context_data(*args, **kwargs)
		return context

class StapherCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/schedules_form.html'
	form_class = StapherCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(StapherCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Stapher:'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(StapherCreate, self).form_valid(form)


class StapherUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/schedules_form.html'
	form_class = StapherCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(StapherUpdate, self).get_context_data(*args, **kwargs)
		name = self.get_object().first_name + ' ' + self.get_object().last_name
		context['title'] = f'Edit - {name} '
		return context

	def get_queryset(self):
		return Stapher.objects.filter(user=self.request.user)

class StapherDelete(DeleteView):
	template_name = 'schedules/schedules_delete.html'
	model = Stapher
	success_url = reverse_lazy('schedules:staphers-list')



class Shift(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/shifts.html'



