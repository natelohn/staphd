import datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.db.models import Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView

from .build import build_schedules
from .forms import FlagCreateForm, ShiftCreateForm, StapherCreateForm, QualificationCreateForm
from .models import Flag, Schedule, Shift, Stapher, Staphing, Qualification
from .models import Settings as ScheduleSettings
from .sort import get_sorted_shifts
from .excel import update_individual_excel_files



class Home(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class BuildView(LoginRequiredMixin, TemplateView):
    template_name = 'schedules/build.html'
 
@login_required
def building_schedules(request):
	################ For testing...  ################
	start_time = datetime.datetime.now()
	Schedule.objects.all().delete()
	Staphing.objects.all().delete()
	# settings = ScheduleSettings.objects.get()
	# parameters = settings.parameters.filter(use = True).order_by('rank')
	# print(f'{len(parameters)} parameters used:')
	# for p in parameters:
	# 	print(f'	{p}')
	#################################################

	sorted_shifts = cache.get('sorted_shifts')
	if cache.get('resort') or not sorted_shifts:
		all_shifts = Shift.objects.all()
		all_staphers = Stapher.objects.all()
		sorted_shifts = get_sorted_shifts(all_staphers, all_shifts)
		cache.set('sorted_shifts', sorted_shifts, None)
		cache.set('resort', False, None)

	settings = ScheduleSettings.objects.get()
	schedule = build_schedules(sorted_shifts, settings)
	cache.set('schedule_id', schedule.id, None)

	############### For testing...  ################
	# staphings = Staphing.objects.filter(schedule__id = schedule.id)
	# uncovered_shifts = []
	# uncovered_staphings = 0
	# staphings_made = len(staphings)
	# total_shifts = len(sorted_shifts)

	# for info in sorted_shifts:
	# 	shift = info[0]
	# 	if not shift.is_covered(staphings):
	# 		uncovered_shifts.append(shift)
	# 		uncovered_staphings += shift.left_to_cover(staphings)
	# print(f'-------------------------\n{100 * round((1 - (len(uncovered_shifts) / total_shifts)), 4)}% of shifts covered.')
	# print(f'{100 * round(1 - (uncovered_staphings / (uncovered_staphings + staphings_made)), 4)}% of staphings made.\n-------------------------')
	# print(f'Uncovered Shifts:')
	# for shift in uncovered_shifts:
	# 	print(f'	{shift.left_to_cover(staphings)} still needed for {shift}.')
	# end_time = datetime.datetime.now()

	# print(f'====================================================\nTime Elapsed Building: {end_time - start_time}\n====================================================')
	# schedule.print()
	# print('=================================================')
	# if settings.ranked_wins_break_ties():
	# 	print(f'Resolving ties by Rank.')
	# elif settings.break_ties_randomly():
	# 	print(f'Resolving Ties Randomly.')
	# parameters = settings.parameters.filter(use = True).order_by('rank')
	# print(f'{len(parameters)} parameters used:')
	# for p in parameters:
	# 	print(f'	{p}')
	################################################
	return HttpResponseRedirect(reverse('schedules:build'))

 
@login_required
def updating_files(request):
	################ For testing...  ################
	start_time = datetime.datetime.now()
	#################################################
	schedule_id = cache.get('schedule_id')
	if schedule_id:
		staphings = Staphing.objects.filter(schedule__id = schedule_id)
		all_staphers = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))
		update_individual_excel_files(all_staphers, staphings)
	else:
		print('NO SCHEDULE U DUM FUK :(')
		exit()
	############### For testing...  ################
	print(f'==========================\nTime Elapsed Updating: {datetime.datetime.now() - start_time}\n==========================')
	################################################
	return HttpResponseRedirect(reverse('schedules:build'))

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
		return queryset.order_by('day','start')
		

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
