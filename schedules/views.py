import datetime
import json
import os

from celery import current_task
from celery.result import AsyncResult
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, render, redirect
from django.template import RequestContext
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView


from .forms import FlagCreateForm, ShiftCreateForm, StapherCreateForm, QualificationCreateForm
from .models import Flag, Schedule, Shift, Stapher, Staphing, Qualification, Master
from .tasks import build_schedules_task, update_files_task


class HomeView(LoginRequiredMixin, TemplateView):
	template_name = 'home.html'

	def get_context_data(self, *args, **kwargs):
		context = super(HomeView, self).get_context_data(*args, **kwargs)
		percent = 0
		schedule_id = cache.get('schedule_id')
		if schedule_id:
			schedule = Schedule.objects.get(id = schedule_id)
			percent = schedule.get_percent_complete()
		context['percent_complete'] = percent
		return context

class DownloadView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/download.html'

@login_required
def build_view(request):
	task_id = cache.get('current_task_id')
	if task_id:
		task = AsyncResult(task_id)
		data = task.result or task.state
		if 'PENDING' not in data:
			return render(request,'schedules/progress.html', {'task_id':task_id})
		task_id = cache.set('current_task_id', None, 0)
	return render(request, 'schedules/schedule.html', {})


def download_file(request, filename):
	# TODO: add MEDIA ROOT for production
	# file_path = os.path.join(settings.MEDIA_ROOT, path)
	
	file_path = '../output/' + filename
	if os.path.exists(file_path):
		with open(file_path, 'rb') as file:
			# TODO: add MEDIA ROOT for production
			# response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)

			response = HttpResponse(file.read(), content_type="application/xlsx")
			response['Content-Disposition'] = 'inline; filename=' + filename
			return response
	raise Http404

@login_required
def download_individual(request):
	return download_file(request, 'schedules.xlsx')

@login_required
def download_masters(request):
	return download_file(request, 'masters.xlsx')

@login_required
def download_meals(request):
	return download_file(request, 'meal-masters.xlsx')

@login_required
def download_analytics(request):
	return download_file(request, 'analytics.xlsx')

@login_required
@csrf_exempt
def build_schedules(request):
	task_id = cache.get('current_task_id')
	if not task_id:
		task = build_schedules_task.delay()
		task_id = task.task_id
		cache.set('current_task_id', task_id, None)
	request.session['task_id'] = task_id
	context = {'task_id':task_id}
	return render(request,'schedules/progress.html', context)

@login_required
@csrf_exempt
def track_state(request, *args, **kwargs):
	""" A view to report the progress of a task to the user """
	data = 'Fail'
	task_id = cache.get('current_task_id')
	if request.is_ajax():
		if 'task_id' in request.POST.keys() and request.POST['task_id']:
			task_id = request.POST['task_id']
			task = AsyncResult(task_id)
			data = task.result or task.state
			task_running = not task.ready() and not isinstance(data, str)
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
		task_id = cache.get('current_task_id')
		if not task_id:
			task = update_files_task.delay(schedule_id)
			task_id = task.task_id
			cache.set('current_task_id', task_id, None)
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
		all_staphers = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))
		qual_titles = [q.title for q in Qualification.objects.all()]
		query = self.request.GET.get('q')
		filtered_query_set = all_staphers
		if query:
			query_explanation = "Search results showing staphers that"
			querylist = query.split(',')
			for query in querylist:
				query = query.lower().strip()
				if query == 'returners':
					queryset = all_staphers.filter(summers_worked__gt = 0)
					query_explanation += ' are returners,'
				elif query == 'new':
					queryset = all_staphers.filter(summers_worked__exact = 0)
					query_explanation += ' are new,'
				elif query == 'male':
					queryset = all_staphers.filter(gender__exact = 1)
					query_explanation += ' are male,'
				elif query == 'female':
					queryset = all_staphers.filter(gender__exact = 0)
					query_explanation += ' are female,'
				elif query == 'non-binary':
					queryset = all_staphers.filter(gender__exact = 2)
					query_explanation += ' are non-binary,'
				elif query in qual_titles:
					queryset = [stapher for stapher in all_staphers if stapher.has_qualification(query)]
					query_explanation += f' have the {query} qualification,'
				else:
					names_contain = all_staphers.filter( Q(first_name__icontains = query) | Q(last_name__icontains = query))
					if names_contain:
						query_explanation += f' have name\'s containing {query},'

					title_exact = all_staphers.filter(title__iexact = query)
					if title_exact:
						query_explanation += f' have the {query} title,'

					class_year_exact = all_staphers.filter(class_year__iexact = query)
					if class_year_exact:
						query_explanation += f' graduate in {query},'

					age_exact = all_staphers.filter(age__iexact = query)
					if age_exact:
						query_explanation += f' are {query} years old,'

					summers_exact = all_staphers.filter(summers_worked__iexact = query)
					if summers_exact:
						query_explanation += f' have worked {query} summer(s),'

					queryset = list(names_contain) + list(title_exact) + list(class_year_exact) + list(age_exact) + list(summers_exact)
				if len(querylist) > 1 and query == querylist[-2].lower().strip():
					query_explanation = query_explanation[:-1] + ' and'
				filtered_query_set = list(set(filtered_query_set) & set(queryset))
			cache.set('query_explanation', query_explanation[:-1], None)
			print(f'query_explanation = {query_explanation[:-1]}')
		else:
			cache.set('query_explanation', None, 0)
		return filtered_query_set

	def get_context_data(self, *args, **kwargs):
		context = super(StapherList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Staphers'
		context['link'] = 'schedules:stapher-create'
		context['link_title'] = 'New Stapher'
		context['query_explanation'] = cache.get('query_explanation')
		return context

class StapherDetail(LoginRequiredMixin, DetailView):
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
