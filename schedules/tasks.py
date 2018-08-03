from __future__ import absolute_import, unicode_literals
from celery import shared_task
from celery.decorators import task
from django.core.cache import cache
from django.db.models.functions import Lower
from django.utils import timezone

from .build import build_schedules
from .excel import update_individual_excel_files, update_masters, update_analytics
from .models import Flag, Schedule, Stapher, Shift, ShiftSet, Staphing, Qualification, Master
from .models import Settings as ScheduleBuildingSettings
from .ratio import find_ratios
from .sort import get_sorted_shifts, get_ordered_start_and_end_times_by_day
from .special_shifts import place_special_shifts_by_rank



@task(bind=True, track_started=True, task_time_limit = 1500)
@shared_task(bind=True, ignore_result=False)
def update_files_task(self, schedule_id):
	# Get necessary information from the DB
	staphings = Staphing.objects.filter(schedule__id = schedule_id)
	all_masters = Master.objects.all()
	all_staphers = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))
	all_flags = Flag.objects.all().order_by(Lower('title'))
	all_qualifications = Qualification.objects.all().order_by(Lower('title'))

	# Set the amount of actions for the task to recieve later to use for percentage
	# TODO: Dynamically get num_total_actions (?)
	num_total_actions = (len(all_staphers) * 2) + ((len(all_masters) * 2) - 3) + 9
	cache.set('num_actions_made', 0, 1500)
	cache.set('num_total_actions', num_total_actions, 1500)

	# Do the task
	xl_dir = '/app/static/xlsx/'
	update_individual_excel_files(all_staphers, staphings, xl_dir, self)
	update_masters(all_masters, staphings, xl_dir, self)
	update_analytics(all_staphers, staphings, all_flags, all_qualifications, xl_dir, self)

	#Update the Schedule's 'excel_updated' field
	schedule = Schedule.objects.get(id = schedule_id)
	schedule.excel_updated = timezone.now()

	# Delete the amount of actions from the cache
	cache.delete('num_actions_made')
	cache.delete('num_total_actions')
	cache.delete('current_task_id')


@task(bind=True, track_started=True, task_time_limit = 1500)
@shared_task(bind=True, ignore_result=False)
def build_schedules_task(self, schedule_id):
	try:
		schedule = Schedule.objects.get(id__exact = schedule_id)
		settings = ScheduleBuildingSettings.objects.get()
	except:
		return None
	try:
		staphings = list(Staphing.objects.filter(schedule_id = schedule.id))
	except:
		staphings = []
	sorted_shifts = cache.get('sorted_shifts')
	if not sorted_shifts:
		# Set the message for the front end
		self.update_state(meta = {'message':'Preparing to Place Shifts', 'process_percent':0})
		shifts_in_set = Shift.objects.filter(shift_set = schedule.shift_set)
		active_staphers = Stapher.objects.filter(active = True)
		sorted_shifts = get_sorted_shifts(active_staphers, shifts_in_set)
		cache.set('sorted_shifts', sorted_shifts, None)
	total_actions = sum([shift.workers_needed for shift, staphers in sorted_shifts])
	cache.set('num_total_actions', total_actions, 1500)

	# Do the task
	shift_and_rec = build_schedules(sorted_shifts, settings, schedule, staphings, self)
	if not shift_and_rec: #Schedule Building is done! (no more recs to be made)
		self.update_state(meta = {'message':'All possible shifts placements made.', 'process_percent':100})
		cache.set('recommendation', False, None)
	else:
		recommended_shift = shift_and_rec[0]
		recommendation = shift_and_rec[1]
		cache.set('recommended_shift',recommended_shift, None)
		cache.set('recommendation',recommendation, None)

	# Delete the values needed to track progress
	cache.delete('num_actions_made')
	cache.delete('num_total_actions')
	cache.delete('current_task_id')

@task(bind=True, track_started=True, task_time_limit = 1500)
@shared_task(bind=True, ignore_result=False)
def find_ratios_task(self, schedule_id, shift_set_id):
	shifts = Shift.objects.filter(shift_set_id = shift_set_id)
	staphers = Stapher.objects.filter(active = True)
	staphings = Staphing.objects.filter(schedule_id = schedule_id)
	uncovered_shifts = [s for s in shifts if not s.is_covered(staphings)]
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(uncovered_shifts)

	# Set the amount of actions for the task to recieve later to use for percentage
	total_actions = sum([len(ordered_times_by_day[d]) for d in ordered_times_by_day])
	cache.set('num_total_actions', total_actions, None)

	# Do the task
	ratios = find_ratios(shifts, staphers, staphings, ordered_times_by_day, self)
	cache.delete('special_shift_results')
	cache.set('ratios', ratios, None)
	

	# Delete the values needed to track progress
	cache.delete('num_actions_made')
	cache.delete('num_total_actions')
	cache.delete('current_task_id')


@task(bind=True, track_started=True, task_time_limit = 1500)
@shared_task(bind=True, ignore_result=False)
def place_special_shifts_task(self, schedule_id):
	try:
		schedule = Schedule.objects.get(id = schedule_id)
		special_flag = Flag.objects.get(title__iexact = 'special')
		special_shifts = Shift.objects.filter(shift_set = schedule.shift_set, flags__in = [special_flag])
		staphings = Staphing.objects.filter(schedule = schedule)
	except:
		return None
	ordered_staphers = cache.get('ordered_staphers') # Made sure it exists in views.py
	special_shift_results = place_special_shifts_by_rank(schedule, list(ordered_staphers), special_shifts, list(staphings), self)
	

	cache.delete('ratios')
	cache.set('special_shift_results', special_shift_results, None)
	cache.delete('current_task_id')

@task(bind=True, track_started=True, task_time_limit = 1500)
@shared_task(bind=True, ignore_result=False)
def add_shifts_to_set_task(self, shift_set_id, added_shift_ids):
	shift_set = ShiftSet.objects.get(id = shift_set_id)
	shifts_in_set = Shift.objects.filter(shift_set = shift_set)
	for shift_id in added_shift_ids:
		shift = Shift.objects.get(id = shift_id)
		if shift not in shifts_in_set:
			new_shift = Shift(title = shift.title, day = shift.day, start = shift.start, end = shift.end, workers_needed = shift.workers_needed, shift_set = shift_set)
			new_shift.save()
			new_shift.flags = shift.flags.all()
			new_shift.qualifications = shift.qualifications.all()
			new_shift.save()
			print(f'Saved -> {new_shift}')
	for shift in shifts_in_set:
		if shift.id not in added_shifts_ids:
			shift.delete()
			print(f'Deleted -> {shift}')

