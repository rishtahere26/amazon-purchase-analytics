# Amazon Purchase Analytics — pipeline targets
# `make demo`  : synthetic data -> SQLite -> docs/index.html (committed, public-safe)
# `make real`  : your Amazon export in data/raw/ -> local/index.html (gitignored)

PY := python3

.PHONY: demo real report-demo report-real clean

demo:
	$(PY) etl/generate_sample_data.py --out data/sample --seed 26
	$(PY) etl/load.py --source data/sample --db data/demo.db
	$(PY) analytics/export_dashboard.py --db data/demo.db --out docs/index.html --title-note "demo data"

real:
	$(PY) etl/load.py --source data/raw --db data/real.db
	$(PY) analytics/export_dashboard.py --db data/real.db --out local/index.html

report-demo: data/demo.db
	$(PY) analytics/report.py --db data/demo.db

report-real: data/real.db
	$(PY) analytics/report.py --db data/real.db

clean:
	rm -rf data/sample data/demo.db data/real.db local/index.html
