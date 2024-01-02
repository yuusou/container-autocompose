from setuptools import setup, find_packages
setup(
    name = "podman-autocompose",
    version = "1.2.0",
    description = "Generate a podman-compose yaml definition from a running container",
    url = "https://github.com/yuusou/podman-autocompose",
    author = "yuusou",
    license = "GPLv2",
    keywords = "podman yaml container",
    packages = find_packages(),
    install_requires = ['pyaml>=17.12.1', 'podman>=4.7.0','six>=1.16.0'],
    scripts = ['autocompose.py'],
    entry_points={
        'console_scripts': [
            'autocompose = autocompose:main',
        ]
    }
)
