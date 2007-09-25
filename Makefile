# Edit the paths below to suit your needs.
LIB = /usr/local/lib/python%d.%d/site-packages
SHARE = /usr/local/share
BIN = /usr/local/bin

lib := $(shell python -c 'import sys; print "$(LIB)".find("%d") != -1 and \
	                 "$(LIB)" % sys.version_info[:2] or "$(LIB)"')

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

check-lib:
	@echo -e "import sys\nif '$(lib)' not in sys.path: sys.exit(1)" \
	| python || echo 'WARNING: $(lib) not in Python path!'

install: check-lib $(SHARE)/lcg
	cp -ruv doc resources translations $(SHARE)/lcg
	cp -ruv lib/lcg $(lib)
	cp -u bin/lcgmake.py $(BIN)/lcgmake

uninstall:
	rm -rf $(SHARE)/lcg
	rm -rf $(lib)/lcg
	cp -f $(BIN)/lcgmake

$(SHARE)/lcg:
	mkdir $(SHARE)/lcg

cvs-install: check-lib compile translations link-lib link-bin link-share

link-lib:
	@if [ -d $(lib)/lcg ]; then echo "$(lib)/lcg already exists!"; \
	else echo "Linking LCG libraries to $(lib)/lcg"; \
	ln -s $(CURDIR)/lib/lcg $(lib)/lcg; fi

link-bin:
	@if [ -f $(BIN)/lcg-make ]; then echo "$(BIN)/lcg-make already exists!"; \
	else echo "Linking LCG make to $(BIN)/lcg-make"; \
	ln -s $(CURDIR)/bin/lcgmake.py $(BIN)/lcg-make; fi

link-share: link-share-doc link-share-translations link-share-resources

link-share-%: $(SHARE)/lcg
	@if [ -d $(SHARE)/lcg/$* ]; then echo "$(SHARE)/lcg/$* already exists!"; \
	else echo "Linking $* to $(SHARE)/lcg"; \
	ln -s $(CURDIR)/$* $(SHARE)/lcg; fi

cvs-update: do-cvs-update compile translations

do-cvs-update:
	cvs update -dP

version = $(shell echo 'import lcg; print lcg.__version__' | python)
dir = lcg-$(version)
file = lcg-$(version).tar.gz

compile:
	@echo "Compiling Python libraries from source..."
	@python -c "import compileall; compileall.compile_dir('lib')" >/dev/null

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