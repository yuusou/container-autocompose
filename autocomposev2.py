#! /usr/bin/env python3
"""\
autocompose.py
    This tool generates a docker-compose.yml from running containers
    It can be used with both podman and docker (though testing is mostly done on podman)   
"""

import sys
import argparse
import re

from collections import OrderedDict, abc
from strictyaml import as_document, YAML

try:
    import podman as container
except ImportError:
    try:
        import docker as container
    except ImportError:
        print("Neither podman nor docker modules found.", file=sys.stderr)
        sys.exit(1)

# Values that won't make the container-compose.yml
IGNORE_VALUES = [None, "", [], "null", {}, "default", 0, "0", ",", "no"]

# This will remove all values listed in the IGNORE_VALUES
def clean_values(values) -> dict:
    """Function removing unused values from container-compose.yml."""
    mapping = values

    for key, value in list(mapping.items()):
        if isinstance(value, abc.Mapping):
            mapping[key] = clean_values(value)
        if mapping[key] in IGNORE_VALUES:
            del mapping[key]

    return mapping

# This will generate the networks associated to the requested containers
def generate_networks(con, args) -> dict:
    """Function for creating the networks key"""
    networks = {}
    names = set(args.nnames.split())

    # All networks
    if args.all:
        names = [n.name for n in con.networks.list(all=True)]

    # Build network yaml dict structure
    for name in names:
        try:
            nname = [n.name for n in con.networks.list(all=True) \
                   if name == n.name][0]
        except IndexError:
            print(f"There's no network {name}.", file=sys.stderr)
            continue

        nattrs = con.networks.get(nname).attrs

        values = {
            "name": nattrs.get("name"),
            "driver": nattrs.get("driver", None),
            "enable_ipv6": nattrs.get("ipv6_enabled", False),
            "internal": nattrs.get("internal", False),
            "ipam": {
                "driver": nattrs.get("ipam_options", {}).get("driver", "none"),
            },
        }

        # Add network to networks key
        networks[nattrs.get("name")] = {key: value for key, value in values.items()}

    return networks

# This will generate the services key with the requested containers
def generate_services(con, args) -> tuple[dict, argparse.Namespace]:
    """Function for creating the services key."""
    services = {}
    names = set(args.cnames)
    default_networks = ["bridge", "host", "none"]

    # All containers
    if args.all:
        names = [c.name for c in con.containers.list(all=True)]

    # Filter through containers
    if args.filter:
        names = [name for name in names if re.compile(args.filter).search(con)]

    # Check if containers exists
    for name in names:
        try:
            cid = [c.short_id for c in con.containers.list(all=True) \
                   if name in (c.short_id, c.name)][0]
        except IndexError:
            print(f"There's no container {name}.", file=sys.stderr)
            continue

        cattrs = con.containers.get(cid).attrs

        values = {
            "container_name": cattrs.get("Name"),
            "image": cattrs.get("Config", {}).get("Image", None),
            "hostname": cattrs.get("Config", {}).get("Hostname", None),
            "domainname": cattrs.get("Config", {}).get("Domainname", None),
            "cap_drop": cattrs.get("HostConfig", {}).get("CapDrop", None),
            "cap_add": cattrs.get("HostConfig", {}).get("CapAdd", None),
            "deploy": {
                "resources": {
                    "limits": {
                        "cpus": cattrs.get("HostConfig", {}).get("CpuShares", None),
                        "memory": str(cattrs.get("HostConfig", {}).get("Memory", None)),
                    },
                    "reservations": {
                        "memory": str(cattrs.get("HostConfig", {}).get("MemoryReservation", None)),
                    },
                },
                "restart_policy": {
                    "condition": cattrs.get("HostConfig", {}).get("RestartPolicy", {}).\
                        get("Name", None),
                    "max_attempts": cattrs.get("HostConfig", {}).get("RestartPolicy", {}).\
                        get("MaximumRetryCount", None),
                },
            },
            "logging": {
                "driver": cattrs.get("HostConfig", {}).get("LogConfig", {}).get("Type", None),
                "options": cattrs.get("HostConfig", {}).get("LogConfig", {}).get("Config", None),
            },
            "volume_driver": cattrs.get("HostConfig", {}).get("VolumeDriver", None),
            "volumes_from": cattrs.get("HostConfig", {}).get("VolumesFrom", None),
            "dns": cattrs.get("HostConfig", {}).get("Dns", None),
            "dns_search": cattrs.get("HostConfig", {}).get("DnsSearch", None),
            "environment": cattrs.get("Config", {}).get("Env", None),
            "entrypoint": cattrs.get("Config", {}).get("Entrypoint", None),
            "user": cattrs.get("Config", {}).get("User", None),
            "working_dir": cattrs.get("Config", {}).get("WorkingDir", None),
            "privileged": cattrs.get("HostConfig", {}).get("Privileged", None),
            "read_only": cattrs.get("HostConfig", {}).get("ReadonlyRootfs", None),
            # Placeholders handled further down
            "networks": [],
            "ports": [],
            "expose": [],
            "command": "",
            "ulimits": {},
            "devices": [],
            "mounts": [],
            # These are commented out but usable, uncomment if needed
            #"tty": cattrs.get("Config", {}).get("Tty", None),
            #"stdin_open": cattrs.get("Config", {}).get("OpenStdin", None),
            #"extra_hosts": cattrs.get("HostConfig", {}).get("ExtraHosts", None),
            #"links": cattrs.get("HostConfig", {}).get("Links"),
            #"security_opt": cattrs.get("HostConfig", {}).get("SecurityOpt"),
            #"mac_address": cattrs.get("NetworkSettings", {}).get("MacAddress", None),
            #"labels": cattrs.get("Config", {}).get("Labels", {}),
            #"cgroup_parent": cattrs.get("HostConfig", {}).get("CgroupParent", None),
            #"ipc": cattrs.get("HostConfig", {}).get("IpcMode", None),
        }

        # Populate networks key if networks are present
        networks = [
            x for x in cattrs.get("NetworkSettings", {}).get("Networks", {}).keys() \
                if x not in default_networks
        ]
        if networks:
            if not any("--ip=" in x for x in cattrs.get("Config", {}).get("CreateCommand", [])):
                args.nnames =  f"{args.nnames} {' '.join(networks)}"
                values["networks"] = networks
            else:
                args.nnames =  f"{args.nnames} {networks[0]}"
                for x in cattrs.get("Config", {}).get("CreateCommand", []):
                    if "--ip=" in x:
                        values["networks"] = {
                            networks[0]: {
                                "ipv4_address": x.split("=")[1]
                            }
                        }
                        break
        else:
            values["network_mode"] = cattrs.get("NetworkSettings", {}).get("Networks", {})[0]

        # Populate port forwards or exposed ports if present
        values["expose"] = list(cattrs.get("Config", {}).get("ExposedPorts", {}).keys())
        ports = [
            cattrs.get("HostConfig", {}).get("PortBindings", {})[key][0]["HostIp"] + ":" +
            cattrs.get("HostConfig", {}).get("PortBindings", {})[key][0]["HostPort"] + ":" + key
            for key in cattrs.get("HostConfig", {}).get("PortBindings") \
                if cattrs.get("HostConfig", {}).get("PortBindings", {})[key] is not None
        ]
        if ports not in values["expose"]:
            for index, port in enumerate(ports):
                if port[0] == ":":
                    ports[index] = port[1:]

            values["ports"] = ports

        # Populate command key if command is present
        commands = cattrs.get("Config", {}).get("Cmd")
        if commands:
            for x in commands:
                x = '"' + x + '"' if " " in x else x
                x = x.replace("$","$$")
                values["command"] = " ".join([values["command"], x]).strip()

        # Populate ulimits key if ulimit values are present
        ulimits = cattrs.get("HostConfig", {}).get("Ulimits")
        if ulimits:
            for x in ulimits:
                if x["Soft"] == x["Hard"]:
                    ulimit = { x["Name"].replace('RLIMIT_', '').lower(): x["Hard"] }
                else:
                    ulimit = {
                        x["Name"].replace('RLIMIT_', '').lower(): {
                            "soft": x["Soft"],
                            "hard": x["Hard"],
                        }
                    }
                values["ulimits"].update(ulimit)

        # Populate devices key if device values are present
        devices = cattrs.get("HostConfig", {}).get("Devices")
        if devices:
            values["devices"] = [
                x["PathOnHost"] + ":" + x["PathInContainer"] \
                    for x in cattrs.get("HostConfig", {}).get("Devices")
            ]

        # Add container to services key
        services[cattrs.get("Name")] = {key: value for key, value in values.items()}

    return services, args

# This will send the yaml file to stdout
def render(networks, services, volumes) -> None:
    """Function for rendering container-compose.yml."""
    file = {"version": '3.8'}

    file["networks"] = networks
    file["services"] = services
    file["volumes"] = volumes

    yaml = YAML(as_document(clean_values(OrderedDict(file))).as_yaml())
    print(yaml.data)

# This will generate the container-compose.yml file and print it out.
def main() -> None:
    """Output container-compose.yml"""

    # Check if we have access to container service
    con = container.from_env()

    try:
        con.ping()
    except container.errors.DockerException as e:
        print(f"An error occurred while attempting to connect to container service:\n\
              {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Available arguments
    parser = argparse.ArgumentParser(
        description="This tool generates a container-compose.yml from running containers",
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
        help="The name of the containers to generate from (space-separated))",
    )
    parser.add_argument(
        "-c",
        "--createvolumes",
        action="store_true",
        help="Create new volumes instead of reusing existing ones",
    )

    # Parse arguments
    args = parser.parse_args()
    args.nnames = ""
    args.vnames = ""

    networks = {}
    services = {}
    volumes = {}

    # Services must come first to populate networks and volumes
    c_services, args = generate_services(con, args)
    c_networks = generate_networks(con, args)
    #c_volumes = generate_volumes(con, args)

    services.update(c_services)
    if c_networks is not None:
        networks.update(c_networks)
    #if c_volumes is not None:
    #    volumes.update(c_volumes)

    render(networks, services, volumes)

if __name__ == "__main__":
    main()
