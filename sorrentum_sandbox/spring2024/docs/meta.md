

<!-- toc -->

- [Current dir structure](#current-dir-structure)
  * [Meta](#meta)
  * [Processes](#processes)
  * [Software components](#software-components)
  * [Papers](#papers)

<!-- tocstop -->

- `docs/meta.md`
  - This file contains rules and conventions for all the documentation under
    `docs`.

- `docs/all.code_organization.reference.md`
  - Describe how the code is organized in terms of components, libraries, and
    directories

- `docs/all.software_components.reference.md`
  - List of all the software components in the codebase

- `docs/all.workflow.explanation.md`
  - Describe all the workflows for quants, quant devs, devops

# Current dir structure

Please keep the directory in a conceptual order.

The current dir structure of `docs` is:

## Meta

- `documentation_meta`
  - How to write documentation for code and workflows.

## Processes

- `onboarding`
  - Practicalities of on-boarding new team members
  - All the info about something typically done only once at the beginning of
    employment should go here.

- `work_organization`
  - How the work is organized on a general level: the company’s adopted
    practices spanning coding and development.

- `work_tools`
  - How to set up, run and use various software needed for development (e.g.,
    IDE).

- `general_background`
  - Documents that provide general reference information, often across different
    topics (e.g., glossaries, reading lists).

- `coding`
  - Guidelines and good practices for coding and code-adjacent activities (such
    as code review)
  - This includes general tips and tricks that are useful for anybody writing
    any code (e.g., how to use type hints) as well as in-depth descriptions of
    specific functions and libraries.
  - TODO(gp): unclear what is the difference with `work_organization` and
    `work_tools`.
    - A proposal is:
      - `work_organization`: processes not related to coding
      - `coding`: any process related to only coding
      - `work_tools`: any tool (internal or external)

## Software components

- `kaizenflow`
  - Docs related to high-level packages that are used across the codebase (e.g.,
    `helpers`, `config`), as well as overall codebase organization.

- `datapull`
  - Docs related to dataset handling: downloading, onboarding, interpretation,
    etc.

- `dataflow`
  - Docs related to the framework of implementing and running machine learning
    models.

- `trade_execution`
  - Docs related to placing and monitoring trading orders to market or broker.

- `infra`
  - Docs related to the company’s infrastructure: AWS services, code deployment,
    monitoring, server administration, etc.

## Papers

- `papers`
  - Papers written by the team members about the company's products and
    know-how.
