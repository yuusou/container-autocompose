#! /usr/bin/env python3
import argparse
import datetime
import re
import sys

from collections import OrderedDict

import podman
import pyaml

pyaml.add_representer(bool,lambda s,o: s.represent_scalar('tag:yaml.org,2002:bool',['false','true'][o]))
IGNORE_VALUES = [None, "", [], "null", {}, "default", 0, ",", "no"]


def list_container_names():
    c = podman.from_env()
    return [container.name for container in c.containers.list(all=True)]


def list_network_names():
    c = podman.from_env()
    return [network.name for network in c.networks.list()]


def generate_network_info():
    networks = {}

    for network_name in list_network_names():
        connection = podman.from_env()
        network_attributes = connection.networks.get(network_name).attrs

        values = {
            "name": network_attributes.get("Name"),
            "scope": network_attributes.get("Scope", "local"),
            "driver": network_attributes.get("Driver", None),
            "enable_ipv6": network_attributes.get("EnableIPv6", False),
            "internal": network_attributes.get("Internal", False),
            "ipam": {
                "driver": network_attributes.get("IPAM", {}).get("Driver", "default"),
                "config": [
                    {key.lower(): value for key, value in config.items()}
                    for config in network_attributes.get("IPAM", {}).get("Config", [])
                ],
            },
        }

        networks[network_name] = {key: value for key, value in values.items()}

    return networks


def main():
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

    struct = {}
    networks = {}
    volumes = {}
    containers = {}

    for cname in container_names:
        cfile, c_networks, c_volumes = generate(cname, createvolumes=args.createvolumes)

        struct.update(cfile)

        if not c_networks == None:
            networks.update(c_networks)
        if not c_volumes == None:
            volumes.update(c_volumes)

    # moving the networks = None statements outside of the for loop. Otherwise any container could reset it.
    if len(networks) == 0:
        networks = None
    if len(volumes) == 0:
        volumes = None

    if args.all:
        host_networks = generate_network_info()
        networks = host_networks

    render(struct, args, networks, volumes)


def render(struct, args, networks, volumes):
    ans = {"version": '3.8', "services": struct}

    if networks is not None:
        ans["networks"] = networks

    if volumes is not None:
        ans["volumes"] = volumes

    pyaml.p(OrderedDict(ans), string_val_style='"')


def generate(cname, createvolumes=False):
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
        "cgroup_parent": cattrs.get("HostConfig", {}).get("CgroupParent", None),
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
        "labels": cattrs.get("Config", {}).get("Labels", {}),
        "links": cattrs.get("HostConfig", {}).get("Links"),
        "logging": {
            "driver": cattrs.get("HostConfig", {}).get("LogConfig", {}).get("Type", None),
            "options": cattrs.get("HostConfig", {}).get("LogConfig", {}).get("Config", None),
        },
        "networks": {
            x for x in cattrs.get("NetworkSettings", {}).get("Networks", {}).keys() if x not in default_networks
        },
        "security_opt": cattrs.get("HostConfig", {}).get("SecurityOpt"),
        # the line below would not handle type bind
        #        'volumes': [f'{m["Name"]}:{m["Destination"]}' for m in cattrs.get('Mounts'] if m['Type'] == 'volume'],
        "mounts": cattrs.get("Mounts"),  # this could be moved outside of the dict. will only use it for generate
        "ulimits": {},
        "volume_driver": cattrs.get("HostConfig", {}).get("VolumeDriver", None),
        "volumes_from": cattrs.get("HostConfig", {}).get("VolumesFrom", None),
        "entrypoint": cattrs.get("Config", {}).get("Entrypoint", None),
        "user": cattrs.get("Config", {}).get("User", None),
        "working_dir": cattrs.get("Config", {}).get("WorkingDir", None),
        "domainname": cattrs.get("Config", {}).get("Domainname", None),
        "hostname": cattrs.get("Config", {}).get("Hostname", None),
        "ipc": cattrs.get("HostConfig", {}).get("IpcMode", None),
        "mac_address": cattrs.get("NetworkSettings", {}).get("MacAddress", None),
        "privileged": cattrs.get("HostConfig", {}).get("Privileged", None),
        "read_only": cattrs.get("HostConfig", {}).get("ReadonlyRootfs", None),
        "stdin_open": cattrs.get("Config", {}).get("OpenStdin", None),
        "tty": cattrs.get("Config", {}).get("Tty", None),
    }

    # Populate devices key if device values are present
    if cattrs.get("HostConfig", {}).get("Devices"):
        values["devices"] = [
            x["PathOnHost"] + ":" + x["PathInContainer"] for x in cattrs.get("HostConfig", {}).get("Devices")
        ]
    
    # Populate ulimits
    if cattrs.get("HostConfig", {}).get("Ulimits"):
        for x in cattrs.get("HostConfig", {}).get("Ulimits"):
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
    if values["mounts"] is not None:
        for mount in values["mounts"]:
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
    if cattrs.get("Config", {}).get("Cmd") is not None:
        values["command"] = " ".join(cattrs.get("Config", {}).get("Cmd"))

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
    for key in values:
        value = values[key]
        if value not in IGNORE_VALUES:
            ct[key] = value

    return cfile, networks, volumes


if __name__ == "__main__":
    main()
