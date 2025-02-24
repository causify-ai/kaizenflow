im.run_convert_s3_to_sql_kibot.local:
	IMAGE=$(IM_IMAGE_DEV) \
	docker-compose \
		-f devops/compose/docker-compose.local.yml \
		run \
		--rm \
        app \
		im/app/transform/convert_s3_to_sql.py $(PARAMS)
