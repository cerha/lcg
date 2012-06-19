domains := lcg test
mo_files := $(shell ls *.po | sed 's/\(.*\)\.\(.*\)\.po/\2\/LC_MESSAGES\/\1.mo/')

all: $(mo_files)

include $(domains:%=%.d)

lcg.pot: $(shell find ../lib -name "*.py" -not -name "_test.py*")

test.pot: ../lib/lcg/_test.py

%.d: $(shell find ../lib -name "*.py")
	@echo "Updating rules for domain $*."
	@echo "$(wildcard $*.*.po): $*.%.po: $*.pot" >> $@
	@echo "$(filter %/$*.mo,$(mo_files)): %/LC_MESSAGES/$*.mo: $*.%.po %/LC_MESSAGES" >> $@

%/LC_MESSAGES:
	mkdir -p $*/LC_MESSAGES/

%.mo:
	msgfmt -v $< -o $@

%.po:
	msgmerge --backup=none -q --update $@ $< && touch $@

%.pot:
	xgettext $^ --add-comments=Translators: -o $@

clean:
	rm -f *.d *.pot

.PHONY: all clean
