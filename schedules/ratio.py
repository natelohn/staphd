import datetime


def get_solution(shifts, staphers):
	for shift in shifts:
		print(f'{shift} - {shift.workers_needed}')



def find_ratios(shifts, staphers, staphings):
	free_and_qualified = {}
	for shift in shifts_in_window:
		free_and_qualified[shift.id] = []
		for stapher in staphers:
			if stapher.can_cover(shift, staphings)
	shifts.order_by('workers_needed')
	day = 0
	start = datetime.time(11, 0, 0, 0)
	end = datetime.time(11, 15, 0, 0)
	shifts_in_window = [s for s in shifts if s.is_in_window(day, start, end)]
	get_solution(shifts_in_window, staphers)