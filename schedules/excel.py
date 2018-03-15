from openpyxl import load_workbook
from openpyxl.styles import Alignment, Color, PatternFill, Border, Side, Font
from operator import attrgetter


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

def get_shift_dict(staphings):
	shift_dict = {}
	for staphing in staphings:
		if staphing.stapher.id in shift_dict:
			shift_dict[staphing.stapher.id].append(staphing.shift)
		else:
			shift_dict[staphing.stapher.id] = [staphing.shift]
	return shift_dict

def get_row_from_day(day):
	return 5 + (day * 4)

def get_start_col_from_time(time):
	return 3 + ((time.hour - 6) * 4) + int((time.minute / 60) * 4)

def get_end_col_from_time(time):
	return get_start_col_from_time(time) - 1

# This function takes in a list of staphers and staphings and makes a readable xl file for each stapher.
def update_individual_excel_files(staphers, staphings):
	wb_str = create_new_workbook(staphers)
	schedule_wb = load_workbook(wb_str)

	# Get the information needed before opening excel files.
	shift_dict = get_shift_dict(staphings)
	seconds_in_hour = 60 * 60

	for stapher in staphers:
		print(f'Populating excel worksheet for {stapher.full_name()}...')
		stapher_ws = schedule_wb[stapher.full_name()]
		stapher_ws['A1'] = 'Name: ' + stapher.full_name()
		stapher_ws['AE1'] = 'Postion: ' + stapher.title
		shifts = sorted(shift_dict[stapher.id], key = attrgetter('day', 'start'))
		for shift in shifts:
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