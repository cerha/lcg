export LCGDIR = .

.PHONY: translations doc test

doc:
	bin/lcgmake.py --stylesheet=default.css doc html

translations:
	make -C translations

test:
	lib/lcg/_test.py

tags:
	rm -f TAGS
	find -name '*.py' -not -name '_test.py' | xargs etags --append --regex='/^[ \t]+def[ \t]+\([a-zA-Z_0-9]+\)/\1/'
