domains := lcg lcg-exercises eurochance test
mo_files := $(shell ls *.po | sed 's/\(.*\)\.\(.*\)\.po/\2\/LC_MESSAGES\/\1.mo/')

all: $(mo_files)

include $(domains:%=%.d)

%.d: $(shell python ../lib/lcg/i18n.py)
	@echo "Updating rules for domain $*."
	@echo -n "$*.pot: " > $@ && python ../lib/lcg/i18n.py $* >> $@
	@echo "$(wildcard $*.*.po): $*.%.po: $*.pot" >> $@
	@echo "$(filter %/$*.mo,$(mo_files)): %/LC_MESSAGES/$*.mo: $*.%.po %/LC_MESSAGES" >> $@

%/LC_MESSAGES:
	mkdir -p $*/LC_MESSAGES/

%.mo:
	msgfmt -v $< -o $@

%.po:
	msgmerge -q --update $@ $< && touch $@

%.pot:
	xgettext $^ -o $@
