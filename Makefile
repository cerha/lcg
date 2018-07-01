.PHONY: translations doc test

all: compile translations

compile:
	@echo "Compiling Python libraries from source..."
	@python -c "import compileall; compileall.compile_dir('lib')" >/dev/null
	@python -O -c "import compileall; compileall.compile_dir('lib')" >/dev/null

translations:
	make -C translations

extract:
	make -C translations extract

doc:
	LCGDIR=. PYTHONPATH="./lib:${PYTHONPATH}" bin/lcgmake.py doc/src doc/html

test:
	python -m pytest lib/lcg/_test.py

coverage:
	LCGDIR=. PYTHONPATH="./lib:${PYTHONPATH}" coverage run --source=lib/lcg lib/lcg/_test.py
	coverage report

deps-dev:
	pip2 install flake8
	npm install

lint: lint-flake8 lint-eslint

lint-flake8:
	flake8 lib bin

lint-eslint:
	npm run eslint resources/scripts/{flash,lcg-exercises,lcg}.js

lint-csslint:
	npm run csslint resources/css
