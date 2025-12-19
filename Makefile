BASE_PROJECT_NAME := myproject
PROJECT_NAME := mymodule
DOCKER_IMAGE_TAG := $(BASE_PROJECT_NAME)/$(PROJECT_NAME)
DOCKER_CONTAINER_NAME := $(BASE_PROJECT_NAME)-$(PROJECT_NAME)

install-dev:  ## install dev and test dependencies
	uv lock
	uv sync --group dev --group test

install-test:  ## install only test dependencies
	uv lock
	uv sync --group test

install:  ## install standalone package
	uv lock
	uv sync

test:  ## run tests
	uv run pytest -sv tests

test-cov:  ## run tests with coverage reports (for Jenkins)
	uv run pytest --cov mymodule \
		-o junit_family=xunit2 -o cache_dir=/tmp \
		--cov-report term-missing \
		--cov-report xml:./reports/coverage.xml --junitxml=./reports/junit-result.xml \
		-sv tests

run:  ## run on host
	uv run python -m mymodule.cli --help

docker-build: ## run docker build to create docker image
	docker build . -t $(DOCKER_IMAGE_TAG)

docker-run-dev: ## run docker image in dev mode (with network=host and using the local .env)
	docker run --rm --net=host --env-file .env --name $(DOCKER_CONTAINER_NAME) -t $(DOCKER_IMAGE_TAG) $(COMMAND)

docker-clean: ## remove docker image
	docker rmi $(DOCKER_IMAGE_TAG) || exit 0

help:  ## This help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
