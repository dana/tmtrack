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
	rm -rf .pytest_cache htmlcov .tox tmtrack.egg-info build dist venv/ .venv/ env/
	rm -f tmtrack_backup.json tmtrack_backup.json.tmp
	@docker rm -f tmtrack-test-mongo 2>/dev/null || sudo -n docker rm -f tmtrack-test-mongo 2>/dev/null || true
	@echo "Clean complete."

clean-all: clean
	@echo "Clean-all complete."

push:
	docker push dana/tmtrack:latest

backup:
	@if [ -n "$$MONGO_URI" ]; then \
		echo "Backing up from MONGO_URI ($$MONGO_URI)..."; \
		./backup.py "$$MONGO_URI" "$${MONGO_DB_NAME:-tmtrack_db}" tmtrack_backup.json; \
	elif command -v microk8s >/dev/null 2>&1 && microk8s kubectl get ns tmtrack >/dev/null 2>&1; then \
		echo "Backing up from local MicroK8s tmtrack-api pod on elwing..."; \
		microk8s kubectl exec -n tmtrack deployment/tmtrack-api -- python3 /app/backup.py mongodb://mongodb.mongodb.svc.cluster.local:27017/ tmtrack_db /tmp/tmtrack_backup.json >/dev/null && \
		microk8s kubectl exec -n tmtrack deployment/tmtrack-api -- cat /tmp/tmtrack_backup.json > tmtrack_backup.json.tmp && \
		microk8s kubectl exec -n tmtrack deployment/tmtrack-api -- rm -f /tmp/tmtrack_backup.json && \
		mv tmtrack_backup.json.tmp tmtrack_backup.json; \
	else \
		echo "Backing up from elwing-lan MicroK8s tmtrack-api pod..."; \
		ssh elwing-lan "microk8s kubectl exec -n tmtrack deployment/tmtrack-api -- python3 /app/backup.py mongodb://mongodb.mongodb.svc.cluster.local:27017/ tmtrack_db /tmp/tmtrack_backup.json >/dev/null && microk8s kubectl exec -n tmtrack deployment/tmtrack-api -- cat /tmp/tmtrack_backup.json && microk8s kubectl exec -n tmtrack deployment/tmtrack-api -- rm -f /tmp/tmtrack_backup.json" > tmtrack_backup.json.tmp && \
		mv tmtrack_backup.json.tmp tmtrack_backup.json; \
	fi
	@echo "Backup successfully saved to tmtrack_backup.json"
