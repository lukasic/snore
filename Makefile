.PHONY: install install-backend install-frontend dev dev-backend dev-frontend test build-frontend hash

venv:
	pyenv virtualenv 3.14.3 snore

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

dev:
	@echo "Start backend:  make dev-backend"
	@echo "Start frontend: make dev-frontend"

test:
	cd backend && pytest

build-frontend:
	cd frontend && npm run build

# Generate a bcrypt hash for a password (usage: make hash PW=yourpassword)
hash:
	python3 -c "import bcrypt; print(bcrypt.hashpw('$(PW)'.encode(), bcrypt.gensalt()).decode())"
