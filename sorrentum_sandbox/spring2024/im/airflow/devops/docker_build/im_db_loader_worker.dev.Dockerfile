# Build the Docker image for IM DB worker.

# TODO(gp): Move to im/airflow/devops/docker_build

FROM python:3.7-slim-buster

# TODO(*): Factor out all the code below which is common to all the Airflow workers.
ENV BITNAMI_PKG_CHMOD="-R g+rwX" \
    BITNAMI_PKG_EXTRA_DIRS="/opt/bitnami/airflow/dags" \
    HOME="/" \
    PATH="/opt/bitnami/python/bin:/opt/bitnami/postgresql/bin:/opt/bitnami/common/bin:/opt/bitnami/airflow/venv/bin:/opt/bitnami/nami/bin:$PATH"
COPY devops/airflow_worker/prebuildfs /
RUN apt update && \
        apt install \
            ca-certificates \
            curl \
            gzip \
            libbsd0 \
            libbz2-1.0 \
            libc6 \
            libcom-err2 \
            libedit2 \
            libffi6 \
            libgcc1 \
            libgmp10 \
            libgnutls30 \
            libgssapi-krb5-2 \
            libhogweed4 \
            libicu63 \
            libidn2-0 \
            libk5crypto3 \
            libkeyutils1 \
            libkrb5-3 \
            libkrb5support0 \
            libldap-2.4-2 \
            liblzma5 \
            libmariadb3 \
            libncursesw6 \
            libnettle6 \
            libp11-kit0 \
            libreadline7 \
            libsasl2-2 \
            libsqlite3-0 \
            libssl1.1 \
            libstdc++6 \
            libtasn1-6 \
            libtinfo6 \
            libunistring2 \
            libuuid1 \
            libxml2 \
            libxslt1.1 \
            locales \
            netbase \
            procps \
            sudo \
            tar \
            zlib1g -y
RUN /build/bitnami-user.sh
RUN /build/install-nami.sh
RUN bitnami-pkg install python-3.8.7-6 --checksum ceae8ee5c625cbb0a92534c3a8647ea8c7f65eb3cde2aff5e9615e6ac2e391d3
RUN bitnami-pkg install postgresql-client-10.16.0-0 --checksum 6ae2df74c4cc145690104c9bfbd4f9977cc00d26b3a010bb1eba74d92048485d
RUN bitnami-pkg install tini-0.19.0-1 --checksum 9b1f1c095944bac88a62c1b63f3bff1bb123aa7ccd371c908c0e5b41cec2528d
RUN bitnami-pkg install gosu-1.12.0-2 --checksum 4d858ac600c38af8de454c27b7f65c0074ec3069880cb16d259a6e40a46bbc50
RUN bitnami-pkg unpack airflow-worker-2.0.1-0 --checksum 51385a54b69847e91500a5a2dc8084556e9a75fe4feca007f79bb2e9818d9f3f
RUN localedef -c -f UTF-8 -i en_US en_US.UTF-8
RUN update-locale LANG=C.UTF-8 LC_MESSAGES=POSIX && \
    DEBIAN_FRONTEND=noninteractive dpkg-reconfigure locales
RUN echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen && locale-gen

COPY devops/airflow_worker/rootfs /
RUN /opt/bitnami/scripts/locales/add-extra-locales.sh
ENV AIRFLOW_DATABASE_HOST="postgresql" \
    AIRFLOW_DATABASE_NAME="bitnami_airflow" \
    AIRFLOW_DATABASE_PASSWORD="bitnami1" \
    AIRFLOW_DATABASE_PORT_NUMBER="5432" \
    AIRFLOW_DATABASE_USERNAME="bn_airflow" \
    AIRFLOW_DATABASE_USE_SSL="no" \
    AIRFLOW_EXECUTOR="SequentialExecutor" \
    AIRFLOW_FERNET_KEY="" \
    AIRFLOW_HOME="/opt/bitnami/airflow" \
    AIRFLOW_HOSTNAME_CALLABLE="" \
    AIRFLOW_REDIS_USE_SSL="no" \
    AIRFLOW_WEBSERVER_HOST="airflow" \
    AIRFLOW_WEBSERVER_PORT_NUMBER="8080" \
    AIRFLOW_WORKER_PORT_NUMBER="8793" \
    BITNAMI_APP_NAME="airflow-worker" \
    BITNAMI_IMAGE_VERSION="2.0.1-debian-10-r6" \
    C_FORCE_ROOT="True" \
    LANG="en_US.UTF-8" \
    LANGUAGE="en_US:en" \
    LD_LIBRARY_PATH="/opt/bitnami/python/lib/:/opt/bitnami/airflow/venv/lib/python3.8/site-packages/numpy.libs/:$LD_LIBRARY_PATH" \
    LIBNSS_WRAPPER_PATH="/opt/bitnami/common/lib/libnss_wrapper.so" \
    LNAME="airflow" \
    NAMI_PREFIX="/.nami" \
    NSS_WRAPPER_GROUP="/opt/bitnami/airflow/nss_group" \
    NSS_WRAPPER_PASSWD="/opt/bitnami/airflow/nss_passwd" \
    OS_ARCH="amd64" \
    OS_FLAVOUR="debian-10" \
    OS_NAME="linux" \
    REDIS_HOST="redis" \
    REDIS_PASSWORD="" \
    REDIS_PORT_NUMBER="6379" \
    REDIS_USER=""

# Worker specific section.
# This is copied from im/devops/docker_build/dev.Dockerfile
RUN apt-get update && \
    apt-get install gcc -y && \
    apt-get install python-dev -y && \
    apt-get install libpq-dev -y && \
    apt-get install postgresql-client -y && \
    apt-get purge gcc -y

# This is copied from im/devops/docker_build/dev.Dockerfile
COPY devops/docker_build/im_db_loader_worker.requirements.txt ./requirements.txt
RUN pip install -r /requirements.txt

WORKDIR /app

# Workaround to make work AWS CLI work.
# The rest of this workaround is in
# im/devops/docker_build/entrypoints/entrypoint_worker.sh
RUN echo "airflow     ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
RUN mkdir /home/airflow
RUN chown 1001:1001 /home/airflow

# To use as worker form the original Airflow recipe.
ENTRYPOINT [ "/app-entrypoint.sh" ]
CMD [ "/run.sh" ]
