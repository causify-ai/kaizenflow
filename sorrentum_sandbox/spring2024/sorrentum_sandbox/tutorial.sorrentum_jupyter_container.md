

<!-- toc -->

- [Sorrentum Jupyter container](#sorrentum-jupyter-container)
  * [Building the container](#building-the-container)
  * [Running Jupyter](#running-jupyter)
  * [Running bash](#running-bash)

<!-- tocstop -->

# Sorrentum Jupyter container

- We use Python and Jupyter for all the research projects

- IPython Notebook / Jupyter is an enhanced command shell for Python, that
  offers enhanced introspection, rich media, tab completion, and history
- IPython Notebook started as a web browser-based interface to IPython and
  proved especially popular with data scientists
- A few years ago, the Notebook functionality was forked off as a separate
  project, called [Jupyter](http://jupyter.org/). Jupyter provides support for
  many other languages in addition to Python

## Building the container

- Build with
  ```bash
  > docker_build.sh
  ```

## Running Jupyter

- We have built a `sorrentum_jupyter` container that allows to run Jupyter with
  all the needed dependencies

- To start Jupyter do:
  ```bash
  > cd $GIT_ROOT/sorrentum_sandbox/examples
  > docker_jupyter.sh
  ++ git rev-parse --show-toplevel
  + GIT_ROOT=/Users/saggese/src/sorrentum1
  + REPO_NAME=sorrentum
  + IMAGE_NAME=jupyter
  + FULL_IMAGE_NAME=sorrentum/jupyter
  + docker image ls sorrentum/jupyter
  REPOSITORY   TAG       IMAGE ID   CREATED   SIZE
  + CONTAINER_NAME=jupyter
  + docker run --rm -ti --name jupyter -p 8888:8888 -v /Users/saggese/src/sorrentum1/sorrentum_sandbox:/data sorrentum/jupyter /data/devops/jupyter_docker/run_jupyter.sh
  Unable to find image 'sorrentum/jupyter:latest' locally
  latest: Pulling from sorrentum/jupyter
  677076032cca: Already exists
  4c9de205ab0e: Pull complete
  ...
  7d1edc5584d3: Pull complete
  ac0e0cb28d27: Pull complete
  Digest: sha256:3be2a9bcbae4919d532d891d76ddb57cd8a13d0a8dd518cbdd5e7ed6ab3fa30a
  Status: Downloaded newer image for sorrentum/jupyter:latest
  + jupyter-notebook --port=8888 --no-browser --ip=0.0.0.0 --allow-root --NotebookApp.token= --NotebookApp.password=
  [I 16:29:44.061 NotebookApp] Writing notebook server cookie secret to /root/.local/share/jupyter/runtime/notebook_cookie_secret
  [I 16:29:44.061 NotebookApp] Authentication of /metrics is OFF, since other authentication is disabled.
  [W 16:29:44.273 NotebookApp] All authentication is disabled.  Anyone who can connect to this server will be able to run code.
  [I 16:29:44.276 NotebookApp] [jupyter_nbextensions_configurator] enabled 0.6.1
  [I 16:29:44.284 NotebookApp] Serving notebooks from local directory: /
  [I 16:29:44.284 NotebookApp] Jupyter Notebook 6.5.2 is running at:
  [I 16:29:44.284 NotebookApp] http://917f7e30d7c6:8888/
  [I 16:29:44.284 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
  ```

- This will start a Jupyter server in the container listening on port 8888
  - As discussed above, the Docker start command maps the 8888 port on the
    container to the 8888 port on the host
  - You can access it from the host, by pointing your browser to
    `localhost:8888` or `http://127.0.0.1:8888`

- Navigate to `/data` to see the directories mounted on Docker

- Now you can execute notebooks

## Running bash

- You can run bash in the Sorrentum Jupyter container with:
  ```bash
  > docker_bash.sh
  ```
