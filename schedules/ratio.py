import datetime


def get_solution(shifts, staphers):
	for shift in shifts:
		print(f'{shift} - {shift.workers_needed}')



def find_ratios(shifts, staphers):
	shifts.order_by('workers_needed')
	day = 0
	start = datetime.time(11, 0, 0, 0)
	end = datetime.time(11, 15, 0, 0)
	shifts_in_window = [s for s in shifts if s.is_in_window(day, start, end)]
	get_solution(shifts_in_window, staphers)