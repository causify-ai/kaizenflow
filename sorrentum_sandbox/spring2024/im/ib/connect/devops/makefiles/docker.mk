# Pull image from ECR.
ib_connect.docker_pull:
		$(foreach v, $(ID_CONNECT_RELATED_IMAGES), docker pull $(v); )


## #############################################################################
## Build.
## #############################################################################

# Build images.
# # --no-cache
#ib_connect.docker_build_image.rc:
#	DOCKER_BUILDKIT=0 \
#	docker build \
#		--progress=plain \
#		-t $(IB_CONNECT_RC_IMAGE) \
#		-t $(IB_CONNECT_RC_IMAGE_SHA) \
#		--file devops/docker_build/Dockerfile \
#		.

## Push release candidate images.
#ib_connect.docker_push_image.rc:
#	docker push $(IB_CONNECT_RC_IMAGE)
#	docker push $(IB_CONNECT_RC_IMAGE_SHA)
#
## Tag :rc image with :latest tag.
#ib_connect.docker_tag_latest.rc:
#	docker tag $(IB_CONNECT_RC_IMAGE) $(IB_CONNECT_LATEST_IMAGE)
#
## Push image with :latest tag.
#ib_connect.docker_push_image.latest:
#	docker push $(IB_CONNECT_LATEST_IMAGE)
#
## Tag :latest image with :prod tag.
#ib_connect.docker_tag_prod.latest:
#	docker tag $(IB_CONNECT_LATEST_IMAGE) $(IB_CONNECT_PROD_IMAGE)
#
## Push prod images.
#ib_connect.docker_push.prod_image:
#	docker push $(IB_CONNECT_PROD_IMAGE)
#
## Get docker logs.
#ib_connect.docker.logs:
#	docker logs compose_tws_1
