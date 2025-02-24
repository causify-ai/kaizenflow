## #############################################################################
## Production stage.
## #############################################################################

# Run ib connect app container.
IB_CONNECT_USER?=
IB_CONNECT_PASSWORD?=
IB_CONNECT_APP?=GATEWAY
IB_CONNECT_TRUSTED_IPS?=""
IB_CONNECT_VNC_PASSWORD?=
IB_CONNECT_API_PORT?=4004
IB_CONNECT_VNC_PORT?=5902
ib_connect.docker_run.prod:
ifeq ($(IB_CONNECT_VNC_PASSWORD),)
	@echo "You need to provide IB_CONNECT_VNC_PASSWORD parameter. Example: 'IB_CONNECT_VNC_PASSWORD=12345 make ib_connect.docker_run.prod'"
else ifeq ($(IB_CONNECT_USER),)
	@echo "You need to provide IB_CONNECT_USER parameter. Example: 'IB_CONNECT_USER=gp make ib_connect.docker_run.prod'"
else ifeq ($(IB_CONNECT_PASSWORD),)
	@echo "You need to provide IB_CONNECT_PASSWORD parameter. Example: 'IB_CONNECT_PASSWORD=12345 make ib_connect.docker_run.prod'"
else
	IB_APP=$(IB_CONNECT_APP) \
	TWSUSERID=$(IB_CONNECT_USER) \
	TWSPASSWORD=$(IB_CONNECT_PASSWORD) \
	TRUSTED_IPS=$(IB_CONNECT_TRUSTED_IPS) \
	VNC_PASSWORD=$(IB_CONNECT_VNC_PASSWORD) \
	IMAGE=$(IB_CONNECT_PROD_IMAGE) \
	API_PORT=$(IB_CONNECT_API_PORT) \
	VNC_PORT=$(IB_CONNECT_VNC_PORT) \
	docker-compose \
		-f devops/compose/docker-compose.prod.yml \
    run --rm \
		-l user=$(USER) \
		-l app="ib_connect" \
		--service-ports \
		tws \
		/bin/bash
endif

# Run in detach mode.
ib_connect.docker_up.prod:
ifeq ($(IB_CONNECT_VNC_PASSWORD),)
	@echo "You need to provide IB_CONNECT_VNC_PASSWORD parameter. Example: 'IB_CONNECT_VNC_PASSWORD=12345 make ib_connect.docker_up.prod'"
else ifeq ($(IB_CONNECT_USER),)
	@echo "You need to provide IB_CONNECT_USER parameter. Example: 'IB_CONNECT_USER=gp make ib_connect.docker_up.prod'"
else ifeq ($(IB_CONNECT_PASSWORD),)
	@echo "You need to provide IB_CONNECT_PASSWORD parameter. Example: 'IB_CONNECT_PASSWORD=12345 make ib_connect.docker_up.prod'"
else
	IB_APP=$(IB_CONNECT_APP) \
	TWSUSERID=$(IB_CONNECT_USER) \
	TWSPASSWORD=$(IB_CONNECT_PASSWORD) \
	TRUSTED_IPS=$(IB_CONNECT_TRUSTED_IPS) \
	VNC_PASSWORD=$(IB_CONNECT_VNC_PASSWORD) \
	IMAGE=$(IB_CONNECT_PROD_IMAGE) \
	API_PORT=$(IB_CONNECT_API_PORT) \
	VNC_PORT=$(IB_CONNECT_VNC_PORT) \
	docker-compose \
	  -f devops/compose/docker-compose.prod.yml \
		up \
		-d
endif

# Stop services.
ib_connect.docker_down.prod:
	IB_APP=$(IB_CONNECT_APP) \
	IMAGE=$(IB_CONNECT_PROD_IMAGE) \
	API_PORT=$(IB_CONNECT_API_PORT) \
	VNC_PORT=$(IB_CONNECT_VNC_PORT) \
	docker-compose \
		-f devops/compose/docker-compose.prod.yml \
		down
