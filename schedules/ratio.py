
def get_solution_for_time(shifts, staphers, day, time):
	shifts.filter(day__exact = day, start__lte = time, end__gt = time).order_by('workers_needed')
	for shift in shifts:
		print(shift)