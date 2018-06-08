import datetime

from .sort import get_ordered_start_and_end_times_by_day

def get_solution(shifts, staphers, free_and_qualified):
	for shift in shifts:
		print(f'{shift} - {shift.workers_needed} / {free_and_qualified[shift.id]}')



def find_ratios(shifts, staphers, staphings):
	ordered_times_by_day = get_ordered_start_and_end_times_by_day(shifts)
	for day in ordered_times_by_day:
		print(f'{day}')
		for time in ordered_times_by_day[day]:
			print(f'	- {time}')