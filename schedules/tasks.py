from __future__ import absolute_import, unicode_literals
from celery import shared_task
from celery.decorators import task
from django.core.cache import cache
from django.db.models.functions import Lower

from .build import build_schedules
from .excel import update_individual_excel_files, update_masters, update_analytics
from .models import Flag, Stapher, Shift, Staphing, Qualification, Master
from .models import Settings as ScheduleBuildingSettings
from .sort import get_sorted_shifts



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
	num_total_actions = (len(all_staphers) * 2) + ((len(all_masters) * 2) - 3) + 3
	cache.set('num_actions_made', 0, 1500)
	cache.set('num_total_actions', num_total_actions, 1500)

	# Do the task
	xl_dir = '/app/static/xlsx/'
	update_individual_excel_files(all_staphers, staphings, xl_dir, self)
	update_masters(all_masters, staphings, xl_dir, self)
	update_analytics(all_staphers, staphings, all_flags, all_qualifications, xl_dir, self)

	# Delete the amount of actions from the cache
	cache.set('num_actions_made', None, 0)
	cache.set('num_total_actions', None, 0)
	cache.set('current_task_id', None, 0)


@task(bind=True, track_started=True, task_time_limit = 1500)
@shared_task(bind=True, ignore_result=False)
def build_schedules_task(self, schedule_id):
	try:
		staphings = Staphing.objects.get(schedule_id__exact = schedule_id)
	except:
		staphings = []
	settings = ScheduleBuildingSettings.objects.get()
	sorted_shifts = cache.get('sorted_shifts')
	if cache.get('resort') or not sorted_shifts:
		# Set the message for the front end
		self.update_state(meta = {'message':'Preparing to Place Shifts', 'process_percent':0})
		all_shifts = Shift.objects.all()
		all_staphers = Stapher.objects.all()
		sorted_shifts = get_sorted_shifts(all_staphers, all_shifts)
		cache.set('sorted_shifts', sorted_shifts, None)
		cache.set('resort', False, None)
	
	total_actions = sum([shift.workers_needed for shift, staphers in sorted_shifts])

	# Do the task
	build_schedules(sorted_shifts, settings, schedule, staphings, self)

	# Delete the values needed to track progress
	cache.set('num_actions_made', None, 0)
	cache.set('num_total_actions', None, 0)
	cache.set('current_task_id', None, 0)
	

