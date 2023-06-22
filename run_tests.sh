#!/bin/bash

set -o errexit

echo ----- running black
black --check .
echo
echo ----- running isort
isort --check .
echo
echo ----- running flake8
flake8 .
echo
echo ----- running mypy
mypy .
echo
echo ----- running pytest
pytest
