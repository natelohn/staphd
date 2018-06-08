import datetime

from .sort import get_ordered_start_and_end_times_by_day

def get_solution(shifts, staphers, staphings):
	print(f'Shifts = {shifts}')
	print(f'Staphers = {shifts}')
	if not shifts:
		return True
	for shift in shifts:
		for stapher in staphers:
			if stapher.can_cover(shift, staphings):
				shifts.remove(shift)
				staphers.remove(stapher)
				print('------------------')
				return get_solution(shifts[:], staphers[:], staphings)
	return False



def find_ratios(shifts, staphers, staphings):
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	for day in ordered_times_by_day:
		for i in range(1, len(ordered_times_by_day[day])):
			start = ordered_times_by_day[day][i - 1]
			end = ordered_times_by_day[day][i]
			shifts_in_window = shifts.filter(day = day, start__lt = end, end__gt = start).order_by('workers_needed')
			for shift in shifts_in_window:
				print(f'{shift} - {shift.workers_needed}')
			solution = get_solution(shifts_in_window[:], staphers[:], staphings)
			print(f'------------- solution = {solution} ----------------')

