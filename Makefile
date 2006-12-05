LIB = /usr/local/lib/python2.4/site-packages
SHARE = /usr/local/share

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

install: translations $(SHARE)/lcg
	cp -ruv doc resources translations $(SHARE)/lcg
	cp -ruv lib/lcg $(LIB)
	@# Create the *.pyc and *.pyo files
	PYTHONPATH=$(LIB) python -c "import lcg"
	PYTHONPATH=$(LIB) python -OO -c "import lcg"

uninstall:
	rm -rf $(SHARE)/lcg
	rm -rf $(LIB)/lcg

$(SHARE)/lcg:
	mkdir $(SHARE)/lcg

version := $(shell echo 'import lcg; print lcg.__version__' | python)
dir := lcg-$(version)
file := lcg-$(version).tar.gz

release: translations
	@ln -s .. releases/$(dir)
	@if [ -e releases/$(file) ]; then \
	   echo "Removing old file $(file)"; rm releases/$(file); fi
	@echo "Generating $(file)..."
	@(cd releases; tar --exclude "CVS" --exclude "*~" --exclude "#*" \
	     --exclude ".#*" --exclude "*.pyc" --exclude "*.pyo" \
	     --exclude .cvsignore --exclude html --exclude releases \
	     -czhf $(file) $(dir))
	@rm releases/$(dir)