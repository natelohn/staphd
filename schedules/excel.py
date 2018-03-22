from openpyxl import load_workbook
from openpyxl.styles import Alignment, Color, PatternFill, Border, Side, Font
from operator import attrgetter, itemgetter

from .sort import get_ordered_start_and_end_times_by_day, get_seconds_from_day_and_time

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
	template_wb = load_workbook('../output/masters-templates.xlsx')
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
	return (shift.day * 11) + 5

def update_masters(masters, staphings):
	masters = sorted(masters, key=attrgetter('title'))
	copy_master_template(masters)
	master_wb = load_workbook('../output/masters.xlsx')
	for master in masters:
		print(f'Updating {master} master...')
		master_staphings = master.get_master_staphings(staphings)
		shift_workers = get_shift_workers(master_staphings)
		master_shifts = set([s.shift for s in master_staphings])
		shift_info = [[shift, shift.start, (shift.length() * -1)] for shift in master_shifts]
		sorted_master_shifts = [shift[0] for shift in sorted(shift_info, key=itemgetter(1, 2))]
		ordered = get_ordered_start_and_end_times_by_day(sorted_master_shifts)
		times_to_offset = set_times_to_offsets(ordered)
		ids_to_height = get_shifts_ids_to_height(ordered, sorted_master_shifts)
		off_set_dict = {}
		test_info = []
		master_ws = master_wb[master.title]
		master_ws['A1'] =  master.title + ' Master'
		for shift in sorted_master_shifts:
			height = ids_to_height[shift.id]
			offset = get_and_update_largest_offset(shift, times_to_offset, height)
			start_row = master_row(shift) + offset
			end_row = start_row + height - 1
			start_col = get_master_start_col_from_time(shift.start)
			end_col = get_master_end_col_from_time(shift.end)
			print(f'		{shift}: {height} & {offset} -> ({start_col} right, {start_row} down):({end_col} right, {end_row} down)')
			cell = master_ws.cell(row = start_row, column = start_col)
			value = shift.get_excel_str() + '\n'
			for worker in shift_workers[shift.id]:
				value = value + worker.first_name + ', '
			value = value[:-2]
			cell.value = value
			cell.alignment = Alignment(shrinkToFit = True, wrapText = True, horizontal = 'center', vertical = 'center')
			cell.border = Border(left = Side(style = 'thin'), right = Side(style = 'thin'), top = Side(style = 'thin'), bottom = Side(style = 'thin'))
			master_ws.merge_cells(start_row = start_row, start_column = start_col, end_row = end_row, end_column = end_col)
	print(f'Saving masters.xlsx...')
	master_wb.save("../output/masters.xlsx")
			



def update_analytics(staphers, staphings):
	print('Creating analytics.xlsx file...')
	template_wb = load_workbook('../output/analytics-template.xlsx')
	template_wb.save("../output/analytics.xlsx")
	analytics_wb = load_workbook('../output/analytics.xlsx')
	analytics_ws = analytics_wb['Analytics']
	stapher_col = 2
	for stapher in staphers:
		print(f'Updating analytics for {stapher.full_name()}...')
		name_cell = analytics_ws.cell(row = 1, column = stapher_col)
		name_cell.value = stapher.full_name()
		hour_cell = analytics_ws.cell(row = 2, column = stapher_col)
		hour_cell.value = stapher.total_hours(staphings)
		stapher_col += 1
	print(f'Savings analytics.xlsx...')
	analytics_wb.save("../output/analytics.xlsx")





