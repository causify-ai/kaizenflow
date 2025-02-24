

<!-- toc -->

- [DATA605 Class Projects](#data605-class-projects)
  * [Choosing a project](#choosing-a-project)
  * [Working](#working)
  * [Pre-requisites](#pre-requisites)
  * [Project assignment](#project-assignment)
    + [Documentation](#documentation)
    + [Submitting project](#submitting-project)
  * [Example of a class project](#example-of-a-class-project)

<!-- tocstop -->


# DATA605 Class Projects

- The goal of the class project is to learn cutting-edge modern big data
  technology and write a (small) example of a system using it
- Each class project is similar in spirit to the tutorials for various
  technologies (e.g., Git, Docker, SQL, Mongo, Airflow, Dask) we have looked and
  studied in classes

## Choosing a project

- Each student should pick one of the projects from the signup sheet
  - The difficulty of the project does affect the final grade, but we want to
    give a way for everyone to select a project based on their level of computer
    literacy
  - You will need to give us some information including your GitHub name so we
    can add you to the repo

- The project is individual
  - Students can discuss and help each other (they will do that even if we say
    not to)
  - Students should not have exactly the same project
  - If there are no more projects left for any reason, then we will add more

- The goal is to get your hands dirty and figure things out
  - Often working is all about trying different approaches until one works out
  - Google and ChatGPT are your friends, but don't abuse them: copy-pasting
    without understanding doesn't help you
  - Make sure you understand what, how, and why a piece of code does
 
- On the sign-up sheet, you will find several baseline project proposals
  suggested by us. You can either choose from the given projects or propose your
  own project. You can improve, change, and add other technologies and components
  to enhance your project
- Your project choice should align with your learning goals and interests,
  presenting an excellent opportunity to explore various technologies and enhance
  your resume.


- If you choose one of the projects from the sign-up sheet, fill out the
  corresponding information promptly. If you decide to propose a modification,
  send us an email with the desired information and we will update the sign-up
  sheet and Google Doc for you.

- Please note that you are required to finalize your project selection within
  one week
- The project duration is approximately four weeks, so timely selection is
  crucial for effective planning and execution.

- Your grades will be influenced by factors such as project complexity, your
  efforts and understanding, and adherence to given project guidelines.

## Working

- You will work in the same way open-source developers (and specifically
  developers on Sorrentum) contribute to a project

- Each step of the project is delivered by committing code to your dir
  corresponding to your project (more below) and doing a GitHub Pull Request
  (PR)
  - You can / should commit regularly and not only once at the end
  - This allows us to review intermediate results and give you feedback (like
    companies adopting an Agile methodology do)
- We will do a review of the project in the middle of the project and give you
  some feedback on what to improve

- You can model your working setup after contributors to Sorrentum
  https://github.com/sorrentum/sorrentum/blob/master/docs/onboarding/sorrentum.set_up_development_environment.how_to_guide.md

## Pre-requisites

- Watch, star, and fork the Sorrentum repo
- Install Docker on your computer
  - Ok to use Docker natively on Mac and Linux
  - Use VMware in Windows
    - If you have problems installing it on your laptop, use one computer from
      UMD or your friends
- After signing up for a project accept the invitation to collaborate sent to the
  email that you used to register your GitHub account, or check
  [here](https://github.com/sorrentum/sorrentum/invitations)
- Check your GitHub issue on https://github.com/sorrentum/sorrentum/issues
  - Make sure you are assigned to it

## Project assignment

- Each project requires the following steps
  - Create a Docker container installing all the needed tools (e.g., Redis and
    `redis-py`)
  - You should use Docker Compose to build single or multi-container systems
  - Jupyter notebook (if possible), otherwise a Python script implementing the
    project
  - Only Python3 on Linux/Mac should be used
  - You can always communicate with the tech using Python libraries or HTTP APIs

- Only Python should be used together with the needed configs for the specific
  tools
- Everything needs to run locally: no project should use cloud resources
  - E.g., it's not ok to use an AWS DB instance, you want to install Postgres in
    your container
- Make sure there is a way of building your project with Python, Docker

### Documentation

- Write a 5 to 10-page report in markdown covering your project
  - At least 1 page (60 lines): short description of the technology used (e.g.,
    Redis), e.g.,
    - What it does
    - Why it's different than other technologies solving a similar problem
    - Pros and cons of their approach
    - Relate it to what we have studied in class
    - Cite sources of where you have found this info
    - ...
  - At least 1 page (60 lines): describe and explain the logic of the Docker
    system that you have built, e.g.,
    - The Dockerfile should be commented
    - Explain the decision you have made
    - What are the containers involved
    - How they communicate
    - ...
  - At least 1 page (60 lines): explain how to run the system by starting the
    container system, e.g.,
    - Report command lines
    - How the output looks like
    - ...
  - At least 3 pages (60 lines): describe exactly what you have done
    - Describe the script/notebook with examples of the output
    - Use diagrams (e.g., use `mermaid`)
    - Describe the schema used in the DB
    - ...

- The script/notebook should be able to run end-to-end without errors, otherwise
  the project is not considered complete
  - We are not going to debug your code
  - If there are problems we will use the GitHub issue to communicate and we
    expect you to fix the problem

### Submitting project

- Each project will need to be checked in
  https://github.com/sorrentum/sorrentum, filing bugs, with PRs, etc like in an
  open source project

- The tag of your projects follows the schema
  `Spring{year}_{project_title_without_spaces}`
  - E.g., if the project title is "Redis cache to fetch user profiles", the tag
    is `Spring2024_Redis_cache_to_fetch_user_profiles`

- Create a GitHub issue with the project tag (e.g.,
  `Spring2024_Redis_cache_to_fetch_user_profiles`) and assign the issue to
  yourself
  - Copy/paste the description of the project and add a link to the Google doc
    with the description
  - We will use this issue to communicate as the project progresses

- Create a branch in Git named after your project
  - E.g., `SorrTask645_Redis_cache_to_fetch_user_profiles`
  ```
  > cd $HOME/src
  > git clone git@github.com:sorrentum/sorrentum.git sorrentum1
  > cd $HOME/src/sorrentum1
  > git checkout master
  > git checkout -b SorrTask645_Redis_cache_to_fetch_user_profiles
  ...
  ```

- You should add files only under the directory corresponding to your project
  which is like `{GIT_ROOT}/sorrentum_sandbox/projects/{project_tag}`
  - E.g., on the dir cloned on my laptop the dir is named
    `~/src/sorrentum1/sorrentum_sandbox/projects/SorrTask645_Redis_cache_to_fetch_user_profiles`

- You always need to create a PR from your branch and add your TA and
  `gpsaggese` as reviewers
  - Remember you can't push directly to `master`
  - You can only push code to your branch

- Copy the files from the template project to your project

  ```bash
  > cd $GIT_ROOT
  > cp -r sorrentum_sandbox/projects/project_template sorrentum_sandbox/projects/{project_tag}
  > git add sorrentum_sandbox/projects/{project_tag}
  ```

- You can use consecutive branch and PR names as you make progress
  - E.g., `SorrTask645_Redis_cache_to_fetch_user_profiles_1`,
    `SorrTask645_Redis_cache_to_fetch_user_profiles_2`, ...

## Examples of a class project

- The layout of each project should follow the example in
  https://github.com/sorrentum/sorrentum/tree/master/sorrentum_sandbox/projects/spring2024/SorrTask645_Redis_cache_to_fetch_user_profiles
- Examples for Binance and Reddit in
  https://github.com/sorrentum/sorrentum/tree/master/sorrentum_sandbox/examples
- Projects from 2023
  https://github.com/sorrentum/sorrentum/tree/master/sorrentum_sandbox/spring2023
- The tutorials from DATA605 class
