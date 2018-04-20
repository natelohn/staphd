import datetime
import json
import os

from celery import current_task
from celery.result import AsyncResult
# from dateutil.parser import parse
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
from operator import attrgetter

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
	template_name = 'schedules/stapher_list.html'

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
					query_explanation += f' have the \'{query}\' qualification,'
				else:
					names_contain = all_staphers.filter( Q(first_name__icontains = query) | Q(last_name__icontains = query))
					if names_contain: query_explanation += f' have names containing \'{query}\','

					title_exact = all_staphers.filter(title__iexact = query)
					if title_exact: query_explanation += f' have the \'{query}\' title,'

					class_year_exact = all_staphers.filter(class_year__iexact = query)
					if class_year_exact: query_explanation += f' graduate in {query},'

					age_exact = all_staphers.filter(age__iexact = query)
					if age_exact: query_explanation += f' are {query} years old,'

					summers_exact = all_staphers.filter(summers_worked__iexact = query)
					if summers_exact: query_explanation += f' have worked {query} summer(s),'

					queryset = list(names_contain) + list(title_exact) + list(class_year_exact) + list(age_exact) + list(summers_exact)
				filtered_query_set = list(set(filtered_query_set) & set(queryset))

				# Used for the query_explanation
				if len(querylist) > 1 and query == querylist[-2].lower().strip():
					query_explanation = query_explanation[:-1] + ' and'
			cache.set('query_explanation', query_explanation[:-1], None)
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
	template_name = 'schedules/shift_list.html'
	
	# def get_time_from_string(self, time_string):
	# 	time = parse(time_string)
	# 	print(f'{time_string} -> {time}')


	def get_queryset(self, *args, **kwargs):	
		all_shifts = Shift.objects.all()
		query = self.request.GET.get('q')
		if query:
			filtered_shifts = all_shifts
			all_staphings = Staphing.objects.all()
			qual_titles = [q.title for q in Qualification.objects.all()]
			query_explanation = "Showing shifts that"
			querylist = query.split(',')
			for query in querylist:
				query = query.lower().strip()
				if query == 'covered':
					queryset = [shift for shift in all_shifts if shift.is_covered(all_staphings)]
					query_explanation += ' are covered,'
				elif query == 'uncovered':
					queryset = [shift for shift in all_shifts if not shift.is_covered(all_staphings)]
					query_explanation += ' are not covered,'
				else:
					title_contains = all_shifts.filter(title__icontains = query)
					if title_contains: query_explanation += f' have titles containing \'{query}\','

					days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
					day = days.index(query) if query in days else -1
					day_exact = all_shifts.filter(day__exact = day) #Index returns -1 when it is not in the list
					if day_exact: query_explanation += f' are on {query.capitalize()},'

					# time = self.get_time_from_string(query)
					

					queryset = list(title_contains) + list(day_exact)
				filtered_shifts = list(set(filtered_shifts) & set(queryset))

				# Used for the query_explanation
				if len(querylist) > 1 and query == querylist[-2].lower().strip():
					query_explanation = query_explanation[:-1] + ' and'
			all_shifts = filtered_shifts
			cache.set('query_explanation', query_explanation[:-1], None)
		
		# If there is no query then we see if they have sorted the shifts and return the appr
		else:
			cache.set('query_explanation', None, 0)
			if 'sort' in self.kwargs:
				sort_type = self.kwargs['sort']
				if self.kwargs['key']:
					key = self.kwargs['key']
					if sort_type == 'days':
						all_shifts = Shift.objects.filter(day__iexact = key)
					if sort_type == 'qualifications':
						q = Qualification.objects.get(id = key)
						all_shifts = [s for s in Shift.objects.all() if s.has_qualification(q.title)]
					if sort_type == 'flags':
						f = Flag.objects.get(id = key)
						all_shifts = [s for s in all_shifts if s.has_flag(f.title)]
					if sort_type == 'staphers':
						stapher_staphings = Staphing.objects.filter(stapher__id = key)
						all_shifts = [s.shift for s in stapher_staphings]
		return sorted(all_shifts, key = attrgetter('day', 'start'))
		

	
	def get_sort_options(self):
		options_txt = ['Days', 'Qualifications', 'Flags', 'Staphers']
		options = []
		for i, txt in enumerate(options_txt):
			obj = {'name':txt, 'link':txt.lower()}
			options.append(obj)
		return options

	def readable(self, text):
		text_array = [txt for txt in text.split('-')]
		readable_txt = ''
		for txt in text_array:
			readable_txt += txt.capitalize() + ' '
		return readable_txt[:-1]

	def get_sort_keys(self):
		day_titles = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
		days = [{'title':day, 'sort':'days', 'value':i} for i, day in enumerate(day_titles)]
		qualifications = [{'title':self.readable(q.title), 'sort':'qualifications', 'value':q.id} for q in Qualification.objects.all().order_by('title')]
		flags = [{'title':self.readable(f.title), 'sort':'flags', 'value':f.id} for f in Flag.objects.all().order_by('title')]
		staph = [{'title':s.full_name(), 'sort':'staphers', 'value':s.id} for s in Stapher.objects.all().order_by('first_name')]
		key_dict = {'days':days, 'qualifications':qualifications, 'flags':flags, 'staphers':staph}
		return key_dict


	def get_context_data(self, *args, **kwargs):
		context = super(ShiftList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Shifts'
		context['link'] = 'schedules:shift-create'
		context['link_title'] = 'New Shift'
		context['query_explanation'] = cache.get('query_explanation')
		context['shift_sort_options'] = self.get_sort_options()
		context['shift_displayed_msg'] = 'All Shifts'
		query_explanation = cache.get('query_explanation')
		if query_explanation:
			context['shift_displayed_msg'] = query_explanation
		elif 'sort' in self.kwargs:
			sort_type = self.kwargs['sort']
			context['key_msg'] = 'Select ' + sort_type.capitalize()[:-1]
			key_dict = self.get_sort_keys()
			if sort_type in key_dict:
				keys = key_dict[sort_type]
				context['shift_sort_keys'] = keys
				url_key = self.kwargs['key']
				if url_key:
					for key in keys:
						obj_key = key['value']
						if int(url_key) == obj_key:
							context['shift_displayed_msg'] = key['title'] + ' Shifts'
		return context

class ShiftDetail(LoginRequiredMixin, DetailView):
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
