from __future__ import absolute_import
from celery import shared_task, current_task
from django.core.cache import cache
from django.db.models.functions import Lower
from staphd.celery import app
import time

from .build import build_schedules
from .excel import update_individual_excel_files, update_masters, update_analytics
from .models import Flag, Stapher, Shift, Staphing, Qualification, Master
from .models import Settings as ScheduleSettings
from .sort import get_sorted_shifts


@app.task(bind=True, track_started=True)
@shared_task(bind=True)
def update_files_task(self, schedule_id):
	# Get necessary information from the DB
	staphings = Staphing.objects.filter(schedule__id = schedule_id)
	all_masters = Master.objects.all()
	all_staphers = Stapher.objects.all().order_by(Lower('first_name'), Lower('last_name'))
	all_flags = Flag.objects.all().order_by(Lower('title'))
	all_qualifications = Qualification.objects.all().order_by(Lower('title'))

	# Set the amount of actions for the task to recieve later to use for percentage
	num_total_actions = (len(all_staphers) * 2) + ((len(all_masters) * 2) - 3) + 3
	cache.set('num_actions_made', 0, None)
	cache.set('num_total_actions', num_total_actions, None)

	# Do the task
	update_individual_excel_files(all_staphers, staphings)
	update_masters(all_masters, staphings)
	update_analytics(all_staphers, staphings, all_flags, all_qualifications)

	# Delete the amount of actions from the cache
	cache.set('num_actions_made', None, 0)
	cache.set('num_total_actions', None, 0)
	cache.set('current_task_id', None, 0)


@app.task(bind=True, track_started=True)
@shared_task(bind=True)
def build_schedules_task(self):
	sorted_shifts = cache.get('sorted_shifts')
	if cache.get('resort') or not sorted_shifts:
		# Set the message for the front end
		current_task.update_state(meta = {'message':'Preparing to Place Shifts', 'process_percent':0})
		# Get the necessary info from the DB
		all_shifts = Shift.objects.all()
		all_staphers = Stapher.objects.all()
		sorted_shifts = get_sorted_shifts(all_staphers, all_shifts)
		cache.set('sorted_shifts', sorted_shifts, None)
		cache.set('resort', False, None)

	total_actions = sum([shift.workers_needed for shift, staphers in sorted_shifts])


	# Get the necessary info from the DB
	settings = ScheduleSettings.objects.get()

	# Do the task
	schedule = build_schedules(sorted_shifts, settings)
	cache.set('schedule_id', schedule.id, None)

	# Delete the values needed to track progress
	cache.set('num_total_actions', None, 0)
	cache.set('current_task_id', None, 0)

	
	




