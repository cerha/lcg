MO_FILES = $(patsubst %.po,%/LC_MESSAGES/lcg.mo,$(shell ls *.po))
LCG_SOURCE_FILES = $(shell ls ../lcg/*.py)

.PHONY: all

all: $(MO_FILES)

%/LC_MESSAGES/lcg.mo: %.po %/LC_MESSAGES
	msgfmt -v $< -o $@
%/LC_MESSAGES: 
	mkdir -p $*/LC_MESSAGES/

%.po: translations.pot
	msgmerge --quiet --update $@ $< 

translations.pot: $(LCG_SOURCE_FILES)
	xgettext $(LCG_SOURCE_FILES) -o translations.pot