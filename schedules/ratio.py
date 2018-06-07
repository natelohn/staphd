
def get_solution_for_time(shifts, staphers, day, start, end):
	shifts.filter(day = day, start__lt = end, end__gt = start).order_by('workers_needed')
	for shift in shifts:
		print(shift)