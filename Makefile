.PHONY: all test clean clean-all push backup

all: test

test:
	./run-tests.sh

clean:
	@echo "Cleaning temporary test, build, and bytecode artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.py[co]" -delete 2>/dev/null || true
	find . -type f -name "*.pyd" -delete 2>/dev/null || true
	find . -type f -name ".coverage*" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .tox tmtrack.egg-info build dist
	rm -f tmtrack_backup.json
	@docker rm -f tmtrack-test-mongo 2>/dev/null || true
	@echo "Clean complete."

clean-all: clean
	@echo "Removing virtualenv..."
	rm -rf venv/ .venv/ env/
	@echo "Clean-all complete."

push:
	docker push dana/tmtrack:latest

backup:
	ssh realms 'cd /home/dana/tmtrack && /usr/bin/python3 ./backup.py localhost:27017 tmtrack_db' && scp realms:/home/dana/tmtrack/tmtrack_backup.json /home/dana/notes/
