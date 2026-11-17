# One command per job. On Windows without make, run the commands on the right of each target.
.PHONY: all analysis dashboard test notebook

all: analysis dashboard test

analysis:   ## the whole analysis: outputs/tables + outputs/figures
	python -m bayyin

dashboard:  ## data tables + index.html
	python dashboard/build.py

test:       ## Python tests (also run the JavaScript tests) and the JavaScript tests alone
	python -m pytest
	node --test

notebook:   ## re-run analysis.ipynb and store its outputs
	jupyter nbconvert --to notebook --execute --inplace analysis.ipynb
