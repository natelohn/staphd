import datetime

from .sort import get_ordered_start_and_end_times_by_day

def get_solution(shifts, staphers, staphings):
	if not shifts:
		return True
	for shift in shifts:
		for stapher in staphers:
			if stapher.can_cover(shift, staphings):
				shifts_cpy = shifts[:]
				staphers_cpy = staphers[:]
				shifts_cpy.remove(shift)
				staphers_cpy.remove(stapher)
				return get_solution(shifts_cpy, staphers_cpy, staphings)
			return get_solution(shifts[:], staphers[:], staphings)
	return False



def find_ratios(shifts, staphers, staphings):
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	for day in ordered_times_by_day:
		for i in range(1, len(ordered_times_by_day[day])):
			start = ordered_times_by_day[day][i - 1]
			end = ordered_times_by_day[day][i]
			shifts_in_window = shifts.filter(day = day, start__lt = end, end__gt = start).order_by('workers_needed')
			solution = get_solution(shifts_in_window[:], list(staphers), staphings)
			print(f'------------- solution = {solution} ----------------')
		return

