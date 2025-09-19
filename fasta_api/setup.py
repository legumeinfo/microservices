#!/usr/bin/env python
# Python
import setuptools
import shutil

shutil.copy2("./openapi/fasta_api/v1/fasta_api.yaml", "fasta_api/fasta_api.yaml")

setuptools.setup(include_package_data=True)
