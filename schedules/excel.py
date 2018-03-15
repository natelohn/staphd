from openpyxl import load_workbook


# This function takes in a list of staphers and staphings and makes a readable xl file for each stapher.
def update_individual_excel_files(staphers, staphings):
	# Copy the template workbook.
	template_wb = load_workbook('../output/template.xlsx')
	template_wb.save("../output/schedules.xlsx")
	schedule_wb = load_workbook('../output/schedules.xlsx')

	# Get the template worksheet.
	template_ws = schedule_wb.active

	# Loop the staphers:
	shuffle(staphers)
	for stapher in staphers[:1]:
		stapher_ws = schedule_wb.copy_worksheet(template_ws)
		stapher_ws.title = stapher.full_name()
		stapher_ws['A1'] = 'Name: ' + stapher.full_name()

	# Save the file
	schedule_wb.remove(template_ws)
	schedule_wb.save("../output/schedules.xlsx")
	return