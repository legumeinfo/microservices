#!/usr/bin/env python
import setuptools


PACKAGE_DIRECTORIES = {
  '': '.',
}


class NoOpCommand(setuptools.Command):
  '''No operation command.'''

  description = ''
  user_options = []

  def initialize_options(self):
      pass

  def finalize_options(self):
      pass

  def run(self):
      pass


build_proto_command = 'build_proto'


try:
  # these imports will fail unless in the build environment
  from distutils.command.build import build
  from pairwise_macro_synteny_blocks import commands

  class Build(build):
    '''Custom build command.'''

    def has_protos(self):
      # TODO: update to actually check proto files exist
      return True

    # prepend build_proto because it generates .py files that build_py will
    # install
    sub_commands =  [(build_proto_command, has_protos)] + build.sub_commands

  SETUP_REQUIRES = ('grpcio-tools>=1.39,<2',)
  COMMAND_CLASS = {
    build_proto_command: commands.BuildProtos,
    'build': Build
  }
except ImportError:
  SETUP_REQUIRES = ()
  COMMAND_CLASS = {
    build_proto_command: NoOpCommand,
  }


setuptools.setup(
  package_dir=PACKAGE_DIRECTORIES,
  setup_requires=SETUP_REQUIRES,
  cmdclass=COMMAND_CLASS,
)
