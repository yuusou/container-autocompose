# podman-autocompose
Generates a podman-compose yaml definition from a podman container.

Required Modules:
* [pyaml](https://pypi.python.org/project/pyaml/)
* [podman](https://pypi.python.org/project/podman)
* [six](https://pypi.python.org/project/six)

Example Usage:

    sudo python autocompose.py <container-name-or-id>


Generate a compose file for multiple containers together:

    sudo python autocompose.py apache-test mysql-test


The script defaults to outputting to compose file version 3, but use "-v 1" to output to version 1:

    sudo python autocompose.py -v 1 apache-test


Outputs a podman-compose compatible yaml structure:

[podman-compose reference](https://github.com/containers/podman-compose)

[podman-compose yaml file specification](https://github.com/compose-spec/compose-spec/blob/master/spec.md)

While experimenting with various podman containers from the Hub, I realized that I'd started several containers with complex options for volumes, ports, environment variables, etc. and there was no way I could remember all those commands without referencing the Hub page for each image if I needed to delete and re-create the container (for updates, or if something broke).

With this tool, I can easily generate podman-compose files for managing the containers that I've set up manually.

## Native installation

You can install it system-wide from the project directory with a command:

```python setup.py install --optimize=1```

You can also install directly from PyPI (https://pypi.org/project/podman-autocompose) with a command:
```pipx install podman-autocompose```

There are unofficial packages available in the Arch User Repository:
* [Stable](https://aur.archlinux.org/packages/podman-autocompose)
* [Development (follows the master branch)](https://aur.archlinux.org/packages/podman-autocompose-git)

**AUR packages are provided by a third party and are not tested or updated by the maintainer(s) of the podman-autocompose project.**

## Podman Usage

You can use this tool from a podman container by either cloning this repo and building the image or using the [automatically generated image on GitHub](https://github.com/Red5d/podman-autocompose/pkgs/container/podman-autocompose)

Pull the image from GitHub (supports both x86 and ARM)

    podman pull ghcr.io/red5d/podman-autocompose:latest

Use the new image to generate a podman-compose file from a running container or a list of space-separated container names or ids:

    podman run --rm -v /var/run/podman.sock:/var/run/podman.sock ghcr.io/red5d/podman-autocompose <container-name-or-id> <additional-names-or-ids>...

To print out all containers in a podman-compose format:

    podman run --rm -v /var/run/podman.sock:/var/run/podman.sock ghcr.io/red5d/podman-autocompose $(podman ps -aq)
    
## Contributing

When making changes, please validate the output from the script by writing it to a file (podman-compose.yml or podman-compose.yaml) and running "podman-compose config" in the same folder with it to ensure that the resulting compose file will be accepted by podman-compose.
