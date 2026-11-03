.PHONY: install-deps api frontend load-test

install-deps:
	cd backend && ../.venv/bin/python -m pip install -r requirements.txt

api:
	cd backend && ../.venv/bin/python -m src.main

frontend:
	python3 -m http.server 8001 --directory frontend

load-test:
	./.venv/bin/python -m locust -f backend/tests/load_tests/authentication.py --host=http://localhost:8000 --csv=auth_metrics

start-containers:
	docker-compose up -d

build-containers:
	docker-compose up -d --build

stop-containers:
	docker-compose down

container-logs:
	docker-compose logs -f
