.PHONY: help install train validate predict backend frontend test docker-up docker-down

help:
	@echo "Drone Navigation AI — Development Commands"
	@echo "  make install     - Install Python and Node dependencies"
	@echo "  make train       - Train YOLOv11 model"
	@echo "  make validate    - Validate YOLOv11 model and print metrics"
	@echo "  make predict     - Run inference on sample image"
	@echo "  make backend     - Start FastAPI backend with Uvicorn"
	@echo "  make frontend    - Start Next.js frontend dev server"
	@echo "  make test        - Run backend test suite"
	@echo "  make docker-up   - Run complete stack via Docker Compose"
	@echo "  make docker-down - Stop Docker Compose services"

install:
	pip install -r backend/requirements.txt
	pip install -r ml_engine/requirements.txt
	cd frontend && npm install

train:
	python ml_engine/scripts/train.py --config ml_engine/configs/training.yaml

validate:
	python ml_engine/scripts/validate.py --model ml_engine/models/trained/best.pt

predict:
	python ml_engine/scripts/predict.py --source $$(ls test/images/*.jpg | head -n 1)

backend:
	uvicorn backend.app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest backend/tests

docker-up:
	docker compose up --build

docker-down:
	docker compose down
