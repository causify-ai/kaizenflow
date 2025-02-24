# PyCharm

<!-- toc -->

- [Current situation](#current-situation)
- [How to run our cmamp container directly from PyCharm](#how-to-run-our-cmamp-container-directly-from-pycharm)
- [How to review a PR inside Pycharm](#how-to-review-a-pr-inside-pycharm)
- [How to edit remote code](#how-to-edit-remote-code)
- [General ssh config](#general-ssh-config)
- [DB connection via ssh](#db-connection-via-ssh)
- [Deployment with remote repository (through sync)](#deployment-with-remote-repository-through-sync)
- [PUDB - remote debugging - ToDo](#pudb---remote-debugging---todo)
- [How to run tests inside a container](#how-to-run-tests-inside-a-container)
- [Installing PyCharm Professional](#installing-pycharm-professional)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [Connecting via PyCharm gateway (SSH)](#connecting-via-pycharm-gateway-ssh)
  - [Connecting via VNC](#connecting-via-vnc)
- [Configuration](#configuration)
  - [Reflow](#reflow)
- [Some recommended plug-ins](#some-recommended-plug-ins)

<!-- tocstop -->
# Current situation
There are multiple ways to develop on a remote server using PyCharm

1.  VNC approach

    - PyCharm runs locally on the server using a "virtual screen"
    - Your laptop interacts with a VNC server to get the GUI locally
    - Pros:
      - Everything works
      - You can run anything like you are local on the server, since you are in
        practice just using a virtual screen
    - Cons:
      - Without enough bandwidth it's slow and not snappy enough

2.  X11 approach

    - Same as VNC, but instead of sending bitmaps through VNC, a "compressed"
      version of the GUI is sent to the local computer directly
    - Pros:
      - Maybe faster than VNC
      - PyCharm window is like a native window on your laptop
    - Cons:
      - X11 is old crap developed long time again and not really supported any
        more
      - One needs to tunnel X11 traffic, set things up, and so on

3.  PyCharm Gateway

    - New client-server architecture for PyCharm
      - A "headless" PyCharm runs on the server
      - A GUI client PyCharm runs on your laptop
    - Pros
      - It's as fast as possible, probably as fast as running locally
    - Cons
      - Need a PyCharm pro license (not a problem, we have money)
      - It's not super polished: kind of beta, but it will get better and better

4.  PyCharm Remote Set-up
    - This is described below in
      [PyCharm - Advanced tip and tricks](https://docs.google.com/document/d/1atNNMnmT6ZdIPSEtDaWZiBkL_fo5BHjPHy06He6zEZU/edit#heading=h.e0xo9fe70sks)
      - Edit locally and then PyCharm moves the files back and forth
    - Pros
      - Only requires ssh
    - Cons
      - You can't run / debug remotely

# Current situation

- Approach 1) seems to require lots of memory and CPU and it's not really fast.

- Approach 2) works but it's a pain to set-up and slow.

- We want to try with 3)
  - TODO(gp): @Juraj pls a short tutorial on how to install
  - TODO(gp): @Juraj understand if it works, if it's fast, and if it requires
    less memory

# How to run our cmamp container directly from PyCharm

- PyCharm allows to run commands directly inside a container
  - See
    [https://www.jetbrains.com/help/pycharm/using-docker-as-a-remote-interpreter.html](https://www.jetbrains.com/help/pycharm/using-docker-as-a-remote-interpreter.html)
- In fact when we do `i docker_bash` we launch a container and run bash inside
  it, but PyCharm can do the same thing

- TODO(gp): @Juraj Let's both try this. There are some notes below about it

# How to review a PR inside Pycharm

- CTRL + SHIFT + A -> View Pull Request

- <img src="figs/pycharm/image13.png" style="width:3.612198162729659in;height:4.932292213473316in" />

# How to edit remote code

- You need to use a certain local directory (e.g.,
  /Users/saggese/src/commodity_research1) and a remote directory (e.g.,
  /wd/saggese/src/commodity_research1)

- They need to be synced at the same git branch (e.g., master or
  AmpTask1112_Audit_amp_Docker_system_03)

- Set-up Deployment

<img src="figs/pycharm/image3.png" style="width:4.810558836395451in;height:3.51540791776028in" />

<img src="figs/pycharm/image10.png" style="width:3.9114588801399823in;height:1.6807655293088364in" />

- The deployment options are

<img src="figs/pycharm/image9.png" style="width:3.123700787401575in;height:2.78830271216098in" />

- You can see what file is changed in the file transfer window:

<img src="figs/pycharm/image14.png" style="width:6.5in;height:1.2083333333333333in" />

pycharm

- Develop on one node, sync, run on the server
- Run local application with venv

- Database

- Run application inside Docker

- Run application remotely inside Docker

# General ssh config

- File | Settings | Tools | SSH Configurations

  - <img src="figs/pycharm/image7.png" style="width:3.802863079615048in;height:1.4626399825021872in" />

- Once setup, ssh config can be used for all tools in PyCharm.

  - Remote Interpreter

  - DataGrip

  - Deployment

  - Etc.

# DB connection via ssh

Note: PyCharm Professional DataGrip is used as an example. There are numerous
open source alternatives such as [Beaver](https://dbeaver.io/). Config below
should apply to them also.

- To add a new data source in DataGrip, go to the database section in the lower
  left corner.

  - <img src="figs/pycharm/image4.png" style="width:2.7734372265966756in;height:2.7734372265966756in" />

- Then pick your desired data source from the dropdown in the upper right
  corner.

  - <img src="figs/pycharm/image6.png" style="width:4.164062773403325in;height:2.028646106736658in" />

- You will be presented with a dummy config that needs to be replaced with
  proper data as shown below.

  - <img src="figs/pycharm/image8.png" style="width:4.158922790901137in;height:3.0320844269466316in" />
  
- Before that is done, be sure that proper ssh info is added in SSH/SSL section.

  - <img src="figs/pycharm/image11.png" style="width:2.776042213473316in;height:0.598069772528434in" />

# Deployment with remote repository (through sync)

Note: Before setting up deployment, pull the cmamp repo on EC2 instance and use
the same name as on your local machine (example: cmamp1). Always try to keep
both repos in sync via git. For more subtle and simpler changes use File |
Reload All From Disk . This will upload changes to the remote repo.

- Tools | Deployment | Configuration

  - <img src="figs/pycharm/image1.png" style="width:4.893396762904637in;height:2.0781255468066493in" />

  - <img src="figs/pycharm/image12.png" style="width:4.838542213473316in;height:1.1398490813648294in" />
  
- Tools | Deployment | Options
  - <img src="figs/pycharm/image2.png" style="width:4.671411854768154in;height:3.2864588801399823in" />

    - Uncheck "Skip external changes" and check "Delete remote files"

- Tools | Deployment | Automatic Upload

  - Check it

- Tools | Deployment | Browse Remote Host
  - <img src="figs/pycharm/image5.png" style="width:5.394192913385827in;height:1.765625546806649in" />

# PUDB - remote debugging - ToDo

# How to run tests inside a container

- [https://www.jetbrains.com/help/pycharm/using-docker-compose-as-a-remote-interpreter.html#docker-compose-remote](https://www.jetbrains.com/help/pycharm/using-docker-compose-as-a-remote-interpreter.html#docker-compose-remote)

- Note that the "start SSH session..." action is available only in PyCharm
  Professional Edition, while the terminal itself is available in both
  Professional and Community editions.

# Installing PyCharm Professional

## Windows

1. Download the installer using this
   [link](https://www.jetbrains.com/pycharm/download/#section=windows)
2. Run the installer and follow the wizard steps.
3. To run PyCharm, find it in the Windows Start menu or use the desktop
   shortcut.

## macOS

There are separate disk images for Intel and Apple Silicon processors.

1. Download the image, based on your processor using this
   [link](https://www.jetbrains.com/pycharm/download/#section=mac)

2. Mount the image and drag the PyCharm app to the Applications folder.

3. Run the PyCharm app from the Applications directory, Launchpad, or Spotlight.

## Linux

**Using tar archives **

1. Download the tar archive using this
   [link](https://www.jetbrains.com/pycharm/download/#section=linux)

2. Unpack the pycharm-\*.tar.gz file to a different folder, if your current
   Download folder doesn't support file execution:

   ```
   > tar xzf pycharm-*.tar.gz -C <new_archive_folder>
   ``
   ```

The recommended installation location according to the filesystem hierarchy
standard (FHS) is `/opt`. To install PyCharm into this directory, enter the
following command:

```
> sudo tar xzf pycharm-\*.tar.gz -C /opt/
```

3. Switch to the **bin** subdirectory:

   ```
   > cd <new archive folder>/pycharm-\*/bin
   # E.g.,
   > cd /opt/pycharm-\*/bin
   ```

4. Run pycharm.sh from the bin subdirectory
   ```
   > sh pycharm.sh
   ```

**Using snap packages**

1. For Ubuntu 16.04 and later, you can use snap packages to install PyCharm.

   ```
   > sudo snap install pycharm-professional --classic
   # or
   > sudo snap install pycharm-community --classic
   ```

2. Run in the Terminalu
   ```
   > pycharm-professional
   # or
   > pycharm-community
   # or
   > pycharm-educational
   ```

# Connecting via PyCharm gateway (SSH)

The first thing you need to do is sign up for a free
[trial license](https://www.jetbrains.com/ru-ru/remote-development/gateway/) or
use it if it already have

Then make sure you have a VPN connection to our VPC

1.  Click on Connect via SSH
2.  Into Username: write <<yours_dev_server_username>> Example: richard
3.  Into Host: write <<dev_server_ip_address>> Example: 172.30.2.136
4.  Mark the Specify private key check box and locate the private key from the
    zip which was sent in the onboarding process. Example: crypto.pub
5.  Leave Port: 22 as it is.
6.  Click on Check Connection and Continue.
7.  Select IDE version: PyCharm Py 213.6777.x
8.  Locate your directory. Example: /data/richard
9.  Click on Download and Start IDE.

## Connecting via VNC

- Make sure you have a VPN connection.

**Installing VNC**

- Install VNC using this link:
  - [https://www.realvnc.com/en/connect/download/viewer/windows/](https://www.realvnc.com/en/connect/download/viewer/windows/)

Sysadmin has sent you:

- `os_password.txt`
- your username `$USER`
- a key `crypto.pub` that looks like:
  ```
  -----BEGIN OPENSSH PRIVATE KEY-----
  b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
  NhAAAAAwEAAQAAAYEA0IQsLy1lL3bhPT+43sht2/m9tqZm8sEQrXMAVtfm4ji/LXMr7094 ...
  hakqVTlQ2sr0YTAAAAHnNhZ2dlc2VAZ3BtYWMuZmlvcy1yb3V0ZXIuaG9tZQECAwQ=
  -----END OPENSSH PRIVATE KEY-----
  ```

Let's say you are connected via VNC.

1. Login into the OS.
2. Run pycharm.sh using terminal (should be there)

   ```
   > bash /opt/pycharm-community-2021.2.3/bin/pycharm.sh
   ```

# Configuration

## Reflow

- Set the reflow to reindent
  - <img src="figs/pycharm/image15.png" style="width:6.5in;height:4.486111111111111in" />

# Some recommended plug-ins

- vim
- Grazie
- [Wrap-to-column](https://plugins.jetbrains.com/plugin/7234-wrap-to-column)
- GitHub Copilot
