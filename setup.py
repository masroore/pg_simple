import os

from setuptools import setup, find_packages

import pg_simple

try:
    with open(os.path.abspath('./README.rst')) as stream:
        long_description = stream.read()
except:
    long_description = 'pg_simple is a simple wrapper for Python psycopg2 with connection pooling'

setup(
    name=pg_simple.__name__,
    version=pg_simple.VERSION,
    packages=find_packages(),
    install_requires=['psycopg2'],
    classifiers=['Topic :: Database',
                 'Programming Language :: Python',
                 'Programming Language :: Python :: 2',
                 'Programming Language :: Python :: 2.6',
                 'Programming Language :: Python :: 2.7',
                 'License :: OSI Approved :: BSD License',
                 'Operating System :: OS Independent',
                 'Intended Audience :: Developers',
                 'Development Status :: 3 - Alpha'],
    author='Masroor Ehsan Choudhury',
    author_email='masroore@gmail.com',
    description='A simple wrapper for Python psycopg2 with connection pooling',
    long_description=long_description,
    license='BSD',
    keywords='psycopg2 postgresql sql database',
    url='https://github.com/masroore/pg_simple',
)