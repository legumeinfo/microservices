# setup.py
from setuptools import find_packages, setup

from dscensor import __version__

setup(
    name="dscensor",
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "aiohttp",
        "rororo",
        "pyyaml",
        "networkx",
    ],
    entry_points={
        "console_scripts": [
            "dscensor = dscensor.__main__:create_app",
        ],
    },
)
