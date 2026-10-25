.PHONY: backend-test backend-lint frontend-test frontend-build
backend-test:
	cd backend && pytest
backend-lint:
	cd backend && ruff check .
frontend-test:
	cd frontend && npm test
frontend-build:
	cd frontend && npm run build
