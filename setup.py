#!/usr/bin/env python
# coding=utf-8
from setuptools import setup, find_packages

setup(
    name="tinify-cli",
    version="1.0",
    keywords=("tinify-cli", "tinyjpg", "tinypng"),
    description="基于 Tinify 的批量图片压缩工具。",
    license="MIT",
    author='aheadlead',
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

