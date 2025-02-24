# #############################################################################
# Setup
# #############################################################################

ECR_BASE_PATH=083233266530.dkr.ecr.us-east-2.amazonaws.com

IM_REPO_BASE_PATH=$(ECR_BASE_PATH)/im
IM_IMAGE_DEV=$(IM_REPO_BASE_PATH):latest
IM_IMAGE_RC=$(IM_REPO_BASE_PATH):rc

NO_SUPERSLOW_TESTS='True'

RUN_TESTS_DIR="im/devops/docker_scripts/"

IM_PG_PORT_LOCAL?=5450

# Target image for the common actions.
IMAGE_DEV=$(IM_IMAGE_DEV)
IMAGE_RC=$(IM_IMAGE_RC)

im.print_setup:
	@echo "IM_REPO_BASE_PATH=$(IM_REPO_BASE_PATH)"
	@echo "IM_IMAGE_DEV=$(IM_IMAGE_DEV)"
	@echo "IM_IMAGE_RC=$(IM_IMAGE_RC)"

# #############################################################################
# Local stage.
# #############################################################################

im.docker_pull:
	docker pull $(IMAGE_DEV)

# Run app container, start a local PostgreSQL DB.
# POSTGRES_PORT=${IM_PG_PORT_LOCAL} \
# -f devops/compose/docker-compose.yml
im.docker_up.local:
	IMAGE=$(IMAGE_DEV) \
	docker-compose \
		-f devops/compose/docker-compose.local.yml \
		run \
		--rm \
		-l user=$(USER) \
		app \
		bash

im.docker_cmd.local:
	IMAGE=$(IMAGE_DEV) \
	POSTGRES_PORT=${IM_PG_PORT_LOCAL} \
	docker-compose \
		-f devops/compose/docker-compose.yml \
		-f devops/compose/docker-compose.local.yml \
		run \
		--rm \
		-l user=$(USER) \
		app \
		$(CMD)

# Run app container without PostgreSQL.
im.docker_bash.local:
	IMAGE=$(IMAGE_DEV) \
	POSTGRES_PORT=${IM_PG_PORT_LOCAL} \
	docker-compose \
		-f devops/compose/docker-compose.yml \
		-f devops/compose/docker-compose.local.yml \
		run \
		--rm \
		-l user=$(USER) \
		--no-deps \
		--entrypoint=im/devops/docker_build/entrypoints/entrypoint_app_only.sh \
		app \
		bash

# Stop local container including all dependencies.
im.docker_down.local:
	IMAGE=$(IMAGE_DEV) \
	POSTGRES_PORT=${IM_PG_PORT_LOCAL} \
	docker-compose \
		-f devops/compose/docker-compose.yml \
		-f devops/compose/docker-compose.local.yml \
		down

# Stop local container including all dependencies and remove all data.
im.docker_rm.local:
	IMAGE=$(IMAGE_DEV) \
	POSTGRES_PORT=${IM_PG_PORT_LOCAL} \
	docker-compose \
		-f devops/compose/docker-compose.yml \
		-f devops/compose/docker-compose.local.yml \
		down; \
	docker volume rm \
		compose_im_postgres_data_local

# #############################################################################
# Development stage.
# #############################################################################

# Run app container.
im.docker_bash.dev:
	IMAGE=$(IMAGE_DEV) \
	docker-compose \
		-f devops/compose/docker-compose.dev.yml \
		run \
		--rm \
		app \
		bash

# Run command in app.
im.docker_cmd.dev:
	IMAGE=$(IMAGE_DEV) \
	docker-compose \
		-f devops/compose/docker-compose.dev.yml \
		run \
		--rm \
		-l user=$(USER) \
		app \
		$(CMD)

# Run app container without PostgreSQL.
im.docker_bash_without_psql.dev:
	IMAGE=$(IMAGE_DEV) \
	docker-compose \
		-f devops/compose/docker-compose.dev.yml \
		run \
		--rm \
		-l user=$(USER) \
		--no-deps \
		--entrypoint=im/devops/docker_build/entrypoints/entrypoint_app_only.sh \
		app \
		bash

# Stop dev container including all dependencies.
im.docker_down.dev:
	IMAGE=$(IMAGE_DEV) \
	docker-compose \
		-f devops/compose/docker-compose.dev.yml \
		down

# #############################################################################
# Multistage.
# #############################################################################

im.docker_up.multistage:
	docker-compose \
		-f devops/compose/docker-compose.multistage.yml \
		-d \
		up

# Stop multistage container including all dependencies.
im.docker_down.multistage:
	docker-compose \
		-f devops/compose/docker-compose.multistage.yml \
		down

# #############################################################################
# Test IM workflow.
# #############################################################################

# We need to pass the params from the callers.
# E.g.,
# > make run_*_tests _IMAGE=083233266530.dkr.ecr.us-east-2.amazonaws.com/amp_env:rc
im._run_tests:
	IMAGE=$(_IMAGE) \
	docker-compose \
		-f devops/compose/docker-compose.yml \
		-f devops/compose/docker-compose.test.yml \
		run \
		--rm \
		-l user=$(USER) \
		app \
		$(_CMD)

# Make sure pytest works.
im.run_blank_tests:
	_IMAGE=$(IMAGE_DEV) \
	_CMD="pytest -h >/dev/null" \
	make im._run_tests

im.run_fast_tests:
ifeq ($(NO_FAST_TESTS), 'True')
	@echo "No fast tests"
else
	_IMAGE=$(IMAGE_RC) \
	_CMD="$(RUN_TESTS_DIR)/run_fast_tests.sh $(USER_OPTS)" \
	make im._run_tests
endif

# Run the tests with the base container and the tests needing a special container.
im.run_all_fast_tests:
	(cd ..; make run_fast_tests USER_OPTS="im")
	make im.run_fast_tests

im.run_all_fast_tests_coverage:
	(cd ..; make run_fast_tests USER_OPTS="--cov --cov-branch --cov-report term-missing --cov-report html --cov-report annotate im")
	make im.run_fast_tests USER_OPTS="--cov --cov-branch --cov-report term-missing --cov-report html --cov-report annotate"
	(cd ../htmlcov; python -m http.server 33333)

im.run_slow_tests:
ifeq ($(NO_SLOW_TESTS), 'True')
	@echo "No slow tests"
else
	_IMAGE=$(IMAGE_DEV) \
	_CMD="$(RUN_TESTS_DIR)/run_slow_tests.sh" \
	make im._run_tests
endif

im.run_superslow_tests:
ifeq ($(NO_SUPERSLOW_TESTS), 'True')
	@echo "No superslow tests"
else
	_IMAGE=$(IMAGE_DEV) \
	_CMD="$(RUN_TESTS_DIR)/run_superslow_tests.sh" \
	make im._run_tests
endif

# #############################################################################
# Images workflows.
# #############################################################################

# Use Docker buildkit or not.
# DOCKER_BUILDKIT=1
DOCKER_BUILDKIT=0
GITHUB_SHA?=$(shell git rev-parse HEAD)
IMAGE_RC_SHA:=$(GITHUB_SHA)

im.docker_build_image.rc:
	DOCKER_BUILDKIT=$(DOCKER_BUILDKIT) \
	docker build \
		--progress=plain \
		--no-cache \
		-t $(IMAGE_RC) \
		-t $(IM_REPO_BASE_PATH):$(IMAGE_RC_SHA) \
		--file devops/docker_build/dev.Dockerfile \
		.

im.docker_build_image_with_cache.rc:
	DOCKER_BUILDKIT=$(DOCKER_BUILDKIT) \
	docker build \
		--progress=plain \
		-t $(IMAGE_RC) \
		-t $(IM_REPO_BASE_PATH):$(IMAGE_RC_SHA) \
		--file devops/docker_build/dev.Dockerfile \
		.

# Push the "rc" image to the registry.
im.docker_push_image.rc:
	docker push $(IMAGE_RC)
	docker push $(IM_REPO_BASE_PATH):$(IMAGE_RC_SHA)

# Mark the "rc" image as "latest".
im.docker_tag_rc_image.latest:
	docker tag $(IMAGE_RC) $(IMAGE_DEV)

# Push the "latest" image to the registry.
im.docker_push_image.latest:
	docker push $(IMAGE_DEV)

im.docker_release.latest:
	make im.docker_build_image_with_cache.rc
	make im.run_fast_tests.rc
	#make run_slow_tests.rc
	make im.docker_tag_rc_image.latest
	make im.docker_push_image.latest
	@echo "==> SUCCESS <=="

# #############################################################################
# Test IM workflow (RC)
# #############################################################################

# Make sure pytest works.
im.run_blank_tests.rc:
	_IMAGE=$(IMAGE_RC) \
	_CMD="pytest -h >/dev/null" \
	make im._run_tests

im.run_fast_tests.rc:
ifeq ($(NO_FAST_TESTS), 'True')
	@echo "No fast tests"
else
	_IMAGE=$(IMAGE_RC) \
	_CMD="$(RUN_TESTS_DIR)/run_fast_tests.sh" \
	make im._run_tests
endif

im.run_slow_tests.rc:
ifeq ($(NO_SLOW_TESTS), 'True')
	@echo "No slow tests"
else
	_IMAGE=$(IMAGE_RC) \
	_CMD="$(RUN_TESTS_DIR)/run_slow_tests.sh" \
	make im._run_tests
endif

im.run_superslow_tests.rc:
ifeq ($(NO_SUPERSLOW_TESTS), 'True')
	@echo "No superslow tests"
else
	_IMAGE=$(IMAGE_RC) \
	_CMD="$(RUN_TESTS_DIR)/run_superslow_tests.sh" \
	make im._run_tests
endif

# #############################################################################
# Self test.
# #############################################################################

# Run sanity checks on the current build system to make sure it works after
# changes.
#
# NOTE: We need to run with IMAGE_RC since that's what we should be working
# with, when changing the build system.

im.fast_self_tests:
	make im.print_setup
	make im.docker_pull
	make im.docker_build_image_with_cache.rc
	make im.run_fast_tests.rc
	make im.docker_cmd.local CMD="ls"
	@echo "==> SUCCESS <=="

im.slow_self_tests:
	make im.docker_build_image.prod
	make im.run_slow_tests.rc
	@echo "==> SUCCESS <=="

im.self_tests:
	make im.fast_self_tests
	make im.slow_self_tests
	@echo "==> SUCCESS <=="

#BASE_IMAGE?=$(IM_IMAGE)
#VERSION?=
## Tag :latest image with specific tag
#docker_im_tag_latest_version:
#ifeq ($(VERSION),)
#	@echo "You need to provide VERSION parameter. Example: 'make docker_tag_im_rc_version VERSION=0.1'"
#else
#	docker tag $(BASE_IMAGE) $(IM_REPO_BASE_PATH):$(VERSION)
#endif
#
## Push image wish specific tag
#docker_im_push_version_image:
#ifeq ($(VERSION),)
#	@echo "You need to provide VERSION parameter. Example: 'make docker_push_im_version_image VERSION=0.1'"
#else
#	docker push $(IM_REPO_BASE_PATH):$(VERSION)
#endif
