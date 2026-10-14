#!/usr/bin/env python
# Python
import shutil

import setuptools

shutil.copy2(
    "./openapi/ds_utilities/v1/ds_utilities.yaml", "ds_utilities/ds_utilities.yaml"
)

setuptools.setup(include_package_data=True)
