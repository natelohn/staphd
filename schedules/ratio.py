import datetime

from .sort import get_ordered_start_and_end_times_by_day, get_qual_and_shifts_dicts, get_stapher_dict

from .models import Shift, Stapher, Staphing

def get_ratios_in_window(shifts, staphers, staphings):
	busy_staphers = [s.stapher.id for s in staphings]
	shift_and_qual_dicts = get_qual_and_shifts_dicts(shifts)
	shift_dict = shift_and_qual_dicts[1]
	stapher_dict = get_stapher_dict(staphers, shift_and_qual_dicts[0])
	all_ratios = []
	for q_set in shift_dict.keys():
		sum_needed = sum([s.workers_needed for s in shift_dict[q_set]])
		availible_workers = [s for s in stapher_dict[q_set] if s.id not in busy_staphers]
		all_ratios.append([sum_needed, availible_workers])
	return all_ratios


def find_ratios(schedule_id, shift_set_id):
	print('P')
	shifts = Shift.objects.filter(shift_set_id = shift_set_id)
	print('O')
	staphers = Stapher.objects.all()
	print('N')
	staphings = Staphing.objects.filter(schedule_id = schedule_id)
	print('M')
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	print('L')
	all_window_info = []
	print('K')
	for day in ordered_times_by_day:
		print('J')
		for i in range(1, len(ordered_times_by_day[day])):
			print('I')
			start = ordered_times_by_day[day][i - 1]
			print('H')
			end = ordered_times_by_day[day][i]
			print('G')
			shifts_in_window = shifts.filter(day = day, start__lt = end, end__gt = start).order_by('workers_needed')
			print('F')
			staphings_in_window = staphings.filter(shift_day = day, shift_start__lt = end, shift_end__gt = start)
			print('E')
			ratios_in_window = get_ratios_in_window(shifts_in_window, staphers, staphings_in_window)
			print('D')
			time_info = [day, start, end]
			print('C')
			window_info = [time_info, ratios_in_window]
			print('B')
			all_window_info.append(window_info)
			print('A')
	return all_window_info
