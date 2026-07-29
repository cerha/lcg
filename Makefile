.PHONY: all update resources sync-resources sync-doc clean-obsolete javascript translations extract doc test build check-release publish publish-test install clean coverage lint lint-flake8 lint-eslint

js_src := $(wildcard javascript/*.js)
js_out := $(js_src:javascript/%.js=lcg/assets/resources/scripts/%.js)

all: doc update

update: clean-obsolete translations resources sync-doc

# The generated data directories moved under 'assets'.  Working copies created
# before that still contain them in their former locations, where they are no
# longer ignored by git, so they break the sdist build.  This target may be
# removed once all the working copies around are rebuilt.
clean-obsolete:
	rm -rf lcg/resources lcg/translations lcg/doc

resources: sync-resources javascript

sync-resources:
	git ls-files resources | rsync -a --info=name --delete --files-from=- ./ lcg/assets/

sync-doc:
	git -C doc/src ls-files | rsync -a --info=name --delete --files-from=- doc/src/ lcg/assets/doc/

javascript: $(js_out)

lcg/assets/resources/scripts/%.js: javascript/%.js
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

# The files uploaded by the publishing targets below -- the wheel and the
# source distribution, both created by the build.
published := dist/*

# Refuse to publish anything but a committed release, as the upload can not be
# taken back.  Release commits are titled 'Release <version>' by convention.
check-release:
	@git diff --quiet && git diff --cached --quiet || \
	    { echo "The working tree has uncommitted changes."; exit 1; }
	@git log -1 --format=%s | grep -q '^Release ' || \
	    { echo "The last commit is not a release."; exit 1; }

# Both publishing targets rebuild from scratch, so that only the files of the
# current version are in 'dist' and thus uploaded.  Uploading to PyPI is
# irreversible (the same version can never be uploaded again), so it asks
# before it proceeds.
publish: check-release
	rm -rf dist
	$(MAKE) build
	@echo
	@echo "The following files will be uploaded to PyPI:"
	@ls $(published)
	@echo
	@read -p "Proceed? [y/N] " answer && [ "$$answer" = y ]
	python -m twine upload --repository pypi $(published)

publish-test:
	rm -rf dist
	$(MAKE) build
	python -m twine upload --repository testpypi $(published)

install:
	# Only for development installs.  Use pip for production/user installs.
	flit install --symlink

clean: clean-obsolete
	rm -rf dist lcg/assets doc/html
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
