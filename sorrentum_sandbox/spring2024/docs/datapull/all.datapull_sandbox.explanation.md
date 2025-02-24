## Sandbox

This paragraph describes an example of infrastructure that implements the
`DataPull` protocol.

It is implemented as a Docker Container containing the following services:
- Airflow
- Jupyter notebook
- Postgres
- MongoDB

- It is a separated code base from CK and it shares only a few base library
  (e.g., `helpers`)

- It is a scaled down version of CK production infrastructure (e.g., managed
  Airflow is replaced by a local Airflow instance)
