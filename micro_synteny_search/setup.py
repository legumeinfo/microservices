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
  from setuptools.command.build_py import build_py
  from micro_synteny_search import commands

  class BuildPy(build_py):
    '''Custom build_py command class.'''

    def run(self):
      self.run_command(build_proto_command)
      build_py.run(self)

  SETUP_REQUIRES = ('grpcio-tools>=1.39,<2',)
  COMMAND_CLASS = {
    build_proto_command: commands.BuildProtos,
    'build_py': BuildPy
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
