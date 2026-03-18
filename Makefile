.PHONY: doc test translations resources javascript

js_src := $(wildcard javascript/*.js)
js_out := $(js_src:javascript/%.js=lcg/resources/scripts/%.js)

all: compile translations resources

compile:
	python -m compileall -d . lcg
	python -O -m compileall -d . lcg

translations:
	make -C translations

extract:
	make -C translations extract

javascript: $(js_out)

lcg/resources/scripts/%.js: javascript/%.js
	mkdir -p $(@D)
	python3 -m rjsmin < $< > $@

resources:
	git ls-files resources | rsync -av --delete --files-from=- ./ lcg/

doc: resources
	python -m lcg.make doc/src doc/html

test:
	python -m pytest lcg/test.py -v

build: translations resources
	flit build

publish:
	python -m twine upload --repository pypi dist/*.whl

publish-test:
	python -m twine upload --repository testpypi dist/*.whl

install:
        # Only for development installs.  Use pip for production/user installs.
	flit install --symlink

clean:
	rm -rf dist lcg/resources doc/html
	make -C translations clean

coverage:
	coverage run --source=lcg -m pytest lcg/test.py
	coverage report

lint: lint-flake8 lint-eslint

lint-flake8:
	flake8 lcg bin

lint-eslint:
	npm run eslint javascript/{lcg-exercises,lcg}.js

lint-csslint:
	npm run csslint resources/css
