.PHONY: install test cov run ui dark board gov clean

install:
	pip install -r requirements.txt fastapi uvicorn httpx

test:
	pytest -q

cov:
	pytest -q --cov=. --cov-report=term-missing

run:
	uvicorn web_ui_premium:app --port 8000

dark:
	uvicorn web_ui_dark:app --port 8003

board:
	uvicorn web_board:app --port 8002

gov:
	uvicorn web_governance:app --port 8001

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
