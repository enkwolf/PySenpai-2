from setuptools import find_packages, setup

setup(
    name="PySenpai",
    version="2.0.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={"pysenpai.msg_data": ["*/*.yml"]},
    install_requires=[
        "setuptools-git",
        "pylint",
        "pyyaml"
    ],
    entry_points={
        "console_scripts": [
            "pysen-cliout=pysenpai.scripts.cliout:main"
        ]
    },
)
