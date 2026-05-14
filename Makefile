PYTHON = venv/bin/python

.PHONY: run setup load-demo reset-demo test install-hooks

run:
	$(PYTHON) manage.py runserver

setup:
	$(PYTHON) manage.py migrate
	$(PYTHON) manage.py collectstatic --noinput

load-demo:
	$(PYTHON) manage.py loaddata shiftset
	$(PYTHON) manage.py loaddata flags
	$(PYTHON) manage.py loaddata qualifications
	$(PYTHON) manage.py loaddata shifts
	$(PYTHON) manage.py loaddata demo_staphers
	$(PYTHON) manage.py loaddata parameters
	$(PYTHON) manage.py loaddata settings
	$(PYTHON) manage.py create_demo_superuser

reset-demo:
	$(PYTHON) manage.py loaddata shiftset
	$(PYTHON) manage.py loaddata flags
	$(PYTHON) manage.py loaddata qualifications
	$(PYTHON) manage.py loaddata shifts
	$(PYTHON) manage.py reset_demo_staphers
	$(PYTHON) manage.py loaddata parameters
	$(PYTHON) manage.py loaddata settings
	$(PYTHON) manage.py create_demo_superuser

test:
	$(PYTHON) manage.py test schedules --verbosity=1

install-hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	chmod +x .githooks/pre-push
	@echo "Git hooks installed."
