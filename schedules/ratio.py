
def get_solution_for_time(shifts, staphers, day, time):
	shifts.filter(day__exact = time, start__lte = end, end__gt = time).order_by('workers_needed')
	for shift in shifts:
		print(shift)