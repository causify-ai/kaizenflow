# Semgrep Integration in GitHub Actions

## Table of Contents

<!-- toc -->

- [Overview](#overview)
- [Features](#features)
- [Setup](#setup)
- [Exclusions](#exclusions)
  * [`.semgrepignore` File](#semgrepignore-file)
  * [Ignoring Specific Lines](#ignoring-specific-lines)
- [Notifications](#notifications)
- [Running Semgrep Locally](#running-semgrep-locally)
- [Additional Resources](#additional-resources)
- [Conclusion](#conclusion)

<!-- tocstop -->

## Overview

This document provides an overview and guidance on the integration of Semgrep, a
static analysis tool, into the GitHub Actions workflow. Semgrep is used for
identifying issues and vulnerabilities in the codebase automatically during the
development process.

## Features

- **Automatic Scanning**: Semgrep runs automatically on every pull request to
  the `master` branch and for every push to the `master` branch. This ensures
  that new code is checked before merging.
- **Scheduled Scans**: Additionally, Semgrep scans are scheduled to run once a
  day, ensuring regular codebase checks even without new commits.
- **Workflow Dispatch**: The integration allows for manual triggering of the
  Semgrep scan, providing flexibility for ad-hoc code analysis.

## Setup

- **GitHub Action Workflow**: The Semgrep integration is set up as a part of the
  GitHub Actions workflow in the [`semgrep.yml`](/.github/workflows/semgrep.yml)
  file.
- **Running Environment**: The workflow runs on `ubuntu-latest` and uses the
  `returntocorp/semgrep` container.
- **Semgrep Rules**: The current configuration uses the `p/secrets` rule pack
  from Semgrep, focusing on detecting secrets and sensitive information
  inadvertently committed to the repository.

## Exclusions

### `.semgrepignore` File

- To optimize the scanning process, a [`.semgrepignore`](/.semgrepignore) file
  is placed in the root directory. This file functions similarly to
  `.gitignore`, specifying files and paths that Semgrep should ignore during
  scans. This is useful for excluding third-party libraries, or any other
  non-relevant parts of the codebase from the scan.

### Ignoring Specific Lines

- To exclude a specific line of code from Semgrep analysis, append the comment
  `# nosemgrep` to the end of the line. This directive instructs Semgrep to
  bypass that particular line, allowing developers to suppress false positives
  or exclude non-relevant code snippets from analysis.

## Notifications

- **Failure Notifications**: In case of scan failures on the `master` branch, a
  Telegram notification is sent. This includes details such as the workflow
  name, repository, branch, event type, and a link to the GitHub Actions run.

## Running Semgrep Locally

To run Semgrep locally for testing before pushing your changes:

1. Install Semgrep on your local machine. Instructions can be found at
   [Semgrep Installation Guide](https://semgrep.dev/docs/getting-started/quickstart/).
2. Run `semgrep --config=p/secrets` in your project directory to execute the
   same rules as the CI/CD pipeline.

## Additional Resources

- For more details on Semgrep rules and usage, visit the
  [Semgrep Official Documentation](https://semgrep.dev/docs/).
- To understand GitHub Actions configuration, refer to the
  [GitHub Actions Documentation](https://docs.github.com/en/actions).

## Conclusion

The Semgrep integration into the GitHub Actions workflow provides an essential
layer of code quality and security checks, aligning with the commitment to
maintaining a robust and secure codebase.
