# Generate/update translation files after code changes.
#
# The target 'extract' is used by developers after code changes
# to update the PO files which are controlled by git.  PO files
# must be committed in separate commits named 'Update translations'
# after code changes which add, remove or update translatable strings
# (other changes may change line number references in PO files, but
# don't need to be comitted all the time).
#
# The target 'all' (the default) is used to create/update MO files
# after PO file changes.  The top level Makefile will run this target
# in this directory when make all is executed at top level.  This
# allows updating MO files in deployment environment after git pull.
# In this case we want to avoid updating PO files, because the
# updated PO files would cause conflicts on next git pull (PO files
# are git controlled).  We need just the git versions of PO files
# to create/update MO files.

mo_dir := ../lcg/translations
mo_files := $(foreach d, lcg lcg-exercises test, \
              $(patsubst $(d).%.po,$(mo_dir)/%/LC_MESSAGES/$(d).mo, \
              $(wildcard $(d).*.po)))
#resource_po_files := $(patsubst %.po,../resources/translations/%.po, $(wildcard *.po))

all: $(mo_files)
extract: $(wildcard *.po) $(mo_files)

ifeq ($(MAKECMDGOALS),extract)

lcg.pot: $(shell find ../lib -name "*.py" -not -name "test.py" -not -name "exercises*.py")
lcg-exercises.pot: ../lib/lcg/exercises.py ../lib/lcg/export/exercises_*.py
test.pot: ../lib/lcg/test.py
$(wildcard *.pot):
	pybabel extract -F $(patsubst %.pot,%.cfg,$@) --add-comments=Translators: -s ../ -o $@

$(wildcard lcg.*.po): lcg.%.po: lcg.pot
$(wildcard lcg-exercises.*.po): lcg-exercises.%.po: lcg-exercises.pot
$(wildcard test.*.po): test.%.po: test.pot
$(wildcard *.po):
	msgmerge -q --backup=none --update $@ $< && touch $@

endif

$(mo_dir)/%/LC_MESSAGES:
	mkdir -p $(mo_dir)/$*/LC_MESSAGES/
$(mo_dir)/%/LC_MESSAGES/lcg.mo: lcg.%.po $(mo_dir)/%/LC_MESSAGES
	msgfmt -v $< -o $@
$(mo_dir)/%/LC_MESSAGES/lcg-exercises.mo: lcg-exercises.%.po $(mo_dir)/%/LC_MESSAGES
	msgfmt -v $< -o $@
$(mo_dir)/%/LC_MESSAGES/test.mo: test.%.po $(mo_dir)/%/LC_MESSAGES
	msgfmt -v $< -o $@

#../resources/translations:
#	mkdir -p ../resources/translations/
#
#../resources/translations/lcg.%.po: lcg.%.po ../resources/translations
#	cp $< $@

clean:
	rm -f *.pot
	rm -rf $(mo_dir)

.PHONY: all clean

# Prevent make from trying to remove the directories.
.PRECIOUS: $(mo_dir)/%/LC_MESSAGES
