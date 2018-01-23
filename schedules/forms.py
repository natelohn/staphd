import datetime as dt
from django import forms

from .models import Flag, Stapher, Shift, Qualification


class StapherCreateForm(forms.ModelForm):
	class Meta:
		model = Stapher
		fields = [
			'first_name',
			'last_name',
			'title',
			'gender',
			'age',
			'class_year',
			'summers_worked',
			'qualifications'
		]

	def clean_first_name(self):
		first_name = self.cleaned_data.get("first_name")
		return self.clean_name(first_name)

	def clean_last_name(self):
		last_name = self.cleaned_data.get("last_name")
		return self.clean_name(last_name)

	def clean_name(self, name):
		just_chars = name.replace(' ', '').replace('-', '')
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





class ShiftCreateForm(forms.ModelForm):
	class Meta:
		model = Shift
		fields = [
			'title',
			'flag',
			'day',
			'start',
			'end',
			'workers_needed',
			'difficult',
			'qualifications'
		]

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




