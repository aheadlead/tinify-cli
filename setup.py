#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages

from tinifycli.__init__ import __title__, __version__, __license__, __author__

setup(
    name=__title__,
    version=__version__,
    keywords=("tinify-cli", "tinyjpg", "tinypng"),
    description="基于 Tinify 的批量图片压缩工具。",
    license=__license__,
    author=__author__,
    author_email="aheadlead@dlifep.com",
    url='http://github.com/aheadlead/tinify-cli',
    package_data={'': ['cacert.pem']},
    install_requires=[
        'requests',
        'prettytable'
    ],
    packages=find_packages(),
    entry_points={
        'console_scripts': ['tinify-cli=tinifycli.__init__:main']
    }
)

