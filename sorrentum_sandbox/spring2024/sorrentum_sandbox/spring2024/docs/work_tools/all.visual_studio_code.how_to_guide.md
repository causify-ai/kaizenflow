# Visual Studio Code

<!-- toc -->

- [Connecting via VNC](#connecting-via-vnc)
  * [Installing VNC](#installing-vnc)
- [Installation of VS Code](#installation-of-vs-code)
  * [Windows, Linux, Mac](#windows-linux-mac)
- [How to run a VSCode debugger within a remote container](#how-to-run-a-vscode-debugger-within-a-remote-container)
  * [Prerequisites](#prerequisites)
  * [Tips](#tips)
  * [Steps](#steps)

<!-- tocstop -->

# Connecting via VNC

- Make sure you have a VPN connection.

## Installing VNC

- Install VNC using this link: [<span
  class="underline">https://www.realvnc.com/en/connect/download/viewer/windows/</span>](https://www.realvnc.com/en/connect/download/viewer/windows/)
- Sysadmin has sent you:

  - `os_password.txt`
  - your username `$USER`
  - a key `crypto.pub` that looks like:

    ```
    -----BEGIN OPENSSH PRIVATE KEY-----
    b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn
    NhAAAAAwEAAQAAAYEA0IQsLy1lL3bhPT+43sht2/m9tqZm8sEQrXMAVtfm4ji/LXMr7094
    …
    hakqVTlQ2sr0YTAAAAHnNhZ2dlc2VAZ3BtYWMuZmlvcy1yb3V0ZXIuaG9tZQECAwQ=
    -----END OPENSSH PRIVATE KEY-----
    ```

- Let's say you are connected via VNC.

  - Login into the OS.
  - Run `pycharm.sh` using terminal (should be there):

    ```
    > bash /opt/pycharm-community-2021.2.3/bin/pycharm.sh
    ```

# Installation of VS Code

## Windows, Linux, Mac

- Download the installer using this link:
  [<span class="underline">Download Visual Studio Code - Mac, Linux, Windows</span>](https://code.visualstudio.com/download).
- Run the installer and follow the wizard steps.
- To run VS Code, find it in the **Start** menu or use the desktop shortcut.
- In the left navigation bar search for extensions ( or use `Ctrl+Shift+X` ) and
  search for "ms-vscode-remote.remote-ssh" and then click on the install button.
  <img src="figs/visual_studio_code/image8.png" style="width:3.13386in;height:1.49306in" />
- Connect to the VPN.
- In bottom left corner click on this green button:
  <img src="figs/visual_studio_code/image3.png" style="width:0.45313in;height:0.41827in" />
- Then you will see these options on top of the screen, click on "Open SSH
  Configuration File…" and then click on the `user\.ssh\config` or
  `user/.ssh/config`.
  <img src="figs/visual_studio_code/image6.png" style="width:4.04688in;height:0.71944in" />
- The config should look like this:
  <img src="figs/visual_studio_code/image7.png" style="width:6.26772in;height:2.59722in" />
  - `HostName`: dev1 (or dev2) server IP.
  - `User`: your linux user name on the dev server.
  - `IdentityFile`: private key that you use to `SSH` to the dev server.
- Save and close the config file and press the green button again, then for
  connection click on "Connect to Host...". You should see the IP address of the
  server, so just click on it and it will connect you in a new window.
- Open a preferred repo directory.
  - Click on the "Source control" button on the left:
    <img src="figs/visual_studio_code/image4.png" style="width:0.41667in;height:0.48958in" />
  - Choose "Open Folder":
    <img src="figs/visual_studio_code/image1.png" style="width:2.47917in;height:1.59375in" />
  - Choose the desired repo directory from the drop-down menu, e.g., `cmamp1`:
    <img src="figs/visual_studio_code/image5.png" style="width:2.5in;height:1.44792in" />

# How to run a VSCode debugger within a remote container

The goal is to successfully run a Visual Studio Code (VSCode) debugger on code
that runs within a docker container located on a remote server.

## Prerequisites

- Mac OS or Linux-based OS

- Visual Studio Code installed on the local machine you are working from

- VSCode extensions installed:

  - [<span
    class="underline">Python</span>](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
    (Installed on the remote machine)

    - VS Code installs some files inside `.vscode-*` directories on the remote
      host to ensure full functionality of the extensions

  - [<span class="underline">Remote SSH</span>](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh)

  - [<span class="underline">Remote Explorer</span>](https://marketplace.visualstudio.com/items?itemName=ms-vscode.remote-explorer)

  - [<span class="underline">Remote Development</span>](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack)
    (Installed on the remote machine)

  - [<span class="underline">Dev Containers</span>](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

- Ability to access the remote server where the container will be located using
  SSH

- Kaizen dev environment set-up on the remote machine to allow running `invoke`
  targets

- A running Kaizen dev docker container created on the remote machine using
  `invoke docker_bash`

## Tips

- To open the command palette in VSCode use a keyboard shortcut Cmd + Shift + P

## Steps

1.  Open the command palette and search for `Remote-SSH: Connect to host` action

2.  Click `+ Add new SSH Host`. The prompt will ask you to provide a full
    command to log in to the server, e.g. "ssh ubuntu@10.11.12.13"

    1.  Note: if you use `~/.ssh/config` to specify frequently used hosts,
        VSCode will automatically fetch the list for you, this way you simply
        choose the name of the host and the connection is established
        automatically

3.  Make sure you have a container running using `invoke docker_bash` on the
    remote machine

4.  VSCode will establish a remote connection to the server and open a new
    window. Make sure that is your active window.

5.  Open the command palette and search for
    `Dev Containers: Attach To Running Container`. A list of all running
    containers on your server will appear, choose your container.

6.  Choose the debugging panel from the sidebar and click on `Run and Debug`

<img src="figs/visual_studio_code/image9.png" style="width:6.5in;height:1.84722in" />

7.  Click "Add Configuration" an editor for "launch.json" should open

<img src="figs/visual_studio_code/image11.png" style="width:6.5in;height:2.36111in" />

8. Paste the following JSON into the file and save it.

```
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit:
    https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
    {
        "name": "Python: Current File",
        "type": "python",
        "request": "launch",
        "program": "${file}",
        "console": "integratedTerminal",
        "justMyCode": true,
        "python":"/venv/bin/python",
        "env": {
            "PATH":
            "/app/amp/documentation/scripts:/app/amp/dev_scripts/testing:/app/amp/dev_scripts/notebooks:/app/amp/dev_scripts/install:/app/amp/dev_scripts/infra:/app/amp/dev_scripts/git:/app/amp/dev_scripts/aws:/app/amp/dev_scripts:/app/amp:/app/dev_script_p1:/app:.:/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONPATH":"/app/amp:/app:"
        }
    }
    ]
}
```

9.  Now you can open any Python file within the environment. You can for example
    set a breakpoint, hit the green "play" button and the debugger will run the
    currently opened file

<img src="figs/visual_studio_code/image10.png" style="width:6.5in;height:2.22222in" />

10. To run a script with a specific set of command line arguments, append
    `"args"` key to the launch.json file (the location should be
    `.vscode/launch.json`). The value is a list of command line arguments and
    values. Example below:

```
"args": [
    "--file",
    "/app/im_v2/ccxt/notebooks/Master_universe.ipynb",
    "--action",
    "convert"
]
```
