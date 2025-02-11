check: shell-script-style check-python-format check-python-style python-test

PYTHON_FILES=$(wildcard *.py)
SH_SCRIPTS   = $(wildcard *.sh)
MAKEFILE_DIR:=$(strip $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST)))))

shell-script-style:
	shellcheck -x --format=gcc ${SH_SCRIPTS}

check-python-style:
	flake8 --color never --ignore E501,W503 ${PYTHON_FILES}
	pylint -f parseable ${PYTHON_FILES}

check-python-format:
	black --check ${PYTHON_FILES}

format-python:
	black ${PYTHON_FILES}

python-test:
	PYTHONPATH="${MAKEFILE_DIR}" pytest