import datetime as dt
from django import forms
from django.db import models
from django.db.models.functions import Lower

from .models import Flag, Qualification, Schedule, Settings, Shift, Stapher, Staphing
from .models import Settings as ScheduleBuildingSettings


class StapherCreateForm(forms.ModelForm):
	
	class Meta:
		model = Stapher
		fields = ['first_name','last_name', 'title', 'age', 'class_year', 'summers_worked', 'gender','qualifications']
		widgets = { 'qualifications': forms.CheckboxSelectMultiple()}


	def __init__(self, auto_id, *args, **kwargs):
		super(StapherCreateForm, self).__init__(*args, **kwargs)
		self.auto_id = auto_id
		self.fields['qualifications'].queryset = Qualification.objects.order_by(Lower('title'))
		
	def clean_first_name(self):
		first_name = self.cleaned_data.get("first_name")
		return self.clean_name(first_name)

	def clean_last_name(self):
		last_name = self.cleaned_data.get("last_name")
		return self.clean_name(last_name)

	def clean_name(self, name):
		just_chars = name.replace(' ', '').replace('-', '').replace('.', '')
		if not just_chars.isalpha():
			raise forms.ValidationError("Must use only alphanumeric characters.")
		return name		

	def clean_age(self):
		age = self.cleaned_data.get("age")
		min_age = 16
		max_age = 100
		if age < min_age:
			raise forms.ValidationError("Minimum age is 16.")
		if age > max_age:
			raise forms.ValidationError("They should retire.")
		return age


	def clean_class_year(self):
		class_year = self.cleaned_data.get("class_year")
		age = self.cleaned_data.get("age")
		this_year = dt.datetime.today().year
		if not age:
			age = 18
		max_class_year = this_year + 4
		min_class_year = this_year - age + 10
		if class_year > max_class_year:
			raise forms.ValidationError("Their class year must be within 4 years of current year (Current freshman)")
		if class_year < min_class_year:
			raise forms.ValidationError("They could not have graduated before they were 10.")
		return class_year

	def clean_summers_worked(self):
		summers_worked = self.cleaned_data.get("summers_worked")
		age = self.cleaned_data.get("age")
		if not age:
			age = 18
		max_summers = age
		min_summers = 0
		if summers_worked > max_summers:
			raise forms.ValidationError("They have not been alive that many summers.")
		if summers_worked < min_summers:
			raise forms.ValidationError("Must be a positive integer.")
		return summers_worked

	def clean_gender(self):
		gender = self.cleaned_data.get("gender")
		if not gender:
			gender = 3
		return gender

	def clean_qualifications(self):
		qualifications = self.cleaned_data.get("qualifications")
		for s in Staphing.objects.filter(stapher = self.instance):
			for q in s.shift.qualifications.all():
				if q not in qualifications:
					error_string = f"The {q} qualification is needed for {self.instance}'s scheduled shift {s.shift} on {s.schedule}. Give the {q} qualification to {self.instance} or remove {s.shift} from {self.instance}'s schedule on {s.schedule}."
					raise forms.ValidationError(error_string)
		return qualifications

class ShiftCreateForm(forms.ModelForm):
	class Meta:
		model = Shift
		fields = ('title','start','end','day','workers_needed','flags','qualifications')
		widgets = {'flags': forms.CheckboxSelectMultiple(), 'qualifications': forms.CheckboxSelectMultiple()}

	def __init__(self, auto_id, *args, **kwargs):
		super(ShiftCreateForm, self).__init__(*args, **kwargs)
		self.auto_id = auto_id
		self.fields['flags'].queryset = Flag.objects.order_by(Lower('title'))
		self.fields['qualifications'].queryset = Qualification.objects.order_by(Lower('title'))

	def clean_start(self):
		start = self.cleaned_data.get("start")
		if not start:
			raise forms.ValidationError("Must enter a valid time format: (i.e. 12:00pm)")
		return start

	def clean_end(self):
		start = self.cleaned_data.get("start")
		end = self.cleaned_data.get("end")
		if not end:
			raise forms.ValidationError("Must enter a valid time format: (i.e. 12:00pm)")
		if start and start >= end:
			raise forms.ValidationError("Shift must end after it starts.")
		return end

	def clean_day(self):
		day = self.cleaned_data.get("day")
		start = self.cleaned_data.get("start")
		end = self.cleaned_data.get("end")
		for s in Staphing.objects.filter(shift = self.instance):
			staphers_other_staphings = Staphing.objects.filter(stapher = s.stapher).exclude(shift = self.instance)
			for other_s in staphers_other_staphings:
				if other_s.shift.is_in_window(day, start, end) and s.schedule.id == other_s.schedule.id:
					error_string = f"{s.stapher} is working {s.shift} and {other_s.shift} on the {other_s.schedule} schedule, so this time edit can not be made. Either delete {s.shift} or {other_s.shift} from {s.stapher}'s schedule on {other_s.schedule} to make this edit."
					raise forms.ValidationError(error_string)
		return day

	def clean_workers_needed(self):
		workers_needed = self.cleaned_data.get("workers_needed")
		min_workers = 1
		max_availible_workers = Stapher.objects.all().count()
		if workers_needed < min_workers:
			raise forms.ValidationError(f"Shifts require at least {min_workers} worker.")
		if workers_needed > max_availible_workers:
			raise forms.ValidationError(f'You have {max_availible_workers} workers! Shifts cannot require more workers than you have.')
		scheduled_per_schedule = {}
		over_scheduled_schedule = None
		for s in Staphing.objects.filter(shift = self.instance):
			if s.schedule.id in scheduled_per_schedule:
				scheduled_per_schedule[s.schedule.id] += 1
			else:
				scheduled_per_schedule[s.schedule.id] = 1
			if scheduled_per_schedule[s.schedule.id] > workers_needed:
				over_scheduled_schedule = s.schedule
		if over_scheduled_schedule:
			raise forms.ValidationError(f"The \"{over_scheduled_schedule}\" schedule has more than {workers_needed} scheduled worker(s) for this shift ({scheduled_per_schedule[over_scheduled_schedule.id]} workers to be exact). To make this edit delete {scheduled_per_schedule[over_scheduled_schedule.id] - workers_needed} workers from the \"{over_scheduled_schedule}\" schedule")
		return workers_needed

	def clean_qualifications(self):
		qualifications = self.cleaned_data.get("qualifications")
		for s in Staphing.objects.filter(shift = self.instance):
			for q in qualifications: 
				if q not in s.stapher.qualifications.all():
					error_string = f"{s.stapher} does not have the {q} qualification and they are scheduled for {self.instance} on {s.schedule}. Give the {q} qualification to {s.stapher} or remove {self.instance} from {s.stapher}'s schedule on {s.schedule}."
					raise forms.ValidationError(error_string)
		return qualifications



class QualificationCreateForm(forms.ModelForm):
	class Meta:
		model = Qualification
		fields = [
			'title'
		]


class FlagCreateForm(forms.ModelForm):
	class Meta:
		model = Flag
		fields = [
			'title'
		]


class ScheduleCreateForm(forms.ModelForm):
	class Meta:
		model = Schedule
		fields = [
			'title'
		]

class SettingsParameterForm(forms.ModelForm):
	class Meta:
		model = ScheduleBuildingSettings
		fields = [
			'parameters'
		]
		widgets = { 'parameters': forms.CheckboxSelectMultiple()}

class SettingsPreferenceForm(forms.ModelForm):
	class Meta:
		model = ScheduleBuildingSettings
		fields = [
			'auto_schedule',
			'auto_threshold',
			'tie_breaker'
		]

	def clean_auto_threshold(self):
		auto_threshold = self.cleaned_data.get("auto_threshold")
		min_auto_threshold = 0
		max_auto_threshold = ScheduleBuildingSettings.objects.get().parameters.all().count()
		if auto_threshold < min_auto_threshold:
			raise forms.ValidationError(f"A thresholds minimum possible value is {min_auto_threshold}.")
		if auto_threshold > max_auto_threshold:
			raise forms.ValidationError(f'You have {max_auto_threshold} active parameters. A threshold greater than {max_auto_threshold} is not allowed.')
		return auto_threshold


class AddShiftsForm(forms.Form):
	ALL_SHIFTS = {}
	for shift in Shift.objects.all():
		ALL_SHIFTS[shift.id] = f'{shift}'
	added_shifts = forms.MultipleChoiceField(label='added_shifts', widget = forms.CheckboxSelectMultiple(), choices=tuple(sorted(ALL_SHIFTS.items())))


	def clean_test_shifts(self):
		added_shifts = self.cleaned_data.get("added_shifts")
		print(f'cleaning -->> {test_shifts}')
		return added_shifts


