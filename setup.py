#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    # TODO: put package requirements here
    
]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='pulsar_telescope',
    version='0.1.0',
    description="A python package to run and collect data from a pulsar telescope.",
    long_description=readme + '\n\n' + history,
    author="Daniel Williams",
    author_email='1007382w@student.gla.ac.uk',
    url='https://github.com/transientlunatic/pulsar_telescope',
    packages=[
        'pulsar_telescope',
    ],
    package_data={
        '': ['pulsar_telescope/graycode.txt']
    }
    package_dir={'pulsar_telescope':
                 'pulsar_telescope'},
    include_package_data=True,
    install_requires=requirements,
    license="BSD",
    zip_safe=False,
    keywords='pulsar_telescope',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)