mo_files := $(shell ls *.po | sed 's/\(.*\)\.\(.*\)\.po/\2\/LC_MESSAGES\/\1.mo/')
#resource_po_files := $(patsubst lcg.%.po,../resources/translations/lcg.%.po,$(shell ls lcg.*.po))


all: $(mo_files)


lcg.pot: $(shell find ../lib -name "*.py" -not -name "_test.py" -not -name "exercises*.py")
	pybabel extract -F lcg.cfg --add-comments=Translators: -s ../ -o lcg.pot

lcg-exercises.pot: ../lib/lcg/exercises.py ../lib/lcg/export/exercises_*.py
	pybabel extract -F lcg-exercises.cfg --add-comments=Translators: -s ../ -o lcg-exercises.pot

test.pot: ../lib/lcg/_test.py
	pybabel extract -F test.cfg --add-comments=Translators: -s ../ -o test.pot

%/LC_MESSAGES:
	mkdir -p $*/LC_MESSAGES/

%/LC_MESSAGES/lcg.mo: lcg.%.po %/LC_MESSAGES
	msgfmt -v $< -o $@

$(shell ls lcg.*.po): lcg.%.po: lcg.pot
	msgmerge -q --backup=none --update $@ $< && touch $@

%/LC_MESSAGES/lcg-exercises.mo: lcg-exercises.%.po %/LC_MESSAGES
	msgfmt -v $< -o $@

$(shell ls lcg-exercises.*.po): lcg-exercises.%.po: lcg-exercises.pot
	msgmerge -q --backup=none --update $@ $< && touch $@

%/LC_MESSAGES/test.mo: test.%.po %/LC_MESSAGES
	msgfmt -v $< -o $@

$(shell ls test.*.po): test.%.po: test.pot
	msgmerge -q --backup=none --update $@ $< && touch $@


#../resources/translations:
#	mkdir -p ../resources/translations/
#
#../resources/translations/lcg.%.po: lcg.%.po ../resources/translations
#	cp $< $@

clean:
	rm -f *.pot
#	rm -rf ../resources/translations/

.PHONY: all clean
