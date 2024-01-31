# container-autocompose
Generates a yaml file from docker or podman containers.
This is a fork of [docker-autocompose](https://github.com/Red5d/docker-autocompose) 
I've modified it to be compatible with both docker and podman.

With this tool, you can easily generate container-compose.yml / docker-compose.yml files for managing the containers that you've manually set up.
## Wee disclaimer
I'm not well versed in either Docker nor Podman, much less python.
If you have problems, please raise an issue and I'll do my best. :)

While experimenting with various containers from the Hub, I realized that I'd started several containers with complex options for volumes, ports, environment variables, etc. and there was no way I could remember all those commands without referencing the Hub page for each image if I needed to delete and re-create the container (for updates, or if something broke).

## Requirements
Required Modules:
* [strictyaml](https://pypi.org/project/strictyaml/)
* [podman](https://pypi.python.org/project/podman) or
* [docker](https://pypi.python.org/project/docker)

## Usage
Example Usage:
```sudo python3 autocompose.py <space-separated-container-names-or-ids>```

For all containers:
```sudo python3 autocompose.py -a```

Generate a compose file for multiple containers together:
```sudo python3 autocompose.py apache-test mysql-test```

If you get an error requiring CONTAINER_HOST or DOCKER_HOST environment variable, try the following (adjusting as necessary):
```CONTAINER_HOST=unix:///var/run/podman/podman.sock sudo python3 autocompose.py -a```

## References
Outputs yaml to stdout compatible with podman-compose and docker-compose (right now there's no difference between them):
[podman-compose reference](https://github.com/docker/compose)
[podman-compose yaml file specification](https://docs.docker.com/compose/compose-file/compose-file-v3/)
[docker-compose reference](https://github.com/containers/podman-compose)
[docker-compose yaml file specification](https://github.com/compose-spec/compose-spec/blob/master/spec.md)

## Native installation
For operating systems that externally manage python3 and pip (Ubuntu, Fedora, maybe others), you'll need to manually install the python3-podman or python3-docker package.
You can install them system-wide from the project directory with a command:

For Podman
```python3 setup.py install --optimize=1```

For Docker
```python3 setup.py install --optimize=1 --docker```
    
## Contributing

When making changes, please validate the output from the script by writing it to a file (podman-compose.yml or podman-compose.yaml) and running "podman-compose config" in the same folder with it to ensure that the resulting compose file will be accepted by podman-compose.
