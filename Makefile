.PHONY: translations doc test

export LCGDIR=.

all: compile translations

compile:
	python -m compileall -d . lcg
	python -O -m compileall -d . lcg

translations:
	make -C translations

extract:
	make -C translations extract

doc:
	python -m lcg.make doc/src doc/html

test:
	python -m pytest lcg/test.py

# Only for development installs.  Use pip for production/user installs.
install:
	flit install --symlink

coverage:
	coverage run --source=lcg -m pytest lcg/test.py
	coverage report

lint: lint-flake8 lint-eslint

lint-flake8:
	flake8 lcg bin

lint-eslint:
	npm run eslint resources/scripts/{flash,lcg-exercises,lcg}.js

lint-csslint:
	npm run csslint resources/css
