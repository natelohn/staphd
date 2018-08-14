import boto3
import botocore
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
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from operator import attrgetter
from staphd.celery import app

from .analytics import get_readable_time
from .forms import WeekdayForm, AddShiftsForm, FlagCreateForm, ScheduleCreateForm, SettingsParameterForm, SettingsPreferenceForm, ShiftCreateForm, StapherCreateForm, QualificationCreateForm, ShiftSetCreateForm, AddShiftsToSetForm
from .models import Flag, Schedule, Shift, ShiftSet, Stapher, Staphing, Master, Parameter, Qualification, ShiftPreference
from .models import Settings as ScheduleBuildingSettings
from .special_shifts import get_special_shift_flags, swap_shift_preferences
from .tasks import build_schedules_task, update_files_task, find_ratios_task, place_special_shifts_task, add_shifts_to_set_task
from .helpers import get_shifts_to_add, get_week_schedule_view_info, get_ratio_table, get_ratio_tables_in_window, get_stapher_breakdown_table, get_time_from_string


# Download Based Views
class DownloadView(LoginRequiredMixin, TemplateView):
	template_name = 'schedules/download.html'

	def get_context_data(self, *args, **kwargs):
		context = super(DownloadView, self).get_context_data(*args, **kwargs)
		try:
			active_schedule = Schedule.objects.get(active = True)
		except:
			active_schedule = None
		last_updated = Schedule.objects.latest('excel_updated')
		up_to_date = False
		from_current_schedule = False
		if active_schedule:
			from_current_schedule = (active_schedule == last_updated)
			up_to_date = (last_updated.updated_on < last_updated.excel_updated)
		latest_excel_deleted = cache.get('latest_excel_deleted')
		clean_excels = from_current_schedule and up_to_date and not latest_excel_deleted
		if clean_excels:
			clean_msg = f'Excel files are up to date.'
		elif latest_excel_deleted:
			last_updated = 'a deleted schedule.'
			clean_msg = f'Excel files match a deleted schedule, please update Excel files'
		elif from_current_schedule:
			clean_msg = f'These files are not up to date. Please update Excel files for {active_schedule}'
		elif up_to_date:
			clean_msg = f'Excel files match {last_updated} - not the current schedule ({active_schedule})'
		else:
			clean_msg = f'Files do not match {last_updated}. Please update the Excel files for {last_updated} or {active_schedule} before downloading'

		context['last_updated'] = last_updated
		context['clean_excels'] = clean_excels
		context['clean_msg'] = clean_msg
		return context

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
		context['percent_complete'] = schedule.get_percent_complete()
	except:
		context = {}
	task_id = cache.get('current_task_id')
	if task_id:
		template = 'schedules/progress.html'
		context['task_id'] = task_id
	context['at_build'] = True
	cache.delete('no_redirect')
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
		context['at_build'] = True
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
		context['at_build'] = True
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
		context['random'] = settings.break_ties_randomly()
		context['rank_based'] = settings.ranked_wins_break_ties()
		context['at_build'] = True
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
		cache.set('no_redirect', True, None)
	request.session['task_id'] = task_id
	context = {'task_id':task_id}
	context['schedule'] = schedule.title
	context['at_build'] = True
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
			cache.set('no_redirect', True, None)
			cache.set('latest_excel_deleted', False, None)
	else:
		template = 'schedules/progress.html'
		context['update_error_message'] = 'Please wait for the current task to complete.'

	request.session['task_id'] = task_id
	context['task_id'] = task_id
	context['schedule'] = schedule.title
	context['at_build'] = True
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
@csrf_exempt
def redirect(request, *args, **kwargs):
	RECOMMENDATION_REDIRECT = 1
	RATIO_REDIRECT = 2
	SPECIAL_SHIFT_REDIRECT = 3
	redirect_value = cache.get('redirect_value')
	print(f'Cached Value = {redirect_value}')
	recommendations_view = redirect_value == RECOMMENDATION_REDIRECT
	ratio_view = redirect_value == RATIO_REDIRECT
	special_results_view = redirect_value == SPECIAL_SHIFT_REDIRECT
	print(f'recommendations_view = {recommendations_view}')
	print(f'ratio_view = {ratio_view}')
	print(f'special_results_view = {special_results_view}')

	if not redirect_value:
		print('No redirect')
		return HttpResponseRedirect(reverse('schedules:schedule'))
	if recommendations_view:
		print('recommendations view')
		return HttpResponseRedirect(reverse('schedules:recommendation'))
	elif ratio_view:
		print('ratio view')
		return HttpResponseRedirect(reverse('schedules:ratio-week'))
	elif special_results_view:
		print('special shift view')
		return HttpResponseRedirect(reverse('schedules:special-results'))
	else:
		return Http404
		

@login_required
def recommendations_view(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active__exact = True)
		settings = ScheduleBuildingSettings.objects.get()
	except:
		return Http404

	recs = cache.get('recommendation')
	shift = cache.get('recommended_shift')
	cache.delete('recommendation')

	if not recs or not shift:
		print(f'No recommendations to be made (rec = {recs})')
		return HttpResponseRedirect(reverse('schedules:building'))

	template = 'schedules/recommendation.html'
	context = {}
	rows = []
	parameters = settings.parameters.all().order_by('rank')
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

@login_required
@csrf_exempt
def get_ratio(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active__exact = True)
	except:
		return render(request,'schedules/schedule.html', {'schedule_error_message':'Must select a schedule first.'})
	task_id = cache.get('current_task_id')
	if not task_id:
		schedule_id = schedule.id
		shift_set_id = schedule.shift_set.id
		task = find_ratios_task.delay(schedule_id, shift_set_id)
		task_id = task.task_id
		cache.set('current_task_id', task_id, 3000)
	request.session['task_id'] = task_id
	context = {'task_id':task_id}
	context['schedule'] = schedule.title
	context['at_build'] = True
	return HttpResponseRedirect(reverse('schedules:schedule'))

@login_required
def ratio_week_view(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active__exact = True)
	except:
		return Http404
	template = 'schedules/ratio_week.html'
	ratios = cache.get('ratios')
	if not ratios:
		print(f'No ratios (ratios = {ratios})')
		return HttpResponseRedirect(reverse('schedules:get-ratio'))
	all_rows_for_time = get_ratio_table(ratios)
	context = {}
	context['all_rows_for_time'] = all_rows_for_time
	context['shift_set'] = schedule.shift_set.title
	return render(request, template, context)

@login_required
def ratio_window_view(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active__exact = True)
		day = int(kwargs['d'])
		start = datetime.time(hour = int(kwargs['s'][:2]), minute = int(kwargs['s'][2:]))
		end = datetime.time(hour = int(kwargs['e'][:2]), minute = int(kwargs['e'][2:]))
	except:
		return Http404
	ratios = cache.get('ratios')
	if not ratios:
		return HttpResponseRedirect(reverse('schedules:get-ratio'))
	ratio_tables = get_ratio_tables_in_window(ratios, day, start, end)
	template = 'schedules/ratio_window.html'
	context = {}
	context['shift_set'] = schedule.shift_set.title
	context['day'] = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday'][day]
	context['start'] = get_readable_time(start)
	context['end'] = get_readable_time(end)
	context['ratio_tables'] = ratio_tables
	return render(request, template, context)


# Settings based views
class Settings(LoginRequiredMixin, TemplateView):
	template_name = 'settings.html'

	def get_context_data(self, *args, **kwargs):
		context = super(Settings, self).get_context_data(*args, **kwargs)
		context['at_settings'] = True
		return context

class FlagSettings(LoginRequiredMixin, TemplateView):
	template_name = 'settings_edit.html'
	
	def get_context_data(self, *args, **kwargs):
		context = super(FlagSettings, self).get_context_data(*args, **kwargs)
		context['list'] = Flag.objects.all().order_by(Lower('title'))
		context['delete_link'] = 'schedules:flag-delete'
		context['create_link'] = 'schedules:flag-create'
		context['object_name'] = 'Flag'
		context['at_settings'] = True
		return context

class QualificationSettings(LoginRequiredMixin, TemplateView):
	template_name = 'settings_edit.html'

	def get_context_data(self, *args, **kwargs):
		context = super(QualificationSettings, self).get_context_data(*args, **kwargs)
		context['list'] = Qualification.objects.all().order_by(Lower('title'))
		context['delete_link'] = 'schedules:qualification-delete'
		context['create_link'] = 'schedules:qualification-create'
		context['object_name'] = 'Qualification'
		context['at_settings'] = True
		return context

class ShiftSetList(LoginRequiredMixin, TemplateView):
	template_name = 'settings_edit.html'

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftSetList, self).get_context_data(*args, **kwargs)
		context['list'] = ShiftSet.objects.all().order_by(Lower('title'))
		context['shift_sets'] = True
		context['create_link'] = 'schedules:set-create'
		context['object_name'] = 'Shift Set'
		context['at_settings'] = True
		return context


# Stapher based views
class StapherList(LoginRequiredMixin,ListView):
	template_name = 'schedules/stapher_list.html'

	def get_queryset(self):
		try:
			schedule = Schedule.objects.get(active__exact = True)
			all_staphings = Staphing.objects.filter(schedule_id__exact = schedule.id)
		except:
			all_staphings = []
			schedule = None
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

					# Search by free staph by Day/Time
					days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
					day = None
					start = None
					end = None
					for i, d in enumerate(days):
						if d in query and not (day != None and start != None and end != None):
							query_cpy = query.replace(d,'').strip()
							day = i
							if '-' in query_cpy:
								start_str, end_str = query_cpy.split('-')
								start = get_time_from_string(start_str)
								end = get_time_from_string(end_str)
					free_during_time = [s for s in all_staphers if s.free_during_window(all_staphings, day, start, end)] if (day != None and start != None and end != None) else []
					explanation_str = f' are free on {query.capitalize()} on the \"{schedule}\" schedule,' if schedule else f' free on {query.capitalize()} (which is all staphers since no schedule is selected),'
					if free_during_time: query_explanation += explanation_str

					queryset = list(names_contain) + list(title_exact) + list(class_year_exact) + list(age_exact) + list(summers_exact) + free_during_time
				filtered_query_set = list(set(filtered_query_set) & set(queryset))

				# Used for the query_explanation
				if len(querylist) > 1 and query == querylist[-2].lower().strip():
					query_explanation = query_explanation[:-1] + ' and'
			cache.set('query_explanation', query_explanation[:-1], 60)
		else:
			cache.delete('query_explanation')

		return filtered_query_set

	def get_context_data(self, *args, **kwargs):
		context = super(StapherList, self).get_context_data(*args, **kwargs)
		context['title'] = 'Staphers'
		context['link'] = 'schedules:stapher-create'
		q_e = cache.get('query_explanation')
		context['query_explanation'] = q_e
		context['at_staph'] = True
		if q_e:
			context['new_tab'] = True
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
		context['at_staph'] = True
		return context

class StapherCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/form.html'
	form_class = StapherCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(StapherCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'New Stapher'
		context['cancel_url'] = 'schedules:stapher-list'
		context['qualification_label_name'] = 'stapher_qualifications_hardcoded'
		context['at_staph'] = True
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
		context['at_staph'] = True
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
	context['at_staph'] = True
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
		if form.is_valid():
			for shift in form.cleaned_data['added_shifts']:
				new_staphing = Staphing(stapher = stapher, schedule = schedule, shift = shift)
				new_staphing.save()
			return HttpResponseRedirect(reverse('schedules:stapher-schedule', kwargs={'pk': stapher.id}))
	else:
		form = AddShiftsForm()
	return stapher_schedule(request, args, kwargs, form)

@login_required
def stapher_cover(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	try:
		stapher = Stapher.objects.get(id__exact = stapher_id)
	except:
		return Http404
	try:
		schedule = Schedule.objects.get(active__exact = True)
		all_staphings = Staphing.objects.filter(schedule_id__exact = schedule.id)
	except:
		schedule = None
		all_staphings = []
	if schedule:
		schedule_msg = f'Covering {stapher.full_name()}\'s Shifts on "{schedule.title}"'
	else:
		schedule_msg = f'Unable to cover shifts for {stapher.full_name()}\'s schedule since no schedule is selected...'
	shifts_to_cover = {}
	days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
	if request.method == 'POST':
		form = WeekdayForm(request.POST)
		if form.is_valid():
			all_staphers_shifts = [s.shift for s in all_staphings.filter(stapher = stapher, schedule = schedule)]
			for day in form.cleaned_data['days']:
				day_str = days[int(day)]
				shifts_to_cover[day_str] = []
				for shift in sorted(all_staphers_shifts, key = attrgetter('start')):
					if shift.day == int(day) and not shift.is_unpaid():
						break_down = get_stapher_breakdown_table(shift, Stapher.objects.filter(active = True).exclude(id = stapher.id), all_staphings)
						qual_str = ''
						for qual in shift.qualifications.all():
							qual_str += qual.title + ','
						shift_obj = {}
						shift_obj['txt'] = f'{shift.title}, {get_readable_time(shift.start)}-{get_readable_time(shift.end)}, {len(break_down[3])} availible.'
						shift_obj['id'] = shift.id
						shift_obj['stapher_table'] = break_down
						shift_obj['search_link'] = f'{qual_str} {days[shift.day]} {shift.start.strftime("%I:%M%p")}-{shift.end.strftime("%I:%M%p")}'
						shifts_to_cover[day_str].append(shift_obj)
	else:
		form = WeekdayForm()
	template = 'schedules/stapher_cover.html'
	context = {}
	context['stapher'] = stapher
	context['schedule'] = schedule
	context['schedule_msg'] = schedule_msg 
	context['form'] = form
	context['days'] = days
	context['shifts_to_cover'] = shifts_to_cover
	context['at_staph'] = True
	return render(request, template, context)



# Shift based views
class ShiftList(LoginRequiredMixin, ListView):
	template_name = 'schedules/shift_list.html'

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
			query_existed = True
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
				elif query == 'none':
					queryset = [shift for shift in all_shifts if not shift.has_qualifications()]
					explanation_str = '- have at least one qualification' if negate_query else '- have no qualifications'
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
					time = get_time_from_string(query) 
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
			cache.delete('query_explanation')
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
		context['at_shifts'] = True
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
		context['new_tab'] = query_explanation or 'sort' in self.kwargs
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
			schedule = None
			schedule_title = 'No Schedule Selected.'
			staphings = []
		context['schedule_title'] = schedule_title
		working_shift = [s.stapher for s in staphings if s.shift == shift]
		context['working_shift'] = sorted(working_shift, key = attrgetter('first_name'))
		context['working_msg'] = str(len(working_shift))+ ' Workers Scheduled on :' if working_shift else 'No Workers Scheduled.'
		context['can_schedule_more'] = schedule and len(working_shift) < shift.workers_needed
		context['qualifications'] = sorted(shift.qualifications.all(), key = attrgetter('title'))
		context['flags'] = sorted(shift.flags.all(), key = attrgetter('title'))
		context['at_shifts'] = True
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
		context['at_shifts'] = True
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
		context['at_shifts'] = True
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

@login_required
def shift_schedule(request, *args, **kwargs):
	try:
		shift = Shift.objects.get(id = kwargs['pk'])
		schedule = Schedule.objects.get(active__exact = True)
		staphings = Staphing.objects.filter(schedule_id = schedule.id)
	except:
		return Http404
	template = 'schedules/shift_schedule.html'
	context = {}
	context['object'] = shift
	context['day'] = shift.get_day_string()
	context['time_msg'] = get_readable_time(shift.start) + '-' + get_readable_time(shift.end)
	worker_str = ' Workers Needed' if shift.workers_needed > 1 else ' Worker Needed'
	context['needed_msg'] = str(shift.workers_needed) + worker_str
	context['schedule_title'] = f'Schedule: {schedule.title}'
	working_shift = [s.stapher for s in staphings if s.shift == shift]
	context['working_shift'] = sorted(working_shift, key = attrgetter('first_name'))
	context['working_msg'] = str(len(working_shift))+ ' Workers Scheduled on :' if working_shift else 'No Workers Scheduled.'
	context['can_schedule_more'] = False
	context['qualifications'] = sorted(shift.qualifications.all(), key = attrgetter('title'))
	context['flags'] = sorted(shift.flags.all(), key = attrgetter('title'))
	context['at_shifts'] = True
	return render(request, template, context)


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
	return HttpResponseRedirect(reverse('schedules:schedule'))

class ScheduleCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/schedule_form.html'
	form_class = ScheduleCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'New Schedule'
		context['cancel_url'] = 'schedules:select'
		context['create'] = True
		context['at_build'] = True
		return context

class ScheduleList(LoginRequiredMixin, ListView):
	template_name = 'schedules/schedule_list.html'

	def get_queryset(self):
		return Schedule.objects.exclude(active__exact = True).order_by(Lower('title'))

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleList, self).get_context_data(*args, **kwargs)
		context['at_build'] = True
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
		context['at_build'] = True
		return context

class ScheduleDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = Schedule
	success_url = reverse_lazy('schedules:schedule')

	def get_context_data(self, *args, **kwargs):
		context = super(ScheduleDelete, self).get_context_data(*args, **kwargs)
		schedule = self.get_object()
		context['schedule_id'] = schedule.id
		context['at_build'] = True
		return context

class ScheduleUpdate(LoginRequiredMixin, UpdateView):
	template_name = 'schedules/schedule_form.html'
	form_class = ScheduleCreateForm

	def get_queryset(self):
		return Schedule.objects.all()

	def get_context_data(self, *args, **kwargs):
		schedule = self.get_object()
		context = super(ScheduleUpdate, self).get_context_data(*args, **kwargs)
		context['title'] = 'Edit Schedule'
		context['cancel_url'] = 'schedules:select'
		context['create'] = True
		context['shift_set_url'] = 'schedules:set-select-set'
		context['shift_set'] = schedule.shift_set
		context['at_build'] = True
		return context

@login_required
def schedule_duplicate_confirmation(request, *args, **kwargs):
	duplicate_id = kwargs['pk']
	try:
		schedule = Schedule.objects.get(active = True)
		duplicate_schedule = Schedule.objects.get(id__exact = duplicate_id)
	except:
		return Http404
	template = 'schedules/duplicate_confirmation.html'
	context = {}
	context['schedule'] = schedule
	context['duplicate_schedule'] = duplicate_schedule
	return render(request, template, context)

@login_required
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
		context['at_staph'] = True
		return context

	def get_success_url(self):
		staphing = self.get_object()
		return reverse_lazy('schedules:stapher-schedule', kwargs={'pk':staphing.stapher.id})



# Shift Set Based Views
class ShiftSetCreate(LoginRequiredMixin, CreateView):
	template_name = 'schedules/schedule_form.html'
	form_class = ShiftSetCreateForm

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftSetCreate, self).get_context_data(*args, **kwargs)
		context['title'] = 'New Shift Set'
		context['cancel_url'] = 'schedules:schedule-create'
		context['at_build'] = True
		return context

@login_required
def shift_set_add(request, *args, **kwargs):
	set_id = kwargs['pk']
	try:
		shift_set = ShiftSet.objects.get(id = set_id)
	except:
		return Http404
	other_shift_sets = ShiftSet.objects.exclude(id = shift_set.id).order_by('title')
	template = 'schedules/shift_set_list.html'
	context = {}
	context['shift_set'] = shift_set
	context['cancel_url'] = 'schedules:home'
	context['other_shift_sets'] = other_shift_sets
	context['at_build'] = True
	return render(request, template, context)

@login_required
def shift_set_add_from_set(request, *args, **kwargs):
	set_id = kwargs['pk']
	add_id = kwargs['add']
	if set_id == add_id:
		return Http404
	try:
		shift_set = ShiftSet.objects.get(id = set_id)
		adding_set = ShiftSet.objects.get(id = add_id)
	except:
		return Http404
	shifts_in_set = []
	uncheckable = []
	all_shifts = Shift.objects.filter(Q(shift_set=shift_set) | Q(shift_set=adding_set)).order_by('title','shift_set','day','start')
	shifts_arr = []
	shifts_in_set = []
	uncheckable = []
	for shift in all_shifts:
		flags = []
		for f in shift.flags.all():
			flags.append(f.id)
		arr = [shift.id, shift.shift_set.id, flags]
		shifts_arr.append(arr)
		if shift.shift_set == shift_set:
			shifts_in_set.append(shift)
			if Staphing.objects.filter(shift = shift):
				uncheckable.append(shift)
	if request.method == 'POST':
		form = AddShiftsToSetForm(request.POST)
		if form.is_valid():
			added_shifts = form.cleaned_data['added_shifts']
			added_shift_ids = []
			for shift in added_shifts:
				added_shift_ids.append(shift.id)
			shifts_in_set_ids = []
			add_shifts_to_set_task.delay(shift_set.id, added_shift_ids)
			return HttpResponseRedirect(reverse('schedules:schedule-create'))
	else:
		form = AddShiftsToSetForm()
	template = 'schedules/shift_set_form.html'
	context = {}
	context['shifts_arr'] = shifts_arr
	context['form'] = form
	context['shift_set'] = shift_set
	context['cancel_url'] = 'schedules:schedule-create'
	context['shift_sets'] = [adding_set]
	context['flags'] = Flag.objects.all().order_by('title')
	context['all_shifts'] = all_shifts
	context['shifts_in_set'] = shifts_in_set
	context['uncheckable'] = uncheckable
	context['at_build'] = True
	return render(request, template, context)

class ShiftSetDelete(LoginRequiredMixin, DeleteView):
	template_name = 'schedules/delete.html'
	model = ShiftSet
	success_url = reverse_lazy('schedules:schedule-create')

	def get_context_data(self, *args, **kwargs):
		context = super(ShiftSetDelete, self).get_context_data(*args, **kwargs)
		shift_set = self.get_object()
		schedules = [s for s in Schedule.objects.filter(shift_set = shift_set)]
		shifts = [s for s in Shift.objects.filter(shift_set = shift_set)]
		deleted_extras = schedules + shifts
		context['deleted_extras'] = deleted_extras
		return context




# Special Shift Placement Based Views
@login_required
def rank_staphers_view(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active = True)
	except:
		schedule = None
	template = 'schedules/rank.html'
	ordered_staphers = cache.get('ordered_staphers')
	if not ordered_staphers:
		ordered_staphers = Stapher.objects.filter(active = True).order_by('-summers_worked', 'class_year', '-age', 'first_name')
		cache.set('ordered_staphers', ordered_staphers, 1800)
	context = {}
	context['schedule'] = schedule
	context['ordered_staphers'] = ordered_staphers
	return render(request, template, context)


@login_required
def rank_staphers_swap_rank(request, swap_stapher, up):
	ordered_staphers = cache.get('ordered_staphers')
	if not ordered_staphers:
		ordered_staphers = Stapher.objects.filter(active = True).order_by('-summers_worked', 'class_year', '-age', 'first_name')
		cache.set('ordered_staphers', ordered_staphers, 1800)
	index = -1
	ordered_staphers = list(ordered_staphers)
	for i, stapher in enumerate(ordered_staphers):
		if swap_stapher == stapher:
			index = i
			break
	if index >= 0 and up:
		new_index = index - 1
	elif index >= 0 and not up:
		new_index = index + 1
	else:
		new_index = -1
	if new_index in range(0, len(ordered_staphers)):
		ordered_staphers.remove(swap_stapher)
		ordered_staphers.insert(new_index, swap_stapher)
	cache.set('ordered_staphers', ordered_staphers, 1800)
	return HttpResponseRedirect(reverse('schedules:special'))

@login_required
def rank_staphers_up(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	try:
		stapher = Stapher.objects.get(id = stapher_id)
	except:
		return Http404
	return rank_staphers_swap_rank(request, stapher, True)

@login_required
def rank_staphers_down(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	try:
		stapher = Stapher.objects.get(id = stapher_id)
	except:
		return Http404
	return rank_staphers_swap_rank(request, stapher, False)

@login_required
def stapher_preferences(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	try:
		stapher = Stapher.objects.get(id = stapher_id)
	except:
		return Http404

	special_shift_flags = cache.get('special_shift_flags')
	if not special_shift_flags:
		special_shift_flags = get_special_shift_flags()
		cache.set('special_shift_flags', special_shift_flags, None)
	staphers_preferences = ShiftPreference.objects.filter(stapher = stapher).order_by('ranking')
	preferenced_flags = [p.flag for p in staphers_preferences]
	flags_to_add = [f for f in special_shift_flags if f not in preferenced_flags]
	template = 'schedules/stapher_preferences.html'
	context = {}
	context['stapher'] = stapher
	context['flags_to_add'] = flags_to_add
	context['staphers_preferences'] = staphers_preferences
	return render(request, template, context)

@login_required
def stapher_preferences_add(request, *args, **kwargs):
	stapher_id = kwargs['pk']
	flag_id = kwargs['f']
	try:
		stapher = Stapher.objects.get(id = stapher_id)
		flag = Flag.objects.get(id = flag_id)
		all_preferences = list(ShiftPreference.objects.all().order_by('-ranking'))
		if all_preferences:
			ranking = all_preferences[0].ranking + 1
		else:
			ranking = 1
	except:
		return Http404
	new_preference = ShiftPreference(stapher = stapher, flag = flag, ranking = ranking)
	new_preference.save()
	return HttpResponseRedirect(reverse('schedules:stapher-preferences', kwargs={'pk': stapher.id}))

@login_required
def stapher_preferences_delete(request, *args, **kwargs):
	pref_id = kwargs['pk']
	try:
		preference = ShiftPreference.objects.get(id = pref_id)
	except:
		return Http404
	stapher = preference.stapher
	preference.delete()
	return HttpResponseRedirect(reverse('schedules:stapher-preferences', kwargs={'pk': stapher.id}))

@login_required
def stapher_preferences_up(request, *args, **kwargs):
	pref_id = kwargs['pk']
	try:
		preference = ShiftPreference.objects.get(id = pref_id)
		other_preferences = ShiftPreference.objects.filter(stapher = preference.stapher).order_by('ranking')
	except:
		return Http404
	swap_shift_preferences(preference, other_preferences, True)
	return HttpResponseRedirect(reverse('schedules:stapher-preferences', kwargs={'pk': preference.stapher.id}))

@login_required
def stapher_preferences_down(request, *args, **kwargs):
	pref_id = kwargs['pk']
	try:
		preference = ShiftPreference.objects.get(id = pref_id)
		other_preferences = ShiftPreference.objects.filter(stapher = preference.stapher).order_by('ranking')
	except:
		return Http404
	swap_shift_preferences(preference, other_preferences, False)
	return HttpResponseRedirect(reverse('schedules:stapher-preferences', kwargs={'pk': preference.stapher.id}))

@login_required
def place_special_shifts(request, *args, **kwargs):
	try:
		schedule = Schedule.objects.get(active__exact = True)
	except:
		return render(request,'schedules/rank.html', {})
	if not cache.get('ordered_staphers'):
		return HttpResponseRedirect(reverse('schedules:special'))
	task_id = cache.get('current_task_id')
	if not task_id:
		task = place_special_shifts_task.delay(schedule.id)
		task_id = task.task_id
		cache.set('current_task_id', task_id, 3000)
		cache.delete('no_redirect')
	request.session['task_id'] = task_id
	context = {'task_id':task_id}
	context['schedule'] = schedule.title
	context['at_build'] = True
	return HttpResponseRedirect(reverse('schedules:schedule'))

@login_required
def special_shifts_results(request, *args, **kwargs):
	special_shift_results = cache.get('special_shift_results')
	if not special_shift_results:
		return HttpResponseRedirect(reverse('schedules:schedule'))
	else:
		ordered_staphers = special_shift_results[0]
		results_dict = special_shift_results[1]
		context = {}
		template = 'schedules/special_shift_results.html'
		html_arr = []
		for stapher in ordered_staphers:
			html_obj = {}
			html_obj['name'] = stapher.full_name()
			html_obj['results'] = results_dict[stapher.id]
			html_arr.append(html_obj)
		context['ordered_staphers'] = html_arr
	return render(request, template, context)









