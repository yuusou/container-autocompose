#! /usr/bin/env python3
"""Install container-autocompose."""

from sys import argv
from setuptools import setup, find_packages

reqs = ["strictyaml>=1.6.1"]

if "--docker" in argv:
    reqs.append("docker>=7.0.0")
    argv.remove("--docker")

if "--podman" in argv or "--docker" not in argv:
    reqs.append("podman>=4.7.0")
    argv.remove("--podman")

setup(
    name="container-autocompose",
    version="2.0.0",
    description="Generate a container-compose.yml from running container(s)",
    url="https://github.com/yuusou/podman-autocompose",
    author="yuusou",
    license="GPLv2",
    keywords="podman docker yaml container compose podman-compose docker-compose",
    packages=find_packages(),
    install_requires=reqs,
    scripts=["autocompose.py"],
    entry_points={
        "console_scripts": [
            "autocompose = autocompose:main",
        ]
    },
)
