# Code review
<!-- toc -->

- [General rules about code review](#general-rules-about-code-review)
  * [Read the Google code review best practices](#read-the-google-code-review-best-practices)
- [Code review workflows](#code-review-workflows)
  * [Pull request](#pull-request)
- [From the code author point of view](#from-the-code-author-point-of-view)
  * [Why we review code](#why-we-review-code)
  * [PR checklist](#pr-checklist)
  * [The golden rule of code review](#the-golden-rule-of-code-review)
  * [Be clear in the PR request about what you want](#be-clear-in-the-pr-request-about-what-you-want)
  * [Do not mix changes and refactoring / shuffling code](#do-not-mix-changes-and-refactoring--shuffling-code)
  * [Double check before sending a PR](#double-check-before-sending-a-pr)
  * [Reviewing other people's code is usually not fun](#reviewing-other-peoples-code-is-usually-not-fun)
  * [The first reviews are painful](#the-first-reviews-are-painful)
  * [Apply review comments everywhere](#apply-review-comments-everywhere)
  * [Look at the code top-to-bottom](#look-at-the-code-top-to-bottom)
  * [Answering comments after a review](#answering-comments-after-a-review)
  * [Apply changes to a review quickly](#apply-changes-to-a-review-quickly)
  * [Ask for another review](#ask-for-another-review)
  * [Workflow of a review in terms of GH labels](#workflow-of-a-review-in-terms-of-gh-labels)
  * [Link PR to GH issue](#link-pr-to-gh-issue)
  * [Fix later](#fix-later)
- [From the code reviewer point of view](#from-the-code-reviewer-point-of-view)
  * [Post-commit review](#post-commit-review)
  * [Code walk-through](#code-walk-through)
  * [Close the PR and delete the branch](#close-the-pr-and-delete-the-branch)
  * [Give priority to code review](#give-priority-to-code-review)
  * [Multiple reviewers problem](#multiple-reviewers-problem)
  * [Remember "small steps ahead"](#remember-small-steps-ahead)
  * [Nothing is too small](#nothing-is-too-small)
  * [Final GH comment](#final-gh-comment)

<!-- tocstop -->

# General rules about code review

## Read the Google code review best practices

- From the
  [developer\'s perspective](https://google.github.io/eng-practices/review/developer)

- From the
  [reviewer\'s perspective](https://google.github.io/eng-practices/review/reviewer)

- Where the Google guide says "CL", think "PR"

- Read it (several times, if you need to)

- Think about it

- Understand the rationale

# Code review workflows

## Pull request

- Our usual review process is to work in a branch and create a pull request
  - See the
    [Git](https://docs.google.com/document/u/0/d/1zahC8uDnFGYRSgkBrQRgg3W3ZmDjZZJj6yln6YeuHq4/edit)
    notes for details
  - The name of the pull request is generated with ghi_show.py and looks like
    PTask2704 make exchange contracts get contracts applicable to series

# From the code author point of view

## Why we review code

- We spend time reviewing each other code so that we can:
  - Build a better product, by letting other people look for bugs
  - Propagate knowledge of the code base through the team
  - Learn from each other

## PR checklist

- From
  [Google reviewer checklist](https://google.github.io/eng-practices/review/reviewer/looking-for.html):

- In asking (and doing) a code review, you should make sure that:
  - The code is well-designed.
  - The functionality is good for the users of the code.
  - The code isn't more complex than it needs to be.
  - The developer isn't implementing things they might need in the future but
    don't know they need now.
  - Code has appropriate unit tests.
  - Tests are well-designed.
  - The developer used clear names for everything.
  - Comments are clear and useful, and mostly explain why instead of what.
  - Code is appropriately documented.
  - The code conforms to our style guides.

## The golden rule of code review

- Make life easy for the reviewers
  - Aka "Do not upset the reviewers, otherwise they won't let you merge your
    code"

- Remember that reviewing other people's code is hard and unrewarding work
  - Do your best for not frustrating the reviewers

- If you are in doubt "it's probably clear, although I am not 100% sure", err on
  giving more information and answer potential questions

## Be clear in the PR request about what you want

- Summarize what was done in the PR
  - Refer to the GH task, but the task alone might not be sufficient
  - A PR can implement only part of a complex task
    - Which part is it implementing?
    - Why is it doing it in a certain way?

- If the code is not ready for merge, but you want a "pre-review" convert PR to a draft
  - E.g., ask for an architectural review
  - Draft PRs can not be merged

- Is it blocking?
  - Do not abuse asking for a quick review
  - All code is important and we do our best to review code quickly and
    carefully
  - If it\'s blocking a ping on IM is a good idea

## Do not mix changes and refactoring / shuffling code

- The job of the reviewers become frustrating when the author mixes:
  - Refactoring / moving code; and
  - Changes

- It is time consuming or impossible for a reviewer to understand what happened:
  - What is exactly changed?
  - What was moved where?

- In those cases reviewers have the right to ask the PR to be broken in pieces

- One approach for the PR author is to:
  - Do a quick PR to move code around (e.g., refactoring) or purely cosmetic
    - You can ask the reviewer to take a quick look
  - Do the next PRs with the actual changes

- Another approach is to develop in a branch and break the code into PRs as the
  code firms up
  - In this case you need to be very organized and be fluent in using Git: both
    qualities are expected of you
  - E.g., develop in a branch (e.g., `gp_scratch`)
  - Create a branch from it (e.g., `TaskXYZ_do_this_and_that`) or copy the files
    from `gp_scratch` to `TaskXYZ_do_this_and_that`
  - Edit the files to make the PR self-consistent
  - Do a PR for `TaskXYZ_do_this_and_that`
  - Keep working in gp_scratch while the review is moving forward
  - Make changes to the `TaskXYZ_do_this_and_that` as requested
  - Merge `TaskXYZ_do_this_and_that` to master
  - Merge `master` back into `gp_scratch` and keep moving

## Double check before sending a PR

- After creating a PR take a look at it to make sure things look good, e.g.,
  - Are there merge problems?
  - Did you forget some file?
  - Skim through the PR to make sure that people can understand what you changed

## Reviewing other people's code is usually not fun

- Reviewing code is time-consuming and tedious
  - So do everything you can to make the reviewer's job easier
  - Don't cut corners

- If a reviewer is confused about something, other readers (including you in 1
  year) likely would be too
  - What is obvious to you as the author is often not obvious to readers
  - Readability is paramount
  - You should abhor write-only code

## The first reviews are painful

- One needs to work on the same code over and over
  - Just think about the fact that the reviewer is also reading (still crappy)
    code over and over

- Unfortunately it is needed pain to get to the quality of code we need to make
  progress as a team

## Apply review comments everywhere

- Apply a review comment everywhere, not just where the reviewer pointed out the
  issue

- E.g., reviewer says:
  - "Please replace `_LOG.warning("Hello %s".format(name))` with `_LOG.warning("Hello %s", name)`"
- You are expected to do this replacement:
  - In the current review
  - In all future code you write
  - In old code, as you come across it in the course of your work
    - Of course don't start modifying the old code in this review, but open a
      clean-up bug, if you need a reminder

## Look at the code top-to-bottom

- E.g., if you do a search & replace, make sure everything is fine

## Answering comments after a review

- It's better to answer comments in chunks so we don't get an email per comment
  - Use "start a review" (not in conversation)
- If one of the comment is urgent (e.g., other comments depend on this) you can
  send it as single comment
- When you answer a comment, mark it as resolved

## Apply changes to a review quickly

- In the same way the reviewers are expected to review PRs within 24 hours, the
  author of a PR is expected to apply the requested changes quickly, ideally in
  few hours
  - If it takes longer, then either the PR was too big or the quality of the PR
    was too low

- If it takes too long to apply the changes:
  - The reviewers (and the authors) might forget what is the context of the
    requested changes
  - It becomes more difficult (or even impossible) to merge, since the code base
    is continuously changing
  - It creates dependencies among your PRs
  - Remember that you should not be adding more code to the same PR, but only
    fix the problems and then open a PR with new code
  - Other people that rely on your code are blocked

## Ask for another review

- Once you are done with resolving all the comments ask for another review

## Workflow of a review in terms of GH labels

- The current meaning of the labels are:
  - See GitHub ZenHub workflows [doc](https://github.com/cryptokaizen/cmamp/blob/master/docs/work_organization/all.use_github_and_zenhub.how_to_guide.md#pr-labels)

## Link PR to GH issue

- Mention the corresponding issue in the PR description to ease the navigation
E.g., see an [example](https://github.com/kaizen-ai/kaizenflow/pull/288#issue-1729654983)

## Fix later

- It's ok for an author to file a follow up Issue (e.g., with a clean up), by
  pointing the new Issue to the comments to address, and move on with merge

- The Issue needs to be addressed immediately after

# From the code reviewer point of view

## Post-commit review

- You can comment on a PR already merged

- You can comment on the relevant lines in a commit straight to `master` (this
  is the exception)

## Code walk-through

- It is best to create a branch with the files you want to review
  - Add TODOs in the code (so that the PR will pick up those sections)
  - File bugs for the more involved changes

- Try to get a top to bottom review of a component once every N weeks (N = 2, 3)
  - Sometimes the structure of the

## Close the PR and delete the branch

- When code is merged into master by one of the reviewers through the UI one can
  select the delete branch option

- Otherwise you can delete the branch using the procedure in 
[Git](https://docs.google.com/document/u/0/d/1zahC8uDnFGYRSgkBrQRgg3W3ZmDjZZJj6yln6YeuHq4/edit)

## Give priority to code review

- We target to give feedback on a PR within 24hr so that the author is not
  blocked for too long
  - Usually we respond in few hours

## Multiple reviewers problem

- When there are multiple reviewers for the same PR there can be some problem

- Ok to keep moving fast and avoid blocking
  - Block only if it is controversial

- Merge when we are confident that the other is ok
  - The other can catch up with post-commit review
  - A good approach is to monitor recently merged PRs in GH to catch up

## Remember "small steps ahead"

- Follow the Google approach of merging a PR that is a strict improvement.

## Nothing is too small

- Each reviewer reviews the code pointing out everything that can be a problem

- Problems are highlighted even if small or controversial
  - Not all of those comments might not be implemented by the author

- Of course if different approaches are really equivalent but reviewers have
  their own stylistic preference, this should not be pointed, unless it's a
  matter of consistency or leave the choice to the author

## Final GH comment

- Once you are done with the detailed review of the code, you need to
  - Write a short comment
  - Decide what is the next step for the PR, e.g.,
    - Comment
      - Submit general feedback without explicit approval
    - Approve
      - Submit feedback and approve merging these changes
    - Request changes
      - Submit feedback that must be addressed before merging

- We use an integrator / developer manager workflow, initially with Paul and GP
  testing and merging most of the PRs

- We use the 3 possible options in the following way:
  - Comment
    - When reviewers want the changes to be applies and then look at the
      resulting changes to decide the next steps
    - In practice this means "make the changes and then we'll discuss more"
    - E.g., this is of course the right choice for a pre-PR
  - Approve
    - No more changes: time to merge!
    - Often it is accompanied with the comment "LGMT" (Looks Good To Me)
  - Request changes
    - This typically means "if you address the comments we can merge"
    - In practice this is more or less equivalent to "Comment"
