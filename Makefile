.PHONY: install
install: ## Install the virtual environment and install the pre-commit hooks
	@echo "🚀 Creating virtual environment using uv"
	@uv sync
	@source .venv/bin/activate && uv run pre-commit install

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Linting code: Running pre-commit"
	@source .venv/bin/activate && uv run pre-commit run -a
	@echo "🚀 Static type checking: Running mypy"
	@source .venv/bin/activate && uv run mypy
	@echo "🚀 Checking for obsolete dependencies: Running deptry"
	@source .venv/bin/activate && uv run deptry .

.PHONY: test
test: ## Run unit tests only (excludes all integration tests)
	@echo "🚀 Testing code: Running unit tests only"
	@source .venv/bin/activate && uv run python -m pytest -k "not integration" --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: test-integration
test-integration: ## Run all integration tests
	@echo "🚀 Testing code: Running integration tests"
	@source .venv/bin/activate && INTEGRATION_TESTS=1 uv run python -m pytest tests/integration/

.PHONY: test-all
test-all: ## Run all tests including integration tests
	@echo "🚀 Testing code: Running all tests"
	@source .venv/bin/activate && INTEGRATION_TESTS=1 uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@uvx --from build pyproject-build --installer uv

.PHONY: clean-build
clean-build: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@source .venv/bin/activate && uv run python -c "import shutil; import os; shutil.rmtree('dist') if os.path.exists('dist') else None"

.PHONY: publish
publish: ## Publish a release to PyPI.
	@echo "🚀 Publishing."
	@uvx twine upload --repository-url https://upload.pypi.org/legacy/ dist/*

.PHONY: build-and-publish
build-and-publish: build publish ## Build and publish.

.PHONY: docs-test
docs-test: ## Test if documentation can be built without warnings or errors
	@source .venv/bin/activate && uv run mkdocs build -s

.PHONY: docs
docs: ## Build and serve the documentation
	@source .venv/bin/activate && uv run mkdocs serve

.PHONY: help
help:
	@source .venv/bin/activate && uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
