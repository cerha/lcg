# You may edit the paths below to suit your needs.
LIB = /usr/local/lib/python2.4/site-packages
SHARE = /usr/local/share
BIN = /usr/local/bin


.PHONY: translations doc test

doc:
	LCGDIR=. bin/lcgmake.py --stylesheet=default.css doc html

translations:
	make -C translations

test:
	lib/lcg/_test.py

tags:
	rm -f TAGS
	find -name '*.py' -not -name '_test.py' | xargs etags --append --regex='/^[ \t]+def[ \t]+\([a-zA-Z_0-9]+\)/\1/'

install: $(SHARE)/lcg
	cp -ruv doc resources translations $(SHARE)/lcg
	cp -ruv lib/lcg $(LIB)
	cp -u bin/lcgmake.py $(BIN)/lcgmake

uninstall:
	rm -rf $(SHARE)/lcg
	rm -rf $(LIB)/lcg
	cp -f $(BIN)/lcgmake

$(SHARE)/lcg:
	mkdir $(SHARE)/lcg

version = $(shell echo 'import lcg; print lcg.__version__' | python)
dir = lcg-$(version)
file = lcg-$(version).tar.gz

compile:
	python -c "import compileall; compileall.compile_dir('lib')"

release: compile translations
	@ln -s .. releases/$(dir)
	@if [ -e releases/$(file) ]; then \
	   echo "Removing old file $(file)"; rm releases/$(file); fi
	@echo "Generating $(file)..."
	@(cd releases; tar --exclude "CVS" --exclude "*~" --exclude "#*" \
	     --exclude ".#*" --exclude "*.pyo" \
	     --exclude .cvsignore --exclude html --exclude releases \
	     -czhf $(file) $(dir))
	@rm releases/$(dir)