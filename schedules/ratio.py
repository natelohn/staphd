import datetime

from .sort import get_ordered_start_and_end_times_by_day, get_qual_and_shifts_dicts, get_stapher_dict

def get_solution(staphings, day, start, end,shift_dict, stapher_dict):
	for key in shift_dict:
		shifts_in_window = []
		print(f'pre-loop shifts: {shifts_in_window}')
		for s in shift_dict[key]:
			print(s)
			if s.is_in_window(day, start, end):
				shifts_in_window.append(s)
				print(f'mid-loop shifts: {shifts_in_window}')
		print(f'post-loop shifts: {shifts_in_window}')
		if shifts_in_window:
			eligible_staphers = []
			print(f'pre-loop staphers: {eligible_staphers}')
			for s in stapher_dict[key]:
				print(s)
				print(staphings)
				print(day)
				print(start)
				print(end)
				print(s.is_free_during_window(staphings, day, start, end))
				print(f'mid-loop staphers: {eligible_staphers}')
				if s.is_free_during_window(staphings, day, start, end):
					eligible_staphers.append(s)
					print(f'edited staphers: {eligible_staphers}')
			print(eligible_staphers)
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
			get_solution(staphings, day, start, end, shift_dict, stapher_dict)
