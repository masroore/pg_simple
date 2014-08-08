from setuptools import setup, find_packages

import pg_simple

with open("README.md") as stream: long_description = stream.read()

setup(
    name=pg_simple.__name__,
    version=pg_simple.VERSION,
    packages=find_packages(),
    install_requires=['psycopg2'],
    classifiers=["Topic :: Database",
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 2",
                 "License :: OSI Approved :: BSD License",
                 "Operating System :: OS Independent",
                 "Intended Audience :: Developers",
                 "Development Status :: 2 - Pre-Alpha"],
    author="Masroor Ehsan Choudhury",
    author_email="masroore@gmail.com",
    description="A simple wrapper for Python psycopg2",
    long_description=long_description,
    license="BSD",
    keywords="psycopg2 postgresql sql database",
    url="https://github.com/masroore/pg_simple",
)