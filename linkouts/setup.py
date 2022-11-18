#!/usr/bin/env python
# Python
import setuptools
from setuptools.command.build_py import build_py


PACKAGE_DIRECTORIES = {
  '': '.',
}


COMMAND_CLASS = {}


class BuildPy(build_py):
  '''Custom build_py command class.'''

  def run(self):
    build_py.run(self)


SETUP_REQUIRES = ()
COMMAND_CLASS = {
  'build_py': BuildPy
}


setuptools.setup(
  package_dir=PACKAGE_DIRECTORIES,
  setup_requires=SETUP_REQUIRES,
  cmdclass=COMMAND_CLASS,
)
