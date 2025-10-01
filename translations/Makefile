# Generate/update translation files after code changes.
#
# The target 'extract' is used by developers after code changes to update the
# PO files which are controlled by git.  PO files must be committed in separate
# commits named 'Update translations' after code changes which add, remove or
# update translatable strings (other changes may change line number references
# in PO files, but don't need to be comitted all the time).
#
# The target 'all' (the default) is used to create/update MO files after PO
# file changes.  The top level Makefile will run this target in this directory
# when make all is executed at top level.  This allows updating MO files for
# deployment (such as before building a package for distribution).  In this
# case we want to avoid updating PO files, because the updated PO files would
# cause conflicts on next git pull (PO files are git controlled).  We need just
# the git versions of PO files to create/update MO files.

domains := lcg lcg-exercises test
mo_dir := ../lcg/translations
mo_files := $(foreach d, $(domains), $(patsubst $(d).%.po,\
                                       $(mo_dir)/%/LC_MESSAGES/$(d).mo,\
                                       $(wildcard $(d).*.po)))
pot_files := $(patsubst %,%.pot,$(domains))

#resource_po_files := $(patsubst %.po,../resources/translations/%.po, $(wildcard *.po))

all: $(mo_files)
extract: $(wildcard *.po) $(pot_files) $(mo_files)

ifeq ($(MAKECMDGOALS),extract)

# Get a list of matching source files for given domain (to be used as dependencies).
# This allows avoiding duplication of the filename patterns defined in *.cfg.
define sources
$(shell pybabel extract -F $1.cfg -s .. -o /dev/null 2>&1
  | grep '^extracting messages from '
  | sed 's/^extracting messages from //')
endef

lcg.pot: $(call sources, lcg)
lcg-exercises.pot: $(call sources, lcg-exercises)
test.pot: $(call sources, test)

%.pot: %.cfg
	pybabel extract -F $< --add-comments=Translators: -s .. -o $@

$(wildcard lcg.*.po): lcg.%.po: lcg.pot
$(wildcard lcg-exercises.*.po): lcg-exercises.%.po: lcg-exercises.pot
$(wildcard test.*.po): test.%.po: test.pot

$(wildcard *.po):
	msgmerge -q --backup=none --update $@ $< && touch $@

endif

$(mo_dir)/%/LC_MESSAGES/lcg.mo: lcg.%.po
	@mkdir -p $(dir $@)
	msgfmt -v $< -o $@
$(mo_dir)/%/LC_MESSAGES/lcg-exercises.mo: lcg-exercises.%.po
	@mkdir -p $(dir $@)
	msgfmt -v $< -o $@
$(mo_dir)/%/LC_MESSAGES/test.mo: test.%.po
	@mkdir -p $(dir $@)
	msgfmt -v $< -o $@

#../resources/translations/lcg.%.po: lcg.%.po
#	@mkdir -p ../resources/translations/
#	cp $< $@

clean:
	rm -rf *.pot $(mo_dir)

.PHONY: all extract clean
