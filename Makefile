.PHONY: install data pipeline report dashboard test lint all

install:
	pip install -r requirements-dev.txt

data:
	PYTHONPATH=src python -m ecommerce.generate

pipeline:
	PYTHONPATH=src python -m ecommerce.pipeline

report:
	PYTHONPATH=src python -m ecommerce.report

dashboard:
	streamlit run app.py

test:
	pytest -q

lint:
	ruff check .

all: data pipeline report
