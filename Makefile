DJANGO_MANAGE := python manage.py

run:
	cd ./src
	@$(DJANGO_MANAGE) runserver

migrate:
	@$(DJANGO_MANAGE) migrate

makemigrations:
	@$(DJANGO_MANAGE) makemigrations

init:
	pip install -r requirements/base.txt


info:
	@echo "localhost at http://127.0.0.1:8000/"


help:
	@echo "run - run the server"
	@echo "init - install dependencies"
	@echo "migrate - apply migrations"
	@echo "makemigrations - create migrations"
	@echo "info - display server info"
	@echo "help - display this help message"
