## #############################################################################
## Local stage.
## #############################################################################

# Run ib connect app container.
IB_CONNECT_APP?=GATEWAY
IB_CONNECT_TRUSTED_IPS?=""
IB_CONNECT_VNC_PASSWORD?=
IB_CONNECT_API_PORT?=4003
IB_CONNECT_VNC_PORT?=5901

# TODO(gp): The difference between docker_run and docker_up seems to be daemon vs docker.
# We can ignore for now.

ib_connect.docker_run.local:
ifeq ($(IB_CONNECT_VNC_PASSWORD),)
	@echo "You need to provide IB_CONNECT_VNC_PASSWORD parameter. Example: 'IB_CONNECT_VNC_PASSWORD=12345 make ib_connect.docker_run.local'"
else
	IB_APP=$(IB_CONNECT_APP) \
	IMAGE=$(IB_CONNECT_LATEST_IMAGE) \
	TRUSTED_IPS=$(IB_CONNECT_TRUSTED_IPS) \
	VNC_PASSWORD=$(IB_CONNECT_VNC_PASSWORD) \
	API_PORT=$(IB_CONNECT_API_PORT) \
	VNC_PORT=$(IB_CONNECT_VNC_PORT) \
	docker-compose \
		-f devops/compose/docker-compose.local.yml \
    run --rm \
		-l user=$(USER) \
		-l app="ib_connect" \
		--service-ports \
		tws \
		/bin/bash
endif

# Run in detach mode.
ib_connect.docker_up.local:
ifeq ($(IB_CONNECT_VNC_PASSWORD),)
	@echo "You need to provide IB_CONNECT_VNC_PASSWORD parameter. Example: 'IB_CONNECT_VNC_PASSWORD=12345 make ib_connect.docker_up.local'"
else
	IB_APP=$(IB_CONNECT_APP) \
	IMAGE=$(IB_CONNECT_LATEST_IMAGE) \
	TRUSTED_IPS=$(IB_CONNECT_TRUSTED_IPS) \
	VNC_PASSWORD=$(IB_CONNECT_VNC_PASSWORD) \
	API_PORT=$(IB_CONNECT_API_PORT) \
	VNC_PORT=$(IB_CONNECT_VNC_PORT) \
	docker-compose \
	  -f devops/compose/docker-compose.local.yml \
		up \
		-d
endif

# Stop services.
ib_connect.docker_down.local:
	IB_APP=$(IB_CONNECT_APP) \
	IMAGE=$(IB_CONNECT_LATEST_IMAGE) \
	API_PORT=$(IB_CONNECT_API_PORT) \
	VNC_PORT=$(IB_CONNECT_VNC_PORT) \
	docker-compose \
		-f devops/compose/docker-compose.local.yml \
		down
