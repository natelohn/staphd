from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.db.models.functions import Lower
from django.urls import reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Flag, Stapher, Shift, Qualification
from .forms import FlagCreateForm, StapherCreateForm, ShiftCreateForm, QualificationCreateForm

class Home(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class Settings(LoginRequiredMixin, TemplateView):
    template_name = 'settings.html'

    def get_context_data(self, *args, **kwargs):
    	context = super(Settings, self).get_context_data(*args, **kwargs)
    	context['qualifications'] = Qualification.objects.filter(user=self.request.user).order_by(Lower('title'))
    	context['flags'] = Flag.objects.filter(user=self.request.user).order_by(Lower('title'))
    	return context

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
	template_name = 'schedules/form.html'
	form_class = StapherCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(StapherCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Stapher:'
		context['cancel_url'] = 'schedules:stapher-list'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(StapherCreate, self).form_valid(form)


class StapherUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/form.html'
	form_class = StapherCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(StapherUpdate, self).get_context_data(*args, **kwargs)
		context['title'] = f'Edit - {self.get_object()} '
		return context

	def get_queryset(self):
		return Stapher.objects.filter(user=self.request.user)

class StapherDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Stapher
	success_url = reverse_lazy('schedules:stapher-list')



class ShiftList(LoginRequiredMixin, ListView):
	template_name = 'schedules/list.html'
	def get_queryset(self):
		queryset = Shift.objects.all()
		query = self.request.GET.get('q')
		if query:
			queryset = queryset.filter(
				Q(title__icontains=query) |
				Q(flag__icontains=query)
			)
		return queryset
		

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Shifts'
		context['link'] = 'schedules:shift-create'
		return context


class ShiftDetail(LoginRequiredMixin,DetailView):
	queryset = Shift.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftDetail, self).get_context_data(*args, **kwargs)
		return context


class ShiftCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = ShiftCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Shift:'
		context['cancel_url'] = 'schedules:shift-list'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(ShiftCreate, self).form_valid(form)


class ShiftUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/form.html'
	form_class = ShiftCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftUpdate, self).get_context_data(*args, **kwargs)
		title = self.get_object().title
		context['title'] = f'Edit - {self.get_object()} '
		return context

	def get_queryset(self):
		return Shift.objects.filter(user=self.request.user)

class ShiftDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Shift
	success_url = reverse_lazy('schedules:shift-list')


class QualificationCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = QualificationCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(QualificationCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Qualification:'
		context['cancel_url'] = 'settings'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(QualificationCreate, self).form_valid(form)

class QualificationDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Qualification
	success_url = reverse_lazy('settings')

class FlagCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = FlagCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(FlagCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Flag:'
		context['cancel_url'] = 'settings'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(FlagCreate, self).form_valid(form)

class FlagDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Flag
	success_url = reverse_lazy('settings')
