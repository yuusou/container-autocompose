# podman-autocompose
Generates a podman-compose yaml definition from a podman container.

## Wee disclaimer
I'm not well versed in either Docker nor Podman, much less python.
I forked docker-autocomplete and did what needed doing to make it work for podman.

If you have problems, please raise an issue and I'll do my best, though don't expect miracles. :)

## Requirements and Usage
Required Modules:
* [pyaml](https://pypi.python.org/project/pyaml/)
* [podman](https://pypi.python.org/project/podman)
* [six](https://pypi.python.org/project/six)

Example Usage:

    sudo python3 autocompose.py <container-name-or-id>

Generate a compose file for multiple containers together:

    sudo python3 autocompose.py apache-test mysql-test

The script defaults to outputting to compose file version 3, but use "-v 1" to output to version 1:

    sudo python3 autocompose.py -v 1 apache-test

If you get an error requiring CONTAINER_HOST environment variable, try the following (adjusting as necessary):

    CONTAINER_HOST=unix:///var/run/podman/podman.sock sudo python3 autocompose.py <container-name-or-id>

Outputs a podman-compose compatible yaml structure:

[podman-compose reference](https://github.com/containers/podman-compose)

[podman-compose yaml file specification](https://github.com/compose-spec/compose-spec/blob/master/spec.md)

While experimenting with various ~~docker~~containers from the Hub, I realized that I'd started several containers with complex options for volumes, ports, environment variables, etc. and there was no way I could remember all those commands without referencing the Hub page for each image if I needed to delete and re-create the container (for updates, or if something broke).

With this tool, you can easily generate podman-compose files for managing the containers that I've set up manually.

## Native installation
For operating systems that externally manage python3 and pip (Ubuntu, Fedora, maybe others), you'll need to install the python3-podman package.
You can install it system-wide from the project directory with a command:

```python3 setup.py install --optimize=1```
    
## Contributing

When making changes, please validate the output from the script by writing it to a file (podman-compose.yml or podman-compose.yaml) and running "podman-compose config" in the same folder with it to ensure that the resulting compose file will be accepted by podman-compose.
