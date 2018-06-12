import datetime

from django.core.cache import cache
from operator import attrgetter

from .excel import get_percent
from .sort import get_qual_and_shifts_dicts, get_stapher_dict

from .models import Shift, Stapher, Staphing

def get_ratios_info_in_window(shifts, staphers, workers_left, busy_staphers):
	shift_and_qual_dicts = get_qual_and_shifts_dicts(shifts)
	shift_dict = shift_and_qual_dicts[1]
	stapher_dict = get_stapher_dict(staphers, shift_and_qual_dicts[0])
	all_ratios = []
	for q_set in shift_dict.keys():
		sum_needed = sum([workers_left[s.id] for s in shift_dict[q_set]])
		availible_workers = []
		not_free_workers = []
		not_qualified_workers = []
		not_free_or_qualified_workers = []
		for s in sorted(staphers, key = attrgetter('first_name', 'last_name')):
			if s in stapher_dict[q_set]:
				if s.id not in busy_staphers:
					availible_workers.append(s)
				else:
					not_free_workers.append(s)
			else:
				if s.id not in busy_staphers:
					not_qualified_workers.append(s)
				else:
					not_free_or_qualified_workers.append(s)

		ratios = [sum_needed, len(availible_workers)]
		shifts_in_q_set = shift_dict[q_set][0]
		q_strings = [q.title for q in shifts_in_q_set.qualifications.all()]
		stapher_info = [not_free_or_qualified_workers, not_qualified_workers, not_free_workers, availible_workers]
		all_ratios.append([ratios, q_strings, stapher_info])
	return all_ratios


def find_ratios(shifts, staphers, staphings, all_ordered_times, current_task):
	total_actions = cache.get('num_total_actions') or 70
	meta = {'message':'Retrieving Information for Ratios', 'process_percent':0}
	current_task.update_state(meta = meta)
	days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

	workers_left = {}
	for shift in shifts:
		workers_left[shift.id] = shift.left_to_cover(staphings)
	windows_by_day = {}
	actions_taken = 0
	for day in all_ordered_times:
		windows_by_day[day] = []
		for i in range(1, len(all_ordered_times[day])):
			start = all_ordered_times[day][i - 1]
			end = all_ordered_times[day][i]

			actions_taken += 1
			percent = get_percent(actions_taken, total_actions)
			meta = {'message':f'Geting Ratio for {days[day]}, {start}-{end}', 'process_percent':percent}
			current_task.update_state(meta = meta)
			
			shifts_in_window = [s for s in shifts.filter(day = day, start__lt = end, end__gt = start) if workers_left[s.id] > 0]
			if len(shifts_in_window) > 0:
				busy_staphers = [s.stapher.id for s in staphings.filter(shift__day = day, shift__start__lt = end, shift__end__gt = start)]
				ratios_info_in_window = get_ratios_info_in_window(shifts_in_window, staphers, workers_left, busy_staphers)
				time_info = [start, end]
				window_info = [time_info, ratios_info_in_window]
				windows_by_day[day].append(window_info)
	return windows_by_day