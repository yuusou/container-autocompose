#! /usr/bin/env python3
"""\
autocompose.py
    This tool generates a docker-compose.yml from running containers
    It can be used with both podman and docker (though testing is mostly done on podman)   
"""

import sys
import argparse
import re

try:
    import podman as container
except ImportError:
    try:
        import docker as container
    except ImportError:
        print("Neither podman nor docker modules found.")
        sys.exit(1)


def main():
    """Output docker-compose.yml"""

    # Check if we have access to container service
    c = container.from_env()
    try:
        c.ping()
    except container.errors.DockerException as e:
        print(f"An error occurred while attempting to connect to container service:\n{str(e)}")
        sys.exit(1)

    # Available arguments
    parser = argparse.ArgumentParser(
        description="This tool generates a docker-compose.yml from running containers",
    )

    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include all active containers",
    )
    parser.add_argument(
        "-f",
        "--filter",
        type=str,
        help="Filter containers by regex",
    )
    parser.add_argument(
        "cnames",
        nargs="*",
        type=str,
        help="The name of the containers to generate from (comma-separated))",
    )
    parser.add_argument(
        "-c",
        "--createvolumes",
        action="store_true",
        help="Create new volumes instead of reusing existing ones",
    )

    # Parse arguments
    args = parser.parse_args()
    container_names = args.cnames

    if args.all:
        container_names = [container.name for container in c.containers.list(all=True)]

    if args.filter:
        container_names = [x for x in container_names if re.compile(args.filter).search(c)]


if __name__ == "__main__":
    main()
