

<!-- toc -->

- [What is SSH?](#what-is-ssh)
- [How we use ssh in our company?](#how-we-use-ssh-in-our-company)
- [Public key for authorization?](#public-key-for-authorization)

<!-- tocstop -->

# What is SSH?

From the Wikipedia

> Secure Shell (SSH) is a cryptographic network protocol for operating network
> services securely over an unsecured network.[1] Typical applications include
> remote command-line, login, and remote command execution, but any network
> service can be secured with SSH.

More details [here](https://en.wikipedia.org/wiki/Secure_Shell)

# How we use ssh in our company?

- We use it to connect to any of our servers.
- Sometimes we use `scp` to copy files between hosts via `ssh`.
  - Don't know what is `scp`? read
    [here](https://haydenjames.io/linux-securely-copy-files-using-scp/)

# Public key for authorization?

- We use `public key` authorization. This is the common way of secure
  authorization for SSH connection.
- GitHub also can authorize you with `public key`, if you setup it in your GH
  account. This is mean that you don't have to type your `login` and `password`
  when you interact with GitHub via `git` e.g. `git clone`, `git pull`, etc.

More details about `public key`
[here](https://www.ssh.com/ssh/public-key-authentication)
