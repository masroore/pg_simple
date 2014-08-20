#!/bin/sh

CWD=$(pwd)
echo "Generating README.rst"
pandoc --from=markdown --to=rst --toc --output=README.rst README.md

echo "Building and updloading python egg"
python setup.py sdist bdist_egg upload

echo "Generating HTML documentation"
cd docs
make html

echo "Creating HTML documentation package"
cd _build/html
zip -r ${CWD}/pg_simple_doc.zip .

echo "Done"
cd ${CWD}