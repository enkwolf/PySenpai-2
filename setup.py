from setuptools import find_packages, setup

setup(
    name="PySenpai",
    version="2.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "stdlib_list",
        "pylint",
        "pyyaml"
    ],
    entry_points={
        "console_scripts": [
            "pysen-cliout=pysenpai.scripts.cliout:main"
        ]
    },
)