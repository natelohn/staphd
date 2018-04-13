import datetime
import json

from celery.result import AsyncResult
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, render, redirect
from django.template import RequestContext
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView


from .build import build_schedules
from .forms import FlagCreateForm, ShiftCreateForm, StapherCreateForm, QualificationCreateForm
from .models import Flag, Schedule, Shift, Stapher, Staphing, Qualification, Master
from .models import Settings as ScheduleSettings
from .sort import get_sorted_shifts
from .tasks import build_schedules_task, update_files_task




class Home(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class DownloadView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/download.html'

class BuildView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/schedule.html'

@login_required
def download_individual(request):
	return HttpResponseRedirect(reverse('schedules:download'))

@login_required
def building_schedules(request):
	sorted_shifts = cache.get('sorted_shifts')
	if cache.get('resort') or not sorted_shifts:
		all_shifts = Shift.objects.all()
		all_staphers = Stapher.objects.all()
		sorted_shifts = get_sorted_shifts(all_staphers, all_shifts)
		cache.set('sorted_shifts', sorted_shifts, None)
		cache.set('resort', False, None)
	task = task.delay(sorted_shifts)
	task_id = task.task_id
	request.session['task_id'] = task_id
	context = {'task_id':task_id}
	return HttpResponseRedirect(reverse('schedules:build'))

@login_required
@csrf_exempt
def track_state(request, *args, **kwargs):
	""" A view to report the progress of a task to the user """
	data = 'Fail'
	if request.is_ajax():
		if 'task_id' in request.POST.keys() and request.POST['task_id']:
			task_id = request.POST['task_id']
			task = AsyncResult(task_id)
			data = task.result or task.state
			task_running = not task.ready()
			if task_running:
				data['running'] = task_running
		else:
			data = 'No task_id in the request'
	else:
		data = 'This is not an ajax request'
	json_data = json.dumps(data)
	return HttpResponse(json_data, content_type='application/json')

@login_required
@csrf_exempt
def update_files(request, *args, **kwargs):
	schedule_id = cache.get('schedule_id')
	if schedule_id:
		print('Called!')
		task = update_files_task.delay(schedule_id)
		task_id = task.task_id
		request.session['task_id'] = task_id
		context = {'task_id':task_id}
		return render(request,'schedules/progress.html', context)
	else:
		# TODO: Create an appropriate error message
		print('No schedule!')
		return HttpResponseRedirect(reverse('schedules:schedule'))


class Settings(LoginRequiredMixin, TemplateView):
    template_name = 'settings.html'

    def get_context_data(self, *args, **kwargs):
    	context = super(Settings, self).get_context_data(*args, **kwargs)
    	context['qualifications'] = Qualification.objects.all().order_by(Lower('title'))
    	context['flags'] = Flag.objects.all().order_by(Lower('title'))
    	return context


class StapherList(LoginRequiredMixin,ListView):
	template_name = 'schedules/list.html'

	def get_queryset(self):
		queryset = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))
		query = self.request.GET.get('q')
		if query:
			if query.lower() in 'returner':
				queryset = queryset.filter(summers_worked__gt=0)
			elif query.lower() in 'new':
				queryset = queryset.filter(summers_worked__iexact=0)
			else:
				queryset = queryset.filter(
					Q(first_name__icontains = query) |
					Q(last_name__icontains = query) |
					Q(title__iexact = query) |
					Q(gender__iexact = query) |
					Q(age__iexact = query) |
					Q(class_year__iexact = query)
				)
		return queryset

	def get_context_data(self, *args, **kwargs):
		context = super(StapherList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Staphers'
		context['link'] = 'schedules:stapher-create'
		context['link_title'] = 'New Stapher'
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
		context['title'] = f'Edit - {self.get_object()}'
		return context

	def get_queryset(self):
		return Stapher.objects.all()

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
				Q(title__icontains = query)
			)
		return queryset.order_by('day','start', 'title')
		

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Shifts'
		context['link'] = 'schedules:shift-create'
		context['link_title'] = 'New Shift'
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
	
	def get_form_kwargs(self):
		kwargs = super(ShiftCreate, self).get_form_kwargs()
		kwargs['user_id'] = self.request.user.id
		return kwargs

class ShiftUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/form.html'
	form_class = ShiftCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftUpdate, self).get_context_data(*args, **kwargs)
		title = self.get_object().title
		context['title'] = f'Edit - {title}'
		return context

	def get_queryset(self):
		return Shift.objects.all()

	def get_form_kwargs(self):
		kwargs = super(ShiftUpdate, self).get_form_kwargs()
		kwargs['user_id'] = self.request.user.id
		return kwargs

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
