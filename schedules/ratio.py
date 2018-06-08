import datetime

from .sort import get_ordered_start_and_end_times_by_day, get_qual_and_shifts_dicts, get_stapher_dict

def get_solution(day, start, end, shift_dict, stapher_dict):
	print(f'{day}')
	for key in shift_dict:
		print(f'{key}')
		shifts_in_window = [s for s in shift_dict[key] if s.is_in_window(day, start, end)]
		print(f'{key}')
		eligible_staphers = [s for s in stapher_dict[key] if s.is_free_during_window(day, start, end)]
		print(f'{key}')
		for shift in shifts_in_window:
			print(f'{shift} - {shift.workers_needed} / {len(eligible_staphers)}')



def find_ratios(shifts, staphers, staphings):
	shift_and_qual_dicts = get_qual_and_shifts_dicts(shifts)
	shift_dict = shift_and_qual_dicts[1]
	stapher_dict = get_stapher_dict(staphers, shift_and_qual_dicts[0])
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	for day in ordered_times_by_day:
		for i in range(1, len(ordered_times_by_day[day])):
			start = ordered_times_by_day[day][i - 1]
			end = ordered_times_by_day[day][i]
			get_solution(day, start, end, shift_dict, stapher_dict)
