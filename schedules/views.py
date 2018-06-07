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
from .forms import AddShiftsForm, FlagCreateForm, ScheduleCreateForm, SettingsParameterForm, SettingsPreferenceForm, ShiftCreateForm, StapherCreateForm, QualificationCreateForm, ShiftSetCreateForm, AddShiftsToSetForm
from .models import Flag, Schedule, Shift, ShiftSet, Stapher, Staphing, Master, Parameter, Qualification
from .models import Settings as ScheduleBuildingSettings
from .tasks import build_schedules_task, update_files_task
from .view_helpers import get_shifts_to_add, get_week_schedule_view_info, make_shifts_csv, make_staphings_csv


class HomeView(LoginRequiredMixin, TemplateView):
	template_name = 'home.html'

	def get_context_data(self, *args, **kwargs):
		context = super(HomeView, self).get_context_data(*args, **kwargs)
		try:
			schedule = Schedule.objects.get(active__exact = True)
			context['schedule'] = schedule
			context['percent_complete'] = schedule.get_percent_complete()
		except:
			print('No schedule found in HomeView')
		return context

# Download Based Views
class DownloadView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/download.html'

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
def download_individual(request, *args, **kwargs):
	return download_file(request, 'schedules.xlsx')

@login_required
def download_masters(request, *args, **kwargs):
	return download_file(request, 'masters.xlsx')

@login_required
def download_meals(request, *args, **kwargs):
	return download_file(request, 'meal-masters.xlsx')

@login_required
def download_analytics(request, *args, **kwargs):
	return download_file(request, 'analytics.xlsx')

# Schedule Building based Views
@login_required
def build_view(request, *args, **kwargs):
	template = 'schedules/schedule.html'
	try:
		schedule = Schedule.objects.get(active__exact = True)
		context = {'schedule':schedule.title}
	except:
		context = {}
	task_id = cache.get('current_task_id')
	if task_id:
		template = 'schedules/progress.html'
		context['task_id'] = task_id
	return render(request, template, context) 

class SettingParameterUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/settings_select.html'
	form_class = SettingsParameterForm
	success_url = reverse_lazy('schedules:settings-rank')

	def get_queryset(self):
		return ScheduleBuildingSettings.objects.all()

	def get_object(self):
		try:
			return ScheduleBuildingSettings.objects.get()
		except:
			return Http404

	def get_context_data(self, *args, **kwargs):
		context = super(SettingParameterUpdate, self).get_context_data(*args, **kwargs)
		context['select'] = True
		context['all_parameters'] = Parameter.objects.all().order_by('rank')
		return context

@login_required
def rank_settings(request, *args, **kwargs):
	try:
		settings = ScheduleBuildingSettings.objects.get()
		parameters = settings.parameters.all()
		template = 'schedules/settings_rank.html'
		context = {}
		context['rank'] = True
		context['parameters'] = settings.parameters.all().order_by('rank')
		return render(request, template, context)
	except:
		return Http404

@login_required
def swap_rank(request, param_id, parameters):
	search_param = None
	swap_param = None
	for param in parameters:
		if param.id == param_id:
			search_param = param
			break
		swap_param = param
	if search_param and swap_param:
		search_param.swap_rankings(swap_param)
	return rank_settings(request)

@login_required
def rank_up(request, *args, **kwargs):
	try:
		up_param_id = int(kwargs['pk'])
		settings = ScheduleBuildingSettings.objects.get()
		parameters = settings.parameters.all().order_by('rank') #Highest Raking to Lowest
		return swap_rank(request, up_param_id, parameters)
	except:
		return Http404

@login_required
def rank_down(request, *args, **kwargs):
	try:
		down_param_id = int(kwargs['pk'])
		settings = ScheduleBuildingSettings.objects.get()
		parameters = settings.parameters.all().order_by('-rank') #Lowest Raking to Highest
		return swap_rank(request, down_param_id, parameters)
	except:
		return Http404

class SettingPreferenceUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/settings_auto.html'
	form_class = SettingsPreferenceForm
	success_url = reverse_lazy('schedules:schedule')

	def get_queryset(self):
		return ScheduleBuildingSettings.objects.all()

	def get_object(self):
		try:
			return ScheduleBuildingSettings.objects.get()
		except:
			return Http404

	def get_context_data(self, *args, **kwargs):
		context = super(SettingPreferenceUpdate, self).get_context_data(*args, **kwargs)
		context['auto'] = True
		settings = self.get_object()
		context['auto_schedule'] = settings.auto_schedule
		context['auto_threshold'] = settings.auto_threshold
		context['random'] = settings.tie_breaker == 0
		context['rank_based'] = settings.tie_breaker == 1
		return context

@login_required
@csrf_exempt
def build_schedules(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active__exact = True)
	except:
		return render(request,'schedules/schedule.html', {'schedule_error_message':'Must select a schedule first.'})
	task_id = cache.get('current_task_id')
	if not task_id:
		schedule_id = schedule.id
		task = build_schedules_task.delay(schedule_id)
		task_id = task.task_id
		cache.set('current_task_id', task_id, 3000)	
	request.session['task_id'] = task_id
	context = {'task_id':task_id}
	context['schedule'] = schedule.title
	return render(request,'schedules/progress.html', context)

@login_required
@csrf_exempt
def update_files(request, *args, **kwargs):
	context = {}
	task_id = cache.get('current_task_id')
	if not task_id:
		try:
			schedule = Schedule.objects.get(active__exact = True)
			schedule_id = schedule.id
		except:
			return render(request,'schedules/schedule.html', {'update_error_message':'Must select a schedule first.'})
		staphings = Staphing.objects.filter(schedule__id = schedule_id)
		if not staphings:
			template = 'schedules/schedule.html'
			context['update_error_message'] = 'No Shifts Scheduled - Must Schedule Shifts First'
		else:
			template = 'schedules/progress.html'
			task = update_files_task.delay(schedule_id)
			task_id = task.task_id
			cache.set('current_task_id', task_id, 3000)
	else:
		template = 'schedules/progress.html'
		context['update_error_message'] = 'Please wait for the current task to complete.'

	request.session['task_id'] = task_id
	context['task_id'] = task_id
	context['schedule'] = schedule.title
	return render(request, template, context)

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
def recommendations_view(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active__exact = True)
		settings = ScheduleBuildingSettings.objects.get()
	except:
		return Http404
	template = 'schedules/recommendation.html'
	recs = cache.get('recommendation')
	shift = cache.get('recommended_shift')
	if not recs or not shift:
		print(f'No recommendations to be made (rec = {recs})')
		return HttpResponseRedirect(reverse('schedules:schedule'))
	parameters = settings.parameters.all().order_by('rank')
	context = {}
	rows = []
	for rec in recs:
		stapher = rec[0]
		scores = rec[1]
		wins = rec[2]
		row = {}
		row['stapher'] = stapher
		cells = []
		for i, score in enumerate(scores):
			cell = {}
			cell['score'] = score
			cell['win'] = wins[i]
			cells.append(cell)
		row['cells'] = cells
		try:
			stapher_staphings = Staphing.objects.filter(schedule_id__exact= schedule.id, stapher_id__exact = stapher.id)
		except:
			stapher_staphings = []
		all_rows_for_time = get_week_schedule_view_info(stapher, stapher_staphings, shift, schedule)
		row['schedule'] = [all_rows_for_time]
		rows.append(row)
	context['parameters'] = parameters
	context['rows'] = rows
	context['shift'] = shift
	return render(request, template, context)

@login_required
def add_recommendation(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	try:
		stapher = Stapher.objects.get(id = stapher_id)
		schedule = Schedule.objects.get(active__exact = True)
	except:
		return Http404
	shift = cache.get('recommended_shift')
	if not shift:
		return Http404
	else:
		new_staphing = Staphing(schedule = schedule, stapher = stapher, shift = shift)
		new_staphing.save()
	return HttpResponseRedirect(reverse('schedules:building'))


# Settings based views
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

@login_required
def stapher_schedule(request, args, kwargs, form):
	stapher_id = kwargs['pk']
	try:
		stapher = Stapher.objects.get(id__exact = stapher_id)
	except:
		return Http404
	try:
		schedule = Schedule.objects.get(active__exact = True)
		all_staphings = Staphing.objects.filter(schedule_id__exact = schedule.id)
		stapher_staphings = all_staphings.filter(stapher_id__exact = stapher.id)
	except:
		schedule = None
		all_staphings = []
		stapher_staphings = []
	if schedule:
		schedule_msg = f'{stapher.full_name()}\'s Shifts on "{schedule.title}"'
	else:
		schedule_msg = f'Unable to view {stapher.full_name()} schedule since no schedule selected...'

	if form:
		shifts_in_set = Shift.objects.filter(shift_set = schedule.shift_set).order_by('day', 'start')
		new_shift_rows = get_shifts_to_add(stapher, shifts_in_set, all_staphings, stapher_staphings)
	else:
		new_shift_rows = None

	all_rows_for_time = get_week_schedule_view_info(stapher, stapher_staphings, None, schedule)
	template = 'schedules/stapher_schedule.html'
	context = {}
	context['stapher'] = stapher
	context['name'] = stapher.full_name()
	context['schedule'] = schedule
	context['schedule_msg'] = schedule_msg 
	context['can_delete'] = True
	context['all_rows_for_time'] = all_rows_for_time
	context['form'] = form
	context['new_shift_rows'] = new_shift_rows
	return render(request, template, context)

@login_required
def stapher_schedule_view(request, *args, **kwargs):
	return stapher_schedule(request, args, kwargs, None)


@login_required
def stapher_shift_scheduled(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	shift_id = kwargs['s']
	try:
		stapher = Stapher.objects.get(id__exact = stapher_id)
		shift = Shift.objects.get(id__exact = shift_id)
	except:
		return Http404
	try:
		schedule = Schedule.objects.get(active__exact = True)
		if schedule:
			new_staphing = Staphing(stapher = stapher, shift = shift, schedule = schedule)
			new_staphing.save()
	except:
		schedule = None
		stapher_staphings = []

	return HttpResponseRedirect(reverse('schedules:stapher-schedule-shifts', kwargs={'pk': stapher.id}))

@login_required
def stapher_schedule_add(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	try:
		schedule = Schedule.objects.get(active = True)
		stapher = Stapher.objects.get(id__exact = stapher_id)
	except:
		return Http404
	if request.method == 'POST':
		form = AddShiftsForm(request.POST)
		print(f'Valid = {form.is_valid()}')
		if form.is_valid():
			for shift in form.cleaned_data['added_shifts']:
				new_staphing = Staphing(stapher = stapher, schedule = schedule, shift = shift)
				new_staphing.save()
			return HttpResponseRedirect(reverse('schedules:stapher-schedule', kwargs={'pk': stapher.id}))
	else:
		form = AddShiftsForm()
	return stapher_schedule(request, args, kwargs, form)


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
		try:
			schedule = Schedule.objects.get(active__exact = True)
			all_staphings = Staphing.objects.filter(schedule_id__exact = schedule.id)
			no_schedule = False
			all_shifts = Shift.objects.filter(shift_set = schedule.shift_set)
		except:
			all_staphings = []
			no_schedule = True
			all_shifts = Shift.objects.all()
		query = self.request.GET.get('q')
		if query:
			filtered_shifts = all_shifts
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
					if no_schedule:
						explanation_str += ' (no current schedule)'
					else:
						explanation_str += f' in the "{schedule.title}" schedule.'
					query_explanation.append(explanation_str)
					
				elif query == 'uncovered':
					queryset = [shift for shift in all_shifts if not shift.is_covered(all_staphings)]
					explanation_str = '- are not not covered' if negate_query else '- are not covered'
					if no_schedule:
						explanation_str += ' (no current schedule)'
					else:
						explanation_str += f' in the "{schedule.title}" schedule.'
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
							if not no_schedule:
								explanation_str += f' in the "{schedule.title}" schedule.'								
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

					# Search by Shift Set
					shift_set_match = [s for s in filtered_shifts if query in s.shift_set.title ]
					explanation_str = f'- are not in the \'{query}\' shift set' if negate_query else f'- are in the \'{query}\' shift set'
					if shift_set_match: query_explanation.append(explanation_str)


					queryset = name_contains + list(title_contains) + list(day_exact) + during_time + qual_match + flag_match + shift_set_match

				if negate_query: queryset = list(set(all_shifts) - set(queryset))
				filtered_shifts = list(set(filtered_shifts) & set(queryset))

			
			if len(all_shifts) == len(filtered_shifts): query_explanation = ['- Result includes all shifts.']
			all_shifts = filtered_shifts
			cache.set('query_explanation', query_explanation, 60)
		
		# If there is no query then we see if they have sorted the shifts and return the appr
		else:
			cache.set('query_explanation', None, 0)
			if 'sort' in self.kwargs:
				sort_type = self.kwargs['sort']
				if self.kwargs['key']:
					key = self.kwargs['key']
					if sort_type == 'days':
						all_shifts = all_shifts.filter(day__iexact = key)
					if sort_type == 'qualifications':
						q = Qualification.objects.get(id = key)
						all_shifts = [s for s in all_shifts if s.has_qualification(q.title)]
					if sort_type == 'flags':
						f = Flag.objects.get(id = key)
						all_shifts = [s for s in all_shifts if s.has_flag(f.title)]
					if sort_type == 'staphers':
						stapher_staphings = all_staphings.filter(stapher__id = key) if all_staphings else []
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
		try:
			schedule = Schedule.objects.get(active__exact = True)
		except:
			schedule = None
		context = super(ShiftList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Shifts'
		context['link'] = 'schedules:shift-create'
		context['query_explanation'] = cache.get('query_explanation')
		context['shift_sort_options'] = self.get_sort_options()
		if schedule:
			context['shift_displayed_msg'] = [f'Showing {schedule.shift_set} Shifts']
		else:
			context['shift_displayed_msg'] = [f'Showing Shifts in All Shift Sets', '- select a schedule or search by shifts sets title to show a specific shift set.']
		query_explanation = cache.get('query_explanation')
		if query_explanation:
			context['shift_displayed_msg'] += query_explanation
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
							elif sort_type in 'staphers':
								if schedule:
									msg = key['title'] + f'\'s Shifts in the "{schedule.title}" schedule.'
								else:
									msg = 'No Current Schedule'
							else:
								msg = key['title'] + '\'s Shifts'
							if schedule:
								msg += f' from {schedule.shift_set.title}'
							else:
								msg += f' from All Shift Sets'
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
		try:
			schedule = Schedule.objects.get(active__exact = True)
			schedule_title = f'Schedule: {schedule.title}'
			staphings = Staphing.objects.filter(schedule_id = schedule.id)
		except:
			schedule_title = 'No Schedule Selected.'
			staphings = []
		context['schedule_title'] = schedule_title
		working_shift = [s.stapher for s in staphings if s.shift == shift]
		context['working_shift'] = sorted(working_shift, key = attrgetter('first_name'))
		context['working_msg'] = str(len(working_shift))+ ' Workers Scheduled on :' if working_shift else 'No Workers Scheduled.'
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

# Schedule Based Views
@login_required
def schedule_selected(request, *args, **kwargs):
	schedule_id = kwargs['pk']
	try:
		schedule = Schedule.objects.get(id__exact = schedule_id)
		schedule.active = True
		schedule.save()
		for other_schedule in Schedule.objects.exclude(id__exact = schedule.id):
			other_schedule.active = False
			other_schedule.save()
	except:
		return Http404
	return build_view(request)

class ScheduleCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/schedule_form.html'
	form_class = ScheduleCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'New Schedule'
		context['cancel_url'] = 'schedules:select'
		context['create'] = True
		return context

class ScheduleList(LoginRequiredMixin, ListView):
	template_name = 'schedules/schedule_list.html'

	def get_queryset(self):
		return Schedule.objects.exclude(active__exact = True).order_by(Lower('title'))

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleList, self).get_context_data(*args, **kwargs)
		try:
			schedule = Schedule.objects.get(active__exact = True)
			context['schedule'] = schedule
		except:
			print('No Active Schedule')
		return context

class ScheduleDetail(LoginRequiredMixin, DetailView):
	queryset = Schedule.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleDetail, self).get_context_data(*args, **kwargs)
		schedule = self.get_object()
		context['title'] = schedule.title
		context['percent'] = schedule.get_percent_complete()
		context['shift_set'] = schedule.shift_set.title
		return context

class ScheduleDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Schedule
	success_url = reverse_lazy('schedules:schedule')

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleDelete, self).get_context_data(*args, **kwargs)
		schedule = self.get_object()
		context['schedule_id'] = schedule.id
		return context

class ScheduleUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/schedule_form.html'
	form_class = ScheduleCreateForm

	def get_queryset(self):
		return Schedule.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleUpdate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Edit Schedule'
		context['cancel_url'] = 'schedules:select'
		return context

def schedule_duplicate(request, *args, **kwargs):
	duplicate_id = kwargs['pk']
	try:
		schedule = Schedule.objects.get(active = True)
		duplicate_schedule = Schedule.objects.get(id__exact = duplicate_id)
		
		# Delete all old staphings
		delete_staphings = Staphing.objects.filter(schedule_id__exact = schedule.id).delete()

		#Copy new staphings
		copy_staphings = Staphing.objects.filter(schedule_id__exact = duplicate_schedule.id)
		for staphing in copy_staphings:
			new_staphing = Staphing(schedule = schedule, stapher = staphing.stapher, shift = staphing.shift)
			new_staphing.save()
	except:
		return Http404
	return HttpResponseRedirect(reverse('schedules:schedule-detail', kwargs={'pk':schedule.id}))

# Staphing Based Views
class StaphingDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/staphing_delete.html'
	model = Staphing

	def get_queryset(self):
		return Staphing.objects.all()

	def get_context_data(self, *args, **kwargs):
		context = super(StaphingDelete, self).get_context_data(*args, **kwargs)
		staphing = self.get_object()
		stapher = staphing.stapher
		try:
			schedule = Schedule.objects.get(active__exact = True)
			staphings = Staphing.objects.filter(schedule_id__exact = schedule.id)
		except:
			schedule = None
			staphings = []
		all_rows_for_time = get_week_schedule_view_info(stapher, staphings, None, schedule)
		template = 'schedules/stapher_schedule.html'
		context['stapher'] = stapher
		context['name'] = stapher.full_name()
		context['schedule'] = schedule
		context['can_delete'] = True
		context['all_rows_for_time'] = all_rows_for_time
		return context

	def get_success_url(self):
		staphing = self.get_object()
		return reverse_lazy('schedules:stapher-schedule', kwargs={'pk':staphing.stapher.id})


class ShiftSetCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/schedule_form.html'
	form_class = ShiftSetCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftSetCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'New Shift Set'
		context['cancel_url'] = 'schedules:schedule-create'
		return context

@login_required
def shift_set_add(request, *args, **kwargs):
	set_id = kwargs['pk']
	try:
		shift_set = ShiftSet.objects.get(id = set_id)
	except:
		return Http404
	if request.method == 'POST':
		form = AddShiftsToSetForm(request.POST)
		if form.is_valid():
			for shift in form.cleaned_data['added_shifts']:
				shift.shift_set = shift_set
				shift.id = None # This will copy the shift object 
				shift.save() # .... and save it as another instance

			return HttpResponseRedirect(reverse('schedules:schedule-create'))
	else:
		template = 'schedules/shift_set_form.html'
		form = AddShiftsToSetForm()
		context = {}
		context['title'] = f'Add Shifts to {shift_set.title}'
		context['cancel_url'] = 'schedules:schedule-create'
		context['shift_sets'] = ShiftSet.objects.exclude(id = set_id)
		context['flags'] = Flag.objects.all().order_by('title')
		all_shifts = Shift.objects.all().order_by('title','shift_set','day','start')
		context['all_shifts'] = all_shifts
		shifts_in_set = list(Shift.objects.filter(shift_set = shift_set))
		context['shifts_in_set'] = shifts_in_set
		shifts_arr = []
		for shift in all_shifts:
			flags = []
			for f in shift.flags.all():
				flags.append(f.id)
			shift = [shift.id, shift.shift_set.id, flags]
			shifts_arr.append(shift)
		context['shifts_arr'] = shifts_arr
	template
	return render(request, template, context)

