# Edit the paths below to suit your needs.
LIB = /usr/local/lib/python%d.%d/site-packages
SHARE = /usr/local/share
BIN = /usr/local/bin

lib := $(shell python -c 'import sys; print "$(LIB)".find("%d") != -1 and \
	                 "$(LIB)" % sys.version_info[:2] or "$(LIB)"')

.PHONY: translations doc test

all: check compile translations

check:
	@python -c "import sys; '$(lib)' not in sys.path and sys.exit(1)" || \
           echo 'WARNING: $(lib) not in Python path!'

compile:
	@echo "Compiling Python libraries from source..."
	@python -c "import compileall; compileall.compile_dir('lib')" >/dev/null

translations:
	make -C translations

doc:
	LCGDIR=. PYTHONPATH="./lib:${PYTHONPATH}" bin/lcgmake.py doc/src doc/html

test:
	lib/lcg/_test.py

tags:
	rm -f TAGS
	find -name '*.py' -not -name '_test.py' | xargs etags --append --regex='/^[ \t]+def[ \t]+\([a-zA-Z_0-9]+\)/\1/'

install: $(SHARE)/lcg
	cp -ruv doc resources translations $(SHARE)/lcg
	cp -ruv lib/lcg $(lib)
	cp -u bin/lcgmake.py $(BIN)/lcgmake

uninstall:
	rm -rf $(SHARE)/lcg
	rm -rf $(lib)/lcg
	cp -f $(BIN)/lcgmake

install-links: link-lib link-bin link-share

link-lib:
	@if [ -d $(lib)/lcg ]; then echo "$(lib)/lcg already exists!"; \
	else echo "Linking LCG libraries to $(lib)/lcg"; \
	ln -s $(CURDIR)/lib/lcg $(lib)/lcg; fi

link-bin:
	@if [ -f $(BIN)/lcgmake ]; then echo "$(BIN)/lcgmake already exists!"; \
	else echo "Linking LCG make to $(BIN)/lcgmake"; \
	ln -s $(CURDIR)/bin/lcgmake.py $(BIN)/lcgmake; fi

link-share: link-share-doc link-share-translations link-share-resources

link-share-%: $(SHARE)/lcg
	@if [ -d $(SHARE)/lcg/$* ]; then echo "$(SHARE)/lcg/$* already exists!"; \
	else echo "Linking $* to $(SHARE)/lcg"; \
	ln -s $(CURDIR)/$* $(SHARE)/lcg; fi

$(SHARE)/lcg:
	mkdir $(SHARE)/lcg

version = $(shell echo 'import lcg; print lcg.__version__' | python)
dir = lcg-$(version)
file = lcg-$(version).tar.gz

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