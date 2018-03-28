import datetime
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Alignment, Color, PatternFill, Border, Side, Font
from operator import attrgetter, itemgetter

from .analytics import get_analytics


def create_new_workbook(staphers):
	# Copy the template workbook.
	print('Creating schedules.xlsx file...')
	template_wb = load_workbook('../output/template.xlsx')
	template_wb.save("../output/schedules.xlsx")
	schedule_wb = load_workbook('../output/schedules.xlsx')
	template_ws = schedule_wb['TEMPLATE']
	for stapher in staphers:
		print(f'Making excel worksheet for {stapher.full_name()}...')

		# We copy the template worksheet for each Stapher.
		stapher_ws = schedule_wb.copy_worksheet(template_ws)
		stapher_ws.title = stapher.full_name()
	schedule_wb.remove(template_ws)
	schedule_wb.save("../output/schedules.xlsx")
	return '../output/schedules.xlsx'


def get_row_from_day(day):
	return 5 + (day * 4)

def get_start_col_from_time(time):
	return 3 + ((time.hour - 6) * 4) + int((time.minute / 60) * 4)

def get_end_col_from_time(time):
	return get_start_col_from_time(time) - 1

# This function takes in a list of staphers and staphings and makes a readable xl file for each stapher.
def update_individual_excel_files(staphers, staphings):
	wb_str = create_new_workbook(staphers)

	schedule_wb = load_workbook("../output/schedules.xlsx")

	seconds_in_hour = 60 * 60

	for stapher in staphers:
		print(f'Populating excel worksheet for {stapher.full_name()}...')
		stapher_ws = schedule_wb[stapher.full_name()]
		stapher_ws['A1'] = 'Name: ' + stapher.full_name()
		stapher_ws['AE1'] = 'Postion: ' + stapher.title
		shifts = stapher.ordered_shifts(staphings)
		for shift in shifts:
			print(f'	{shift}')
			row = get_row_from_day(shift.day)
			start_col = get_start_col_from_time(shift.start)
			end_col = get_end_col_from_time(shift.end)
			cell = stapher_ws.cell(row = row, column = start_col)
			cell.alignment = Alignment(shrinkToFit = True, wrapText = True, horizontal = 'center', vertical = 'center')
			cell.border = Border(left = Side(style = 'thin'), right = Side(style = 'thin'), top = Side(style = 'thin'), bottom = Side(style = 'thin'))

			# Resize the text in the cell to make it more readable.
			font_size = 10
			value = shift.get_excel_str()
			if shift.length().seconds <= seconds_in_hour:
				font_size = 8
			if shift.length().seconds <= seconds_in_hour / 2:
				font_size = 6
				value = shift.title
			cell.font = Font(size=font_size)
			cell.value = value

			# Next we make changes for unpaid shifts and add a 1 to the appropriate time cell
			if shift.is_unpaid():
				cell.fill = PatternFill(patternType = 'solid', fill_type = 'solid', fgColor = Color('C4C4C4'))
			else:
				if shift.is_programming():
					row_adjust = 2
				else:
					row_adjust = 1
				for col in range(start_col, end_col + 1):
					time_cell = stapher_ws.cell(row = row - row_adjust, column = col)
					time_cell.value = '1'

			stapher_ws.merge_cells(start_row = row, start_column = start_col, end_row = row, end_column = end_col)
			
	print('Saving schedules.xlsx file...')
	schedule_wb.save("../output/schedules.xlsx")


# This function takes in a set of staphings and returns a list of the staphers working them 
def get_shift_workers(staphings):
	shifts_and_workers = {}
	for staphing in staphings:
		if staphing.shift.id in shifts_and_workers:
			shifts_and_workers[staphing.shift.id].append(staphing.stapher)
		else:
			shifts_and_workers[staphing.shift.id] = [staphing.stapher]
	return shifts_and_workers

# This returns a dictionary of shift ids to the shifts that are at that time
def get_shifts_ids_to_height(ordered, shifts):
	section_height = 10
	ids_to_height = {}
	largest_overlap = 0
	for day in ordered:
		times_for_day = ordered[day]
		for i in range(1, len(times_for_day)):
			start = times_for_day[i - 1]
			end = times_for_day[i]
			shifts_during_window = [shift for shift in shifts if shift.is_in_window(day, start, end)]
			if largest_overlap < len(shifts_during_window):
				largest_overlap = len(shifts_during_window)
			for shift in shifts_during_window:
				height = int(section_height / len(shifts_during_window))
				if shift.id in ids_to_height:
					old_height = ids_to_height[shift.id]
					if old_height > height:
						ids_to_height[shift.id] = height
				else:
					ids_to_height[shift.id] = height
	return ids_to_height



def set_times_to_offsets(ordered):
	times_to_offsets = {}
	for day in ordered:
		times_for_day = ordered[day]
		for i in range(1, len(times_for_day)):
			start = times_for_day[i - 1]
			time_key = get_seconds_from_day_and_time(day, start)
			times_to_offsets[time_key] = 0
	return times_to_offsets

def get_all_time_keys(shift, times_to_offset):
	time_keys = []
	shift_start_key = get_seconds_from_day_and_time(shift.day, shift.start)
	shift_end_key = get_seconds_from_day_and_time(shift.day, shift.end)
	for time_key in times_to_offset:
		if time_key >= shift_start_key and time_key < shift_end_key:
			time_keys.append(time_key)
	return time_keys

def get_and_update_largest_offset(shift, times_to_offset, height):
	time_keys = get_all_time_keys(shift, times_to_offset)
	largest_offset = 0
	for key in time_keys:
		if times_to_offset[key] > largest_offset:
			largest_offset = times_to_offset[key]
	for key in time_keys:
		# We only want to update the cells that are on the same level
		if times_to_offset[key] == largest_offset:
			times_to_offset[key] = times_to_offset[key] + height
	return largest_offset

# TODO: DRY with create_new_workbook method
def copy_master_template(masters):
	# Copy the template workbook.
	print('Creating masters.xlsx file...')
	template_wb = load_workbook('../output/masters-template.xlsx')
	template_wb.save("../output/masters.xlsx")
	master_wb = load_workbook('../output/masters.xlsx')
	for master in masters:
		template_ws = master_wb['TEMPLATE']
		print(f'Making excel worksheet for {master.title}...')

		# We copy the template worksheet for each master.
		master_ws = master_wb.copy_worksheet(template_ws)
		master_ws.title = master.title
	master_wb.remove(template_ws)
	master_wb.save("../output/masters.xlsx")

# TODO: DRY with get_start_col_from_time method
def get_master_start_col_from_time(time):
	return 2 + ((time.hour - 6) * 4) + int((time.minute / 60) * 4)

def get_master_end_col_from_time(time):
	return get_master_start_col_from_time(time) - 1

def master_row(shift):
	return (shift.day * 13) + 5

def get_col_range(shift):
	start_col = get_master_start_col_from_time(shift.start)
	end_col = get_master_end_col_from_time(shift.end)
	return [col for col in range(start_col, end_col + 1)]

# This function returns a dictionary of shift id to the height and offset of the shift
def get_shifts_ids_to_placement(shifts):
	section_height = 12
	cols_to_info = {}
	for shift in shifts:
		col_range = get_col_range(shift)
		if shift.day not in cols_to_info:
			cols_to_info[shift.day] = {}
		for col in col_range:
			if col not in cols_to_info[shift.day]:
				# The first place in the list represents the number of shifts at this time, the second represents the taken rows
				cols_to_info[shift.day][col] = [0, []] 
			cols_to_info[shift.day][col][0] = cols_to_info[shift.day][col][0] + 1
	ids_to_placement = {}
	shifts = sorted(shifts, key = attrgetter('day', 'start'))
	# In order to avoid overflowing the excel sheet - we first place the top layer of each day and then the 2nd layer and so on...
	placed_shifts = []
	last_shift = shifts[0]
	while len(placed_shifts) < len(shifts):
		for shift in shifts:
			not_seen_before = shift not in placed_shifts
			should_place_next  = shift.start == last_shift.start or not shift.overlaps(last_shift)
			have_to_place = len(shifts) == len(placed_shifts) + 1 # Since it is the last shift we have to place it regardless
			if not_seen_before and (should_place_next or have_to_place):
				# First we get the height...
				col_range = get_col_range(shift)
				most_overlap_in_range = 1
				for col in col_range:
					overlap_at_col = cols_to_info[shift.day][col][0]
					if most_overlap_in_range < overlap_at_col:
						most_overlap_in_range = overlap_at_col
				shift_height = int(section_height / most_overlap_in_range)
				# Now we find the offset by checking for the first availible set of rows 
				offset = 0
				solution_found = False
				while not solution_found:
					rows_to_occupy = [row for row in range(offset, offset + shift_height)]
					overlap_found = False
					for col in col_range:
						occupied_rows = cols_to_info[shift.day][col][1]
						if bool(set(rows_to_occupy) & set(occupied_rows)):
							overlap_found = True
					if not overlap_found:
						solution_found = True
					else:
						offset += 1
				for col in col_range:
					cols_to_info[shift.day][col][1].extend(rows_to_occupy)

				# Now we find the start row/col and end row/col and store that information to the shifts ID
				start_col = col_range[0]
				end_col = col_range[-1]
				start_row = master_row(shift) + offset
				end_row = start_row + shift_height - 1
				ids_to_placement[shift.id] = [start_col, start_row, end_col, end_row]

				# If the shifts have the same start time, we don't need to update the shift unless the one we're looking at ends earlier
				if shift.start != last_shift.start or shift.end < last_shift.end:
					last_shift = shift
				placed_shifts.append(shift)
	return ids_to_placement

def get_length(shift):
	return shift.length()

def update_standard_masters(masters, staphings):
	masters =  sorted(masters, key=attrgetter('title'))
	copy_master_template(masters)
	master_wb = load_workbook('../output/masters.xlsx')
	for master in masters:
		print(f'Updating {master} master...')
		master_staphings = master.get_master_staphings(staphings)
		shift_workers = get_shift_workers(master_staphings)
		master_shifts = list(set([s.shift for s in master_staphings]))
		master_shifts = [shift[0] for shift in sorted([[shift, shift.start, shift.length()] for shift in master_shifts], key = itemgetter(1, 2))]
		ids_to_placement = get_shifts_ids_to_placement(master_shifts)
		master_ws = master_wb[master.title]
		master_ws['A1'] =  master.title + ' Master'
		for shift in master_shifts:
			start_col = ids_to_placement[shift.id][0]
			start_row = ids_to_placement[shift.id][1]
			end_col = ids_to_placement[shift.id][2]
			end_row = ids_to_placement[shift.id][3]
			cell = master_ws.cell(row = start_row, column = start_col)
			value = shift.title + ':\n'

			# If the shift is longer than an hour... 
			if start_col < end_col - 3:
				value = shift.get_excel_str() + ':\n'

			# If the shift is 30 min or shorter... 
			if start_col >= end_col - 1:
				cell.font = Font(size = 7)
			else:
				cell.font = Font(size = 12)

			# Now we add the names of the people working the shift
			for worker in set(shift_workers[shift.id]):
				value = value + worker.first_name + ', '
			value = value[:-2]
			cell.value = value
			cell.alignment = Alignment(shrinkToFit = True, wrapText = True, horizontal = 'center', vertical = 'center')
			cell.border = Border(left = Side(style = 'thin'), right = Side(style = 'thin'), top = Side(style = 'thin'), bottom = Side(style = 'thin'))
			master_ws.merge_cells(start_row = start_row, start_column = start_col, end_row = end_row, end_column = end_col)
	print(f'Saving masters.xlsx...')
	master_wb.save("../output/masters.xlsx")
			
def get_meal_master_col(shift):
	return shift.day + 2

def get_meal_master_starting_row(shift):
	if shift.has_flag('meal-head'):
		return 3
	elif shift.has_flag('hobart'):
		if shift.start == datetime.time(12, 0, 0, 0):
			return 25
		elif shift.start == datetime.time(17, 30, 0, 0):
			return 24
	elif shift.has_flag('wine'):
			return 22
	if shift.start == datetime.time(6, 45, 0, 0):
		return 5
	elif shift.start == datetime.time(7, 0, 0, 0):
		return 20
	elif shift.start == datetime.time(7, 30, 0, 0):
		return 8
	elif shift.start == datetime.time(7, 45, 0, 0):
		return 12
	elif shift.start == datetime.time(8, 15, 0, 0):
		return 16
	elif shift.start == datetime.time(11, 15, 0, 0):
		return 5
	elif shift.start == datetime.time(11, 45, 0, 0):
		return 10
	elif shift.start == datetime.time(12, 0, 0, 0):
		return 19
	elif shift.start == datetime.time(17, 15, 0, 0):
		return 4
	elif shift.start == datetime.time(17, 30, 0, 0):
		return 13
	elif shift.start == datetime.time(18, 0, 0, 0):
		return 15


def update_meal_masters(masters, staphings):
	print(f'Loading meal master...')
	meal_master_wb = load_workbook('../output/meal-master-template.xlsx')
	for master in masters:
		print(f'Updating {master} master...')
		master_ws = meal_master_wb[master.title]
		master_staphings = master.get_master_staphings(staphings)
		shift_workers = get_shift_workers(master_staphings)
		master_shifts = list(set([s.shift for s in master_staphings]))
		for shift in master_shifts:
			col = get_meal_master_col(shift)
			curr_row = get_meal_master_starting_row(shift)
			workers = set(shift_workers[shift.id])
			for worker in workers:
				cell = master_ws.cell(row = curr_row, column = col)
				cell.value = worker.full_name()
				cell.font = Font(size = 12)
				curr_row += 1
	print('Saving meal-master.xls')
	meal_master_wb.save("../output/meal-masters.xlsx")


def update_masters(masters, staphings):
	standard_masters = []
	meal_masters = []
	for master in masters:
		if master.is_standard():
			standard_masters.append(master)
		else:
			meal_masters.append(master)
	update_standard_masters(standard_masters, staphings)
	update_meal_masters(meal_masters, staphings)




def update_analytics(staphers, staphings, flags, qualifications):
	analytics = get_analytics(staphers, staphings, flags, qualifications)
	print('Updating analytics.xlsx file...')
	analytics_wb = Workbook()
	analytics_ws = analytics_wb['Sheet']
	analytics_ws.title = 'Analytics'
	for row in range(0, len(analytics)):
		for col in range(0, len(analytics[row])):
			cell = analytics_ws.cell(row = row + 1, column = col + 1)
			cell.value = analytics[row][col]
	print(f'Savings analytics.xlsx...')
	analytics_wb.save("../output/analytics.xlsx")





