load:
	python run_pipeline.py

test:
	python -m pytest tests/ -v

clean:
	rm -f db/nifty100.db output/*.csv
	find . -name "__pycache__" -exec rm -rf {} +