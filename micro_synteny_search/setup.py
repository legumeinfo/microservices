#!/usr/bin/env python

# Python
import setuptools
from setuptools.command.build_py import build_py

# package
from micro_synteny_search import commands


PACKAGE_DIRECTORIES = {
    "": ".",
}


build_proto_command = "build_proto"


class BuildPy(build_py):
    """Custom build_py command class."""

    def run(self):
        build_py.run(self)
        self.run_command(build_proto_command)


SETUP_REQUIRES = ("grpcio-tools",)
COMMAND_CLASS = {build_proto_command: commands.BuildProtos, "build_py": BuildPy}


setuptools.setup(
    package_dir=PACKAGE_DIRECTORIES,
    setup_requires=SETUP_REQUIRES,
    cmdclass=COMMAND_CLASS,
)
