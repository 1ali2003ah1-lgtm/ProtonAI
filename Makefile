install:
	pip install -r requirements.txt

test:
	pytest -q

coverage:
	pytest -q --cov=tools --cov-report=term

site:
	python tools/make_site.py

physics:
	python -m tools.make_physics_report

qa:
	python -m tools.physics_qa

docker-build:
	docker build -t protonai .

docker-run:
	docker run -p 8000:8000 protonai
