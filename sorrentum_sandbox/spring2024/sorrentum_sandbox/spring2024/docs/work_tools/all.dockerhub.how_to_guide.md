# Login Dockerhub

https://hub.docker.com/

# TODO(Sameep): Update to `kaizenflow` once docker is updated
Username: sorrentum
Email: gp@crypto-kaizen.com

There are several public images

- sorrentum/cmamp
- sorrentum/dev_tools

Used in DATA605:
- sorrentum/sorrentum
- sorrentum/defi
- sorrentum/jupyter

The page corresponding to the Sorrentum repo is
https://hub.docker.com/u/sorrentum

# Login through CLI

> docker login --username sorrentum --password XYZ

# List all the images

- Without authentication
```
> curl -s "https://hub.docker.com/v2/repositories/sorrentum/?page_size=100" | jq '.results|.[]|.name'
"sorrentum"
"cmamp"
"jupyter"
"dev_tools"
"defi"
```

# Rename an image

> docker pull yourusername/oldimagename:tag
> docker tag yourusername/oldimagename:tag yourusername/newimagename:tag
> docker push yourusername/newimagename:tag

- To delete the old image you need to go through the GUI
