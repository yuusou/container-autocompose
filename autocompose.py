#! /usr/bin/env python3
"""Generate docker-compose.yml from running containers."""
import argparse
import re
import sys

from collections import OrderedDict, abc

import podman
import pyaml


pyaml.add_representer(bool,lambda s,o:
                      s.represent_scalar('tag:yaml.org,2002:bool',['false','true'][o]))
IGNORE_VALUES = [None, "", [], "null", {}, "default", 0, ",", "no"]


def list_container_names():
    """Function collecting list of container names"""
    c = podman.from_env()
    return [container.name for container in c.containers.list(all=True)]


def list_network_names():
    """Function collecting list of network names"""
    c = podman.from_env()
    return [network.name for network in c.networks.list()]


def generate_network_info():
    """Function generating network information"""
    networks = {}

    for network_name in list_network_names():
        connection = podman.from_env()
        network_attributes = connection.networks.get(network_name).attrs

        values = {
            "name": network_attributes.get("name"),
            "driver": network_attributes.get("driver", None),
            "enable_ipv6": network_attributes.get("ipv6_enabled", False),
            "internal": network_attributes.get("internal", False),
            "ipam": {
                "driver": network_attributes.get("ipam_options", {}).get("driver", "none"),
            },
        }

        networks[network_name] = {key: value for key, value in values.items()}

    return networks


def clean_values(values):
    """Function removing unused values from compose.yml."""
    mapping = values
    for key, value in list(mapping.items()):
        if isinstance(value, abc.Mapping):
            mapping[key] = clean_values(value)
        if mapping[key] in IGNORE_VALUES:
            del mapping[key]
    return mapping


def main():
    """Main function for creating the docker-compose.yml."""
    parser = argparse.ArgumentParser(
        description="Generate podman-compose yaml definition from running container.",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Include all active containers",
    )
    parser.add_argument(
        "cnames",
        nargs="*",
        type=str,
        help="The name of the container to process.",
    )
    parser.add_argument(
        "-c",
        "--createvolumes",
        action="store_true",
        help="Create new volumes instead of reusing existing ones",
    )
    parser.add_argument(
        "-f",
        "--filter",
        type=str,
        help="Filter containers by regex",
    )
    args = parser.parse_args()

    container_names = args.cnames

    if args.all:
        container_names.extend(list_container_names())

    if args.filter:
        cfilter = re.compile(args.filter)
        container_names = [c for c in container_names if cfilter.search(c)]

    services = {}
    networks = {}
    volumes = {}

    for cname in container_names:
        cfile, c_networks, c_volumes = generate(cname, createvolumes=args.createvolumes)

        services.update(cfile)

        if c_networks is not None:
            networks.update(c_networks)
        if c_volumes is not None:
            volumes.update(c_volumes)

    # moving the networks = None statements outside of the for loop. Otherwise any container could reset it.
    if len(networks) == 0:
        networks = None
    if len(volumes) == 0:
        volumes = None

    if args.all:
        host_networks = generate_network_info()
        networks = host_networks

    render(services, networks, volumes)


def render(services, networks, volumes):
    """Function for rendering docker-compose.yml."""
    ans = {"version": '3.8'}

    if services is not None:
        ans["services"] = services

    if networks is not None:
        ans["networks"] = networks

    if volumes is not None:
        ans["volumes"] = volumes

    pyaml.p(OrderedDict(ans), string_val_style='"')


def generate(cname, createvolumes=False):
    """Function for creating the services key."""
    c = podman.from_env()

    try:
        cid = [x.short_id for x in c.containers.list(all=True) if cname == x.name or x.short_id in cname][0]
    except IndexError:
        print("That container is not available.", file=sys.stderr)
        sys.exit(1)

    cattrs = c.containers.get(cid).attrs

    # Build yaml dict structure

    cfile = {}
    cfile[cattrs.get("Name")] = {}
    ct = cfile[cattrs.get("Name")]

    default_networks = ["bridge", "host", "none"]

    values = {
        "cap_drop": cattrs.get("HostConfig", {}).get("CapDrop", None),
        "cap_add": cattrs.get("HostConfig", {}).get("CapAdd", None),
        #"cgroup_parent": cattrs.get("HostConfig", {}).get("CgroupParent", None),
        "container_name": cattrs.get("Name"),
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
                "condition": cattrs.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", None),
                "max_attempts": cattrs.get("HostConfig", {}).get("RestartPolicy", {}).get("MaximumRetryCount", None),
            },
        },
        "devices": [],
        "dns": cattrs.get("HostConfig", {}).get("Dns", None),
        "dns_search": cattrs.get("HostConfig", {}).get("DnsSearch", None),
        "environment": cattrs.get("Config", {}).get("Env", None),
        "extra_hosts": cattrs.get("HostConfig", {}).get("ExtraHosts", None),
        "image": cattrs.get("Config", {}).get("Image", None),
        #"labels": cattrs.get("Config", {}).get("Labels", {}),
        "links": cattrs.get("HostConfig", {}).get("Links"),
        "logging": {
            "driver": cattrs.get("HostConfig", {}).get("LogConfig", {}).get("Type", None),
            "options": cattrs.get("HostConfig", {}).get("LogConfig", {}).get("Config", None),
        },
        "networks": [
            x for x in cattrs.get("NetworkSettings", {}).get("Networks", {}).keys() if x not in default_networks
        ],
        "security_opt": cattrs.get("HostConfig", {}).get("SecurityOpt"),
        "ulimits": {},
        "mounts": [],  # this could be moved outside of the dict. will only use it for generate
        "volume_driver": cattrs.get("HostConfig", {}).get("VolumeDriver", None),
        "volumes_from": cattrs.get("HostConfig", {}).get("VolumesFrom", None),
        "entrypoint": cattrs.get("Config", {}).get("Entrypoint", None),
        "user": cattrs.get("Config", {}).get("User", None),
        "working_dir": cattrs.get("Config", {}).get("WorkingDir", None),
        "domainname": cattrs.get("Config", {}).get("Domainname", None),
        "hostname": cattrs.get("Config", {}).get("Hostname", None),
        #"ipc": cattrs.get("HostConfig", {}).get("IpcMode", None),
        "mac_address": cattrs.get("NetworkSettings", {}).get("MacAddress", None),
        "privileged": cattrs.get("HostConfig", {}).get("Privileged", None),
        "read_only": cattrs.get("HostConfig", {}).get("ReadonlyRootfs", None),
        "stdin_open": cattrs.get("Config", {}).get("OpenStdin", None),
        "tty": cattrs.get("Config", {}).get("Tty", None),
        "command": "",
    }

    # Populate devices key if device values are present
    devices = cattrs.get("HostConfig", {}).get("Devices")
    if devices:
        values["devices"] = [
            x["PathOnHost"] + ":" + x["PathInContainer"] for x in cattrs.get("HostConfig", {}).get("Devices")
        ]

    # Populate ulimits
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

    networks = {}
    if values["networks"] == set():
        del values["networks"]

        if len(cattrs.get("NetworkSettings", {}).get("Networks", {}).keys()) > 0:
            assumed_default_network = list(cattrs.get("NetworkSettings", {}).get("Networks", {}).keys())[0]
            values["network_mode"] = assumed_default_network
            networks = None
    else:
        networklist = c.networks.list()
        for network in networklist:
            if network.attrs["name"] in values["networks"]:
                networks[network.attrs["name"]] = {
                    "external": (not network.attrs["internal"]),
                    "name": network.attrs["name"],
                }
    #     volumes = {}
    #     if values['volumes'] is not None:
    #         for volume in values['volumes']:
    #             volume_name = volume.split(':')[0]
    #             volumes[volume_name] = {'external': True}
    #     else:
    #         volumes = None

    # handles both the returned values['volumes'] (in c_file) and volumes for both, the bind and volume types
    # also includes the read only option
    volumes = {}
    mountpoints = []
    mounts = cattrs.get("Mounts")
    if mounts:
        for mount in mounts:
            destination = mount["Destination"]
            if not mount["RW"]:
                destination = destination + ":ro"
            if mount["Type"] == "volume":
                mountpoints.append(mount["Name"] + ":" + destination)
                if not createvolumes:
                    volumes[mount["Name"]] = {
                        "external": True
                    }  # to reuse an existing volume ... better to make that a choice? (cli argument)
            elif mount["Type"] == "bind":
                mountpoints.append(mount["Source"] + ":" + destination)
        values["volumes"] = sorted(mountpoints)
    if len(volumes) == 0:
        volumes = None
    values["mounts"] = None  # remove this temporary data from the returned data

    # Check for command and add it if present.
    commands = cattrs.get("Config", {}).get("Cmd")
    if commands:
        for x in commands:
            x = '"' + x + '"' if " " in x else x
            x = x.replace("$","$$")
            values["command"] = " ".join([values["command"], x]).strip()

    # Check for exposed/bound ports and add them if needed.
    try:
        expose_value = list(cattrs.get("Config", {}).get("ExposedPorts", {}).keys())
        ports_value = [
            cattrs.get("HostConfig", {}).get("PortBindings", {})[key][0]["HostIp"]
            + ":"
            + cattrs.get("HostConfig", {}).get("PortBindings", {})[key][0]["HostPort"]
            + ":"
            + key
            for key in cattrs.get("HostConfig", {}).get("PortBindings")
        ]

        # If bound ports found, don't use the 'expose' value.
        if ports_value not in IGNORE_VALUES:
            for index, port in enumerate(ports_value):
                if port[0] == ":":
                    ports_value[index] = port[1:]

            values["ports"] = ports_value
        else:
            values["expose"] = expose_value

    except (KeyError, TypeError):
        # No ports exposed/bound. Continue without them.
        ports = None

    # Iterate through values to finish building yaml dict.
    for key, value in clean_values(values).items():
        ct[key] = value

    return cfile, networks, volumes


if __name__ == "__main__":
    main()
