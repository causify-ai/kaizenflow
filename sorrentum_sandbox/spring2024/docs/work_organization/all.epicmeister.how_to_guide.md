# EpicMeister Process

<!-- toc -->

- [General](#general)
- [Responsibilities](#responsibilities)
  * [Epic Management](#epic-management)
  * [Issue Organization](#issue-organization)

<!-- tocstop -->

# General

- EpicMeister ensures that Epics and issues are well-organized and updated,
  providing the team with a clear overview of project progress and priorities
- By assigning Epics to an issue, the EpicMeister establishes a clear
  relationship between the larger project goals and the specific tasks,
  facilitating a holistic view of project progress and alignment
- Refer to this [doc](https://github.com/cryptokaizen/cmamp/blob/master/docs/work_organization/all.use_github_and_zenhub.how_to_guide.md) to have a clear
  understanding of the workflow using GitHub and ZenHub

# Responsibilities

## Epic Management

- Keep this [document](https://github.com/cryptokaizen/cmamp/blob/master/docs/work_organization/all.use_github_and_zenhub.how_to_guide.md#list-of-epics) that lists
  all existing Epics updated
- When a new Epic is required, after discussion
  - Create it within ZenHub
    - Make sure the Epics are alphabetically organized on the ZenHub by right-click
      and select to sort them
  - Update the [document](https://github.com/cryptokaizen/cmamp/blob/master/docs/work_organization/all.use_github_and_zenhub.how_to_guide.md)
  - Provide a concise title that reflects the nature of the Epic
  - Craft a description that outlines the goals and scope of the Epic
- Every two weeks create a checklist of the team members in
  [this](https://github.com/cryptokaizen/cmamp/issues/5668) issues to make sure team
  members are cleaning up the board.

## Issue Organization

- Ensure that all Issues in GitHub/ZenHub are well-organized
- Each Issue should:
  - Be associated with an Epic
  - Have an assigned to a team member (Assignee)
  - Be in the appropriate pipeline
  - Estimate has been set properly
- Review the board once every week (ideally before the Sprint retrospective on
  Friday) to make sure everyone follows the procedure
- Ping the team members to follow the procedure if they are not following
  - Responsibilities of the Issue Creator
    - Write well-defined specs
    - Assign it to the team member
    - Assign a pipeline to the issue when defined (e.g., `Sprint Backlog (P0)`,
      `Product backlog (P1)`)
    - Add an Epic to the issue
    - Add it to the sprint
  - Responsibilities of the Assignee
    - Make sure the specs are clear and well-defined
    - Make sure all the required fields are filled out by the creator
    - Assign an estimate to the issue
    - Make sure to change the pipeline as the progress is made
- Before closing an issue, confirm that it is associated with a relevant Epic
  and all the required fields are filled out. If not, ping/guide the creator to
  link the issue appropriately
