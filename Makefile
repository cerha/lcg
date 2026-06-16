.PHONY: all update resources sync-resources javascript translations extract doc test build install clean coverage lint lint-flake8 lint-eslint

js_src := $(wildcard javascript/*.js)
js_out := $(js_src:javascript/%.js=lcg/resources/scripts/%.js)

all: doc update

update: translations resources

resources: sync-resources javascript

sync-resources:
	git ls-files resources | rsync -av --delete --files-from=- ./ lcg/

javascript: $(js_out)

lcg/resources/scripts/%.js: javascript/%.js
	mkdir -p $(@D)
	python3 -m rjsmin < $< > $@

translations:
	make -C translations

extract:
	make -C translations extract

doc: resources
	python -m lcg.make doc/src doc/html

test:
	python -m pytest lcg/test.py -v

build: update
	# Beware: Use explicitly 'python3' in build and depending targets
	# to make sure the wheel is built correctly within the Python2 test
	# workflow (flit is not available for Python 2).
	python3 -m flit build

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
