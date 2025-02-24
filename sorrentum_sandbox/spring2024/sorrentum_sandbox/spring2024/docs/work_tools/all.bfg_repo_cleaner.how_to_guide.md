# BFG Repo-Cleaner

[BFG](https://rtyley.github.io/bfg-repo-cleaner/) dockerized.

## Build

```bash
docker build . --tag bfg
```

## Usage

You could run BFG in a container by executing the following `docker` command.

```bash
docker run -it --rm \
  --volume "$PWD:/home/bfg/workspace" \
  koenrh/bfg \
  --delete-files id_rsa
```

You could make this command more easily accessible by putting it in an executable,
and make sure that it is available in your `$PATH`. Alternatively, you could create
wrapper functions for your `docker run` commands ([example](https://github.com/jessfraz/dotfiles/blob/master/.dockerfunc)).

```bash
bfg() {
  docker run -it --rm \
    --volume "$PWD:/home/bfg/workspace" \
    --name bfg \
    koenrh/bfg "$@"
}
```
