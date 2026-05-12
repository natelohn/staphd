.PHONY: run setup

run:
	python manage.py runserver

setup:
	python manage.py migrate
	python manage.py createsuperuser
