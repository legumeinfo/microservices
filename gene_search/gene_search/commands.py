# this file is a modification of:
# https://github.com/grpc/grpc/blob/fd3bd70939fb4239639fbd26143ec416366e4157/src/python/grpcio_health_checking/health_commands.py
# it uses build_package_proto, which is defined here
# https://github.com/grpc/grpc/blob/2231c2ba77cf22f3c8c302d91209c1c3f2f0632f/tools/distrib/python/grpcio_tools/grpc_tools/command.py

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
'''Provides distutils command classes for the gene search Python setup process.'''


import os
import setuptools


class BuildProtos(setuptools.Command):
  '''Command to generate project *_pb2.py modules from proto files.'''

  description = 'build grpc protobuf modules'
  user_options = []

  def initialize_options(self):
    pass

  def finalize_options(self):
    pass

  def run(self):
    # due to limitations of the proto generator, we require that only *one*
    # directory is provided as an 'include' directory. We assume it's the '' key
    # to `self.distribution.package_dir` (and get a key error if it's not
    # there).
    from grpc_tools import command
    proto_dir = \
      os.path.join(self.distribution.package_dir[''], 'gene_search/proto')
    command.build_package_protos(proto_dir)
