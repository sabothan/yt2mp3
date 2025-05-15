"""Setup yt2mp3.

Install yt2mp3 with:
    $ pip install -e .
"""

from setuptools import setup, find_packages


NAME = 'ytmp3'
VERSION = '0.0.1'
AUTHOR = 'sabothan'
description = 'A minimalistic CLI tool to convert YouTube videos to MP3 files.'

def parse_requirements(filename):
    """Read and load the requirements from a corresponding file."""
    with open(filename) as f:
        lines = f.readlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith('#')]

setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    packages=find_packages(),
    install_requires=parse_requirements('requirements.txt'),
    python_requires="==3.9.*",
    entry_points={'console_scripts': ['yt2mp3=yt2mp3.main:main']}
)