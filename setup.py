from os import path
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.readlines()

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md")) as f:
    long_description = f.read()

setup(
    name="idasen-controller",
    version="2.0.0",
    author="Rhys Tyers",
    author_email="",
    url="https://github.com/rhyst/idasen-controller",
    description="Command line tool for controlling the Ikea Idasen (Linak) standing desk",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    packages=find_packages(),
    entry_points={"console_scripts": ["idasen-controller=idasen_controller.main:init"]},
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    keywords="python package idasen-controller idasen linak standing desk",
    install_requires=requirements,
    zip_safe=False,
    include_package_data=True,
    package_data={"": ["example/*"]},
    python_requires=">=3.7.3",
)
