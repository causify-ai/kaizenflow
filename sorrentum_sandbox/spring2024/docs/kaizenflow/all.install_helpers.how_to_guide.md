

<!-- toc -->

- [Helpers Distribution Package](#helpers-distribution-package)
- [Creating and installing the package](#creating-and-installing-the-package)
  * [PyPI local file](#pypi-local-file)
  * [PyPI workflow](#pypi-workflow)
- [PyPI server installation](#pypi-server-installation)
  * [General Information](#general-information)
  * [Client Configuration / Installation](#client-configuration--installation)
  * [Server Details](#server-details)
  * [Server Configuration](#server-configuration)
  * [Limitation](#limitation)
  * [Links](#links)
- [Code organization in `helpers`](#code-organization-in-helpers)

<!-- tocstop -->

# Helpers Distribution Package

- This document describes how to build, distribute and install the `helpers`
  package

- Note for dev/data science members: if you are looking for how to install
  packages for your daily work, go to **Client Configuration**.

# Creating and installing the package

## PyPI local file

- You can create the `helpers` package with:

  ```bash
  > cd helpers
  > python setup.py bdist_wheel
  ```

- This creates a file `dist/helpers-1.0.0-py3-none-any.whl` that contains the
  package

- You can install the package with:
  ```
  > python -m pip install dist/helpers-1.0.0-py3-none-any.whl
  ```

## PyPI workflow

- This section describes a temporary solution while we build the CI pipeline.

- The maintainer of `helpers` package after merging changes of `helpers/` into
  `master`, should run:

1. Edit or create a `~/.pypirc` file with:

   ```ini
   [distutils]
   index-servers =
   part
   [part]
   username:<upload_pypi_username>
   password:<upload_pypi_passwd>
   ```

2. Update the `helpers/CHANGELOG` and add version

3. Edit `setup.py`, changing `version` in accordance in `CHANGELOG`, update
   `install_requires` parameters.

4. Run `python setup.py sdist upload -r part`

# PyPI server installation

## General Information

- We use [pypiserver](https://github.com/pypiserver/pypiserver) as a corporate
  PyPI Index server for installing `pip`
- It implements the same interfaces as [PyPI](https://pypi.org/), allowing
  standard Python packaging tooling such as `pip` to interact with it as a
  package index just as they would with [PyPI](https://pypi.org/)
- The server is based on bottle and serves packages from regular directories
- Wheels, bdists, eggs can be uploaded either with `pip`, `setuptools` or simply
  copied with `scp` to the server directory

## Client Configuration / Installation

You have two options:

1. Since `pypiserver` redirects `pip install` to the pypi.org index if it
   doesn't have a requested package, it is a good idea to configure them to
   always use your local pypi index.

- For pip command this can be done by setting the environment variable
  `PIP_EXTRA_INDEX_URL`

  ```bash
  > export PIP_EXTRA_INDEX_URL=http://172.31.36.23:8855/simple/
  ```

  or by adding the following lines to `~/.pip/pip.conf`:

  ```ini
  [global]
  extra-index-url = http://172.31.36.23:8855/simple/
  trusted-host = 172.31.36.23
  ```

2. Manual installation:

   ```bash
   > pip install --extra-index-url http://172.31.36.23:8855/simple --trusted-host 172.31.36.23 helpers
   ```

   or

   ```bash
   > pip install --extra-index-url http://172.31.36.23:8855 helpers
   ```

- Search hosted packages:

  ```bash
  > pip search --index http://172.31.36.23:8855 ...
  ```

- **Note** that pip search does not currently work with the /simple/ endpoint.

## Server Details

**Simple Index WebUI**: http://172.31.36.23:8855/simple

**Host**: ubuntu@172.31.36.23

**Runtime**: by docker (standalone container)

## Server Configuration

- The corporate PyPI Index server runs with Docker as a standalone container
  with mapped volumes on the host.

- All corporate packages serve from host directory: `/home/ubuntu/pypi/packages`

- Uploading a new packages or updates existing packages password-protected. Only
  authorized user can upload packages. Authorized user credential serves from
  host Apache-Like authentication file: `/home/ubuntu/pypi/.htpasswd`.

- Credential details you can find on the server in a file `~/.pypi_credentials`

- To serve packages and authenticate against local `.htpasswd`:

  ```bash
  > docker run -d -p 8855:8080 -v ~/pypi/packages:/data/packages -v ~/pypi/.htpasswd:/data/.htpasswd --restart=always pypiserver/pypiserver:latest -v  -P .htpasswd packages
  ```

## Limitation

- The `pypiserver` does not implement the full API as seen on
  [PyPI](https://pypi.org/). It implements just enough to make `pip install`,
  and `search` work.

## Links

- [pip user guide](https://pip.pypa.io/en/stable/user_guide/#user-guide)
- [pypiserver](https://github.com/pypiserver/pypiserver)
- [setuptool](https://setuptools.readthedocs.io/en/latest/index.html)
- [packaging python projects](https://packaging.python.org/tutorials/packaging-projects/)

# Code organization in `helpers`

- In `helpers` the following hierarchy should be respected:

  - `repo_config.py`
  - `hwarnings`, `hserver`, `hlogging`
  - `hdbg`
  - `hintrospection`, `hprint`
  - `henv`, `hsystem`, `hio`, `hversio`
  - `hgit`

- A library should only import libs that precede it or are on the same level in
  the hierarchy above.
  - E.g. `henv` can import `hdbg`, `hprint` and `hio`, but it cannot import
    `hgit`.
  - While importing a lib on the same level, make sure you are not creating an
    import cycle.
- For more general infomation, see
  [all.imports_and_packages.how_to_guide.md](https://github.com/cryptokaizen/cmamp/blob/master/docs/coding/all.imports_and_packages.how_to_guide.md).
