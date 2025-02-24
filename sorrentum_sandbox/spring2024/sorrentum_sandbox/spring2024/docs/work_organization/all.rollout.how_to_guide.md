

<!-- toc -->

- [Roll-out process](#roll-out-process)
- [Roll-out documentation](#roll-out-documentation)
- [An example of roll-out email](#an-example-of-roll-out-email)

<!-- tocstop -->

# Roll-out process

- Implement
- Prepare documentation
- Dogfood by RPs or subset of target audience
- Initial roll-out
- Full rollout: Distribute it your team
- Deprecate the old system
  - The deadline is blah: do it!
  - Shut down from old

- File an Issue with the content of the email
  - The assignee is the person in charge of making sure the rollout is done
- Send an ORG email with the same content of the Issue

# Roll-out documentation

- A roll-out should address the following points:
  - Short summary
  - Who is the intended audience
  - What you need to do
  - Where is the reference documentation
  - What has changed
  - Why is it important
  - Whom to ask for help

# An example of roll-out email
```
Hello team,

## Intended audience

Anybody using Jupyter notebooks

## What it is about

- `publish_notebook.py` is a little tool that allows to:
  1. Opening a notebook in your browser (useful for read-only mode)
     - E.g., without having to use Jupyter notebook (which modifies the file in
       your client) or github preview (which is slow or fails when the notebook
       is too large)
  2. Sharing a notebook with others in a simple way
  3. Pointing to detailed documentation in your analysis Google docs
  4. Reviewing someone's notebook
  5. Comparing multiple notebooks against each other in different browser
     windows
  6. Taking a snapshot / checkpoint of a notebook as a backup or before making
     changes
     - This is a lightweight alternative to "unit testing" to capture the
       desired behavior of a notebook
     - One can take a snapshot and visually compare multiple notebooks
       side-by-side for changes

You can get details by running: `dev_scripts/notebooks/publish_notebook.py -h`

## What you need to do

Please update your branches from the `master` for all the submodules.

You can use our shortcut:

> make git_pull

## What has changed

We've deployed the new service for storing notebooks in HTML format. From now on
`publish_notebook.py` will work from the Docker container. The new version of
`publish_notebook.py` works using HTTP protocol and does not require ssh key
authorization as it was before We've synchronized all documents. So all old docs
already available on the new service The old links http://research:8077/...
won't work from now on, we need to replace them with the new ones
(http://notebook-keeper.p1/...) If you see any link starts with
http://research:8077 replace them with http://notebook-keeper.p1 .

## Reference documentation
//amp/docs/coding/all.publish_notebook.how_to_guide.md
```
