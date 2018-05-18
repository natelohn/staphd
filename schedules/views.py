import boto3
import botocore
import datetime
import json
import os

from celery import current_task
from celery.result import AsyncResult
from dateutil.parser import parse
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
from staphd.celery import app

from .analytics import get_readable_time
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

class Settings(LoginRequiredMixin, TemplateView):
    template_name = 'settings.html'

class FlagSettings(LoginRequiredMixin, TemplateView):
	template_name = 'settings_edit.html'
	
	def get_context_data(self, *args, **kwargs):
		context = super(FlagSettings, self).get_context_data(*args, **kwargs)
		context['list'] = Flag.objects.all().order_by(Lower('title'))
		context['delete_link'] = 'schedules:flag-delete'
		context['create_link'] = 'schedules:flag-create'
		context['object_name'] = 'Flag'
		return context

class QualificationSettings(LoginRequiredMixin, TemplateView):
	template_name = 'settings_edit.html'

	def get_context_data(self, *args, **kwargs):
		context = super(QualificationSettings, self).get_context_data(*args, **kwargs)
		context['list'] = Qualification.objects.all().order_by(Lower('title'))
		context['delete_link'] = 'schedules:qualification-delete'
		context['create_link'] = 'schedules:qualification-create'
		context['object_name'] = 'Qualification'
		return context


@login_required
def build_view(request):
	template = 'schedules/schedule.html'
	context = {}
	task_id = cache.get('current_task_id')
	if task_id:
		template = 'schedules/progress.html'
		context['task_id'] = task_id
	return render(request, template, context) 

# Download Based Views
@login_required
def download_file(request, filename):
	path = 'static/xlsx/' + filename
	s3 = boto3.resource('s3')
	try:
		s3.Bucket('staphd').download_file(filename, path)
		with open(path, 'rb') as file:
			response = HttpResponse(file.read(), content_type="application/xlsx")
			response['Content-Disposition'] = 'inline; filename=' + filename
			return response
	except botocore.exceptions.ClientError as e:
		if e.response['Error']['Code'] == "404":
			print("The object does not exist.")
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
def delete_schedule(request):
	task_id = cache.get('current_task_id')
	template = 'schedules/schedule.html'
	context = {}
	if not task_id:
		staphings = Staphing.objects.all()
		if staphings:
			Staphing.objects.all().delete()
			context['success_message'] = 'Schedule Successfully Deleted'
		else:
			context['success_message'] = 'No Schedule to Delete'
	else:
		template = 'schedules/progress.html'
		context['success_message'] = 'Please wait for the current task to complete.'
		context['task_id'] = task_id
	return render(request, template, context)

# Schedule Building based Views
@login_required
@csrf_exempt
def build_schedules(request):
	task_id = cache.get('current_task_id')
	if not task_id:
		staphings = Staphing.objects.all()
		if staphings:
			return render(request,'schedules/schedule.html', {'schedule_error_message':'Must Delete Current Schedule First'})
		task = build_schedules_task.delay()
		task_id = task.task_id
		cache.set('current_task_id', task_id, 1500)
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
			print(f'			task_id -> {task_id}')
			task = app.AsyncResult(task_id)
			data = task.result or task.state
			print(f'			data -> {data}')
			task_running = not task.ready() and not isinstance(data, str)
			print(f'			task_running -> {task_running}')
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
	context = {}
	task_id = cache.get('current_task_id')
	if not task_id:
		schedule_id = cache.get('schedule_id') #TODO: Update schedule_id to be the only active schedule
		staphings = Staphing.objects.filter(schedule__id = schedule_id)
		if not staphings:
			template = 'schedules/schedule.html'
			context['update_error_message'] = 'No Shifts Scheduled - Must Schedule Shifts First'
		else:
			template = 'schedules/progress.html'
			task = update_files_task.delay(schedule_id)
			task_id = task.task_id
			cache.set('current_task_id', task_id, 1500)
	else:
		template = 'schedules/progress.html'
		context['update_error_message'] = 'Please wait for the current task to complete.'

	request.session['task_id'] = task_id
	context['task_id'] = task_id
	return render(request, template, context)

# Stapher based views
class StapherList(LoginRequiredMixin,ListView):
	template_name = 'schedules/stapher_list.html'

	def get_queryset(self):
		all_staphers = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))	
		query = self.request.GET.get('q')
		filtered_query_set = all_staphers
		if query:
			qual_titles = [q.title.lower() for q in Qualification.objects.all()]
			query_explanation = "Search results showing staphers that"
			querylist = list(filter(bool, [q.strip() for q in query.split(',')])) #Removes all empty space queries
			query_explanation = "Search results showing staphers that" if querylist else ''
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
					query_explanation += ' identify as male,'
				elif query == 'female':
					queryset = all_staphers.filter(gender__exact = 0)
					query_explanation += ' identify as female,'
				elif query == 'non-binary':
					queryset = all_staphers.filter(gender__exact = 2)
					query_explanation += ' identify as non-binary'
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
			cache.set('query_explanation', query_explanation[:-1], 60)
		else:
			cache.set('query_explanation', None, 0)

		return filtered_query_set

	def get_context_data(self, *args, **kwargs):
		context = super(StapherList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Staphers'
		context['link'] = 'schedules:stapher-create'
		context['query_explanation'] = cache.get('query_explanation')
		return context

class StapherDetail(LoginRequiredMixin, DetailView):
	queryset = Stapher.objects.all()
	
	def get_context_data(self, *args, **kwargs):
		context = super(StapherDetail, self).get_context_data(*args, **kwargs)
		stapher = self.get_object()
		context['name'] = stapher.full_name()
		suffixes = ['st', 'nd', 'rd', 'th']
		summers = stapher.summers_worked if stapher.summers_worked <= 3 else 3
		suffix = suffixes[summers]
		context['readable_summer'] = str(stapher.summers_worked + 1) + suffix
		context['qualifications'] = sorted(stapher.qualifications.all(), key = attrgetter('title'))
		return context

class StapherCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = StapherCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(StapherCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'New Stapher'
		context['cancel_url'] = 'schedules:stapher-list'
		context['qualification_label_name'] = 'stapher_qualifications_hardcoded'
		return context

	def form_valid(self, form):
		instance = form.save(commit = False)
		instance.user = self.request.user
		return super(StapherCreate, self).form_valid(form)

	def get_form_kwargs(self):
		kwargs = super(StapherCreate, self).get_form_kwargs()
		kwargs['auto_id'] = 'stapher_%s'
		return kwargs

class StapherUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/form.html'
	form_class = StapherCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(StapherUpdate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Edit Stapher'
		context['qualification_label_name'] = 'stapher_qualifications_hardcoded'
		return context

	# TODO: See if this works (takes from the create form in forms.py)
	def form_valid(self, form):
		instance = form.save(commit = False)
		instance.user = self.request.user
		return super(StapherUpdate, self).form_valid(form)

	def get_form_kwargs(self):
		kwargs = super(StapherUpdate, self).get_form_kwargs()
		kwargs['auto_id'] = 'stapher_%s'
		return kwargs

	def get_queryset(self):
		return Stapher.objects.all()

class StapherDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Stapher
	success_url = reverse_lazy('schedules:stapher-list')

# Shift based views
class ShiftList(LoginRequiredMixin, ListView):
	template_name = 'schedules/shift_list.html'
	
	def get_time_from_string(self, time_string):
		try:
			if ':' in time_string or 'am' in time_string or 'pm' in time_string:
				string_dt = parse(time_string)
				time = datetime.time(string_dt.hour, string_dt.minute, 0, 0)
			else:
				raise Exception
		except:
			time =  None
		return time

	def get_queryset(self, *args, **kwargs):	
		all_shifts = Shift.objects.all()
		query = self.request.GET.get('q')
		if query:
			filtered_shifts = all_shifts
			all_staphings = Staphing.objects.all()
			qual_titles = [q.title for q in Qualification.objects.all()]
			flag_titles = [f.title for f in Flag.objects.all()]
			query_explanation = ["Showing shifts that:"]
			querylist = list(filter(bool, [q.strip() for q in query.split(',')])) #Removes all empty space queries
			for query in querylist:
				negate_query = True if '!' == query[0] and len(query) > 1 else False
				if negate_query: query = query[1:]
				upper_query = query
				query = query.lower()
				
				# Special Queries (covered/uncovered, just flag, just qualification)
				if query == 'covered':
					queryset = [shift for shift in all_shifts if shift.is_covered(all_staphings)]
					explanation_str =  '- are not covered' if negate_query else '- are covered'
					query_explanation.append(explanation_str)
				elif query == 'uncovered':
					queryset = [shift for shift in all_shifts if not shift.is_covered(all_staphings)]
					explanation_str = '- are not not covered' if negate_query else '- are not covered'
					query_explanation.append(explanation_str)
				elif '*' in query:
					# To solve for shifts w/ both qualifications and flags always showing up
					if '*q' in query:
						upper_query = upper_query.replace('*q', '').strip()
						queryset = [s for s in filtered_shifts if s.has_qualification(upper_query)] if upper_query in qual_titles else []
						explanation_str = f'- do not have the \'{upper_query}\' qualification' if negate_query else f'- have the \'{upper_query}\' qualification'
					elif '*f' in query:
						upper_query = upper_query.replace('*f', '').strip()
						queryset = [s for s in filtered_shifts if s.has_flag(upper_query)] if upper_query in flag_titles else []
						explanation_str = f'- do not have the \'{upper_query}\' flag' if negate_query else f'- have the \'{upper_query}\' flag'
					else:
						queryset = []
					if queryset: query_explanation.append(explanation_str)
				else:
					# Search by Name of Stapher Scheduled
					name_contains = []
					explanations = set()
					for s in all_staphings:
						if query == s.stapher.first_name.lower() or query == s.stapher.last_name.lower() or query == s.stapher.full_name().lower():
							print(s.stapher)
							name_contains.append(s.shift)
							explanation_str = f'- {s.stapher.full_name()} is not working' if negate_query else f'- {s.stapher.full_name()} is working'
							explanations.add(explanation_str)
					if name_contains: query_explanation.extend(list(explanations))

					# Search by Titles
					title_contains = all_shifts.filter(title__icontains = query)
					explanation_str = f'- do not have titles containing \'{query}\'' if negate_query else f'- have titles containing \'{query}\''
					if title_contains: query_explanation.append(explanation_str)

					# Search by Days
					days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
					day = days.index(query) if query in days else -1
					day_exact = all_shifts.filter(day__exact = day) #Index returns -1 when it is not in the list
					explanation_str = f'- are not on {query.capitalize()}' if negate_query else f'- are on {query.capitalize()}'
					if day_exact: query_explanation.append(explanation_str)

					# Search by Time
					time = self.get_time_from_string(query) 
					during_time = [s for s in filtered_shifts if s.is_during_time(time)] if time else []
					explanation_str = f'- are not during {query}' if negate_query else f'- are during {query}'
					if during_time: query_explanation.append(explanation_str)
					
					# Search by Qualification
					qual_match = [s for s in filtered_shifts if s.has_qualification(upper_query)] if upper_query in qual_titles else []
					explanation_str = f'- do not have the \'{upper_query}\' qualification' if negate_query else f'- have the \'{upper_query}\' qualification'
					if qual_match: query_explanation.append(explanation_str)

					# Search by Flag
					flag_match = [s for s in filtered_shifts if s.has_flag(upper_query)] if upper_query in flag_titles else []
					explanation_str = f'- do not have the \'{upper_query}\' flag' if negate_query else f'- have the \'{upper_query}\' flag'
					if flag_match: query_explanation.append(explanation_str)


					queryset = name_contains + list(title_contains) + list(day_exact) + during_time + qual_match + flag_match 

				if negate_query: queryset = list(set(all_shifts) - set(queryset))
				filtered_shifts = list(set(filtered_shifts) & set(queryset))

			all_shifts = filtered_shifts
			if len(query_explanation) == 1: query_explanation = ['Result includes all shifts.'] 
			cache.set('query_explanation', query_explanation, 60)
		
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
		options_txt = ['Qualifications', 'Flags','Days','Staphers']
		options = []
		for i, txt in enumerate(options_txt):
			obj = {'name':txt, 'link':txt.lower()}
			options.append(obj)
		return options

	def get_sort_keys(self):
		day_titles = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
		days = [{'title':day, 'sort':'days', 'value':i} for i, day in enumerate(day_titles)]
		qualifications = [{'title':q.title, 'sort':'qualifications', 'value':q.id} for q in Qualification.objects.all().order_by(Lower('title'))]
		flags = [{'title':f.title, 'sort':'flags', 'value':f.id} for f in Flag.objects.all().order_by(Lower('title'))]
		staph = [{'title':s.full_name(), 'sort':'staphers', 'value':s.id} for s in Stapher.objects.all().order_by(Lower('first_name'))]
		key_dict = {'days':days, 'qualifications':qualifications, 'flags':flags, 'staphers':staph}
		return key_dict

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Shifts'
		context['link'] = 'schedules:shift-create'
		context['query_explanation'] = cache.get('query_explanation')
		context['shift_sort_options'] = self.get_sort_options()
		context['shift_displayed_msg'] = ['All Shifts']
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
							if sort_type in ['flags', 'qualifications']:
								msg = 'Shifts with the \'' + key['title'] + '\' ' + sort_type[:-1] 
							else:
								msg = key['title'] + '\'s Shifts'
							context['shift_displayed_msg'] = [msg]
		return context

class ShiftDetail(LoginRequiredMixin, DetailView):
	queryset = Shift.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftDetail, self).get_context_data(*args, **kwargs)
		shift = self.get_object()
		context['day'] = shift.get_day_string()
		context['time_msg'] = get_readable_time(shift.start) + '-' + get_readable_time(shift.end)
		worker_str = ' Workers Needed' if shift.workers_needed > 1 else ' Worker Needed'
		context['needed_msg'] = str(shift.workers_needed) + worker_str
		working_shift = [s.stapher for s in Staphing.objects.all() if s.shift == shift]
		context['working_shift'] = sorted(working_shift, key = attrgetter('first_name'))
		context['working_msg'] = str(len(working_shift))+ ' Workers Scheduled:' if working_shift else 'No Workers Scheduled.'
		context['qualifications'] = sorted(shift.qualifications.all(), key = attrgetter('title'))
		context['flags'] = sorted(shift.flags.all(), key = attrgetter('title'))

		return context

class ShiftCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = ShiftCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'New Shift'
		context['cancel_url'] = 'schedules:shift-list'
		context['qualification_label_name'] = 'shift_qualifications_hardcoded'
		context['flag_label_name'] = 'shift_flags_hardcoded'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(ShiftCreate, self).form_valid(form)
	
	def get_form_kwargs(self):
		kwargs = super(ShiftCreate, self).get_form_kwargs()
		kwargs['auto_id'] = 'shift_%s'
		return kwargs

class ShiftUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/form.html'
	form_class = ShiftCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftUpdate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Edit Shift'
		context['qualification_label_name'] = 'shift_qualifications_hardcoded'
		context['flag_label_name'] = 'shift_flags_hardcoded'
		return context

	def get_queryset(self):
		return Shift.objects.all()

	def get_form_kwargs(self):
		kwargs = super(ShiftUpdate, self).get_form_kwargs()
		kwargs['auto_id'] = 'shift_%s'
		return kwargs

class ShiftDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Shift
	success_url = reverse_lazy('schedules:shift-list')

# Qualification Based Views
class QualificationCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = QualificationCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(QualificationCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Qualification'
		context['cancel_url'] = 'schedules:settings'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(QualificationCreate, self).form_valid(form)

class QualificationDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Qualification
	success_url = reverse_lazy('schedules:settings')

# Flag Based Views
class FlagCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = FlagCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(FlagCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Add Flag'
		context['cancel_url'] = 'schedules:settings'
		return context

	def form_valid(self, form):
		instance = form.save(commit=False)
		instance.user = self.request.user
		return super(FlagCreate, self).form_valid(form)

class FlagDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Flag
	success_url = reverse_lazy('schedules:settings')
