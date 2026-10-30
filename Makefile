.PHONY: install-deps

install-deps:
	cd backend && ../.venv/bin/python -m pip install -r requirements.txt

api:
	cd backend && ../.venv/bin/python -m src.main

frontend:
	cd frontend && npm run dev
