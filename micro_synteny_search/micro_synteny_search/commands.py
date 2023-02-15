# this file is a modification of:
# https://github.com/grpc/grpc/blob/2231c2ba77cf22f3c8c302d91209c1c3f2f0632f/tools/distrib/python/grpcio_tools/grpc_tools/command.py

# here is an example of how it should be used:
# https://github.com/grpc/grpc/blob/fd3bd70939fb4239639fbd26143ec416366e4157/src/python/grpcio_health_checking/health_commands.py

# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Provides distutils command classes for the micro-synteny search Python setup process."""


import os
import pkg_resources
import setuptools
import sys


class BuildProtos(setuptools.Command):
    """Command to generate project *_pb2.py modules from proto files."""

    description = "build grpc protobuf modules"
    user_options = [
        ("strict-mode", "s", "exit with non-zero value if the proto compiling fails.")
    ]

    def initialize_options(self):
        self.strict_mode = False
        self.build_lib = None
        self.proto_dir = None
        self.proto_build_dir = None

    def finalize_options(self):
        self.set_undefined_options("build", ("build_lib", "build_lib"))
        package_root = self.distribution.package_dir[""]
        self.proto_dir = os.path.abspath(os.path.join(package_root, "proto"))
        self.proto_build_dir = os.path.abspath(
            os.path.join(self.build_lib, "micro_synteny_search/proto")
        )

    def run(self):
        self.build_package_protos()

    def build_package_protos(self):
        from grpc_tools import protoc

        proto_files = []
        for root, _, files in os.walk(self.proto_dir):
            for filename in files:
                if filename.endswith(".proto"):
                    proto_files.append(os.path.abspath(os.path.join(root, filename)))

        well_known_protos_include = pkg_resources.resource_filename(
            "grpc_tools", "_proto"
        )

        for proto_file in proto_files:
            command = [
                "grpc_tools.protoc",
                "--proto_path={}".format(self.proto_dir),
                "--proto_path={}".format(well_known_protos_include),
                "--python_out={}".format(self.proto_build_dir),
                "--grpc_python_out={}".format(self.proto_build_dir),
            ] + [proto_file]
            if protoc.main(command) != 0:
                if self.strict_mode:
                    raise Exception("error: {} failed".format(command))
                else:
                    sys.stderr.write("warning: {} failed".format(command))
