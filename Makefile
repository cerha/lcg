SRC = data/$(LANG)/intermediate
DST = output/$(LANG)/intermediate

REMOTE_HOST = cesnet
REMOTE_DIR = /var/www/hosts/eurochance.brailcom.org/share/lcg
RSYNC_OPTS = -avC -e ssh --copy-unsafe-links --exclude "*~"

export LCG_TTS_COMMAND = festival_client --ttw 2>/dev/null
export LCG_OGG_COMMAND = oggenc -q 2 --quiet - -o -
export LCG_MP3_COMMAND = lame --quiet - -

TEXT_DOMAIN = lcg
MO_FILES = $(patsubst translations/%.po,\
             translations/%/LC_MESSAGES/$(TEXT_DOMAIN).mo,\
             $(shell ls translations/*.po))
POT_FILE = translations/translations.pot
LCG_SOURCE_FILES = $(shell ls lcg/*.py)

# The target name is the course language
LANG = $@

.PHONY: translations all en de

all: en de

en de:
	rm -f $(DST)/*.html
	bin/generate.py $(SRC) $(DST) $(LANG)
#	rm -f $(DST)/intermediate.zip
#	(cd $(DST); zip -qr intermediate.zip .)

de: translations

translations: $(MO_FILES)

translations/%/LC_MESSAGES/$(TEXT_DOMAIN).mo: translations/%.po translations/%/LC_MESSAGES
	msgfmt -v $< -o $@
translations/%/LC_MESSAGES: 
	mkdir -p translations/$*/LC_MESSAGES/

translations/%.po: $(POT_FILE)
	msgmerge --quiet --update $@ $< 

$(POT_FILE): $(LCG_SOURCE_FILES)
	xgettext $(LCG_SOURCE_FILES) -o $@

test:
	lcg/_test.py

sync:
	rsync $(RSYNC_OPTS) --delete doc output $(REMOTE_HOST):$(REMOTE_DIR)/
	ssh $(REMOTE_HOST) "cd $(REMOTE_DIR);chmod -R g+w .;chgrp -R www-data ."

# unison ?
sync-data:
	rsync $(RSYNC_OPTS) --update data $(REMOTE_HOST):$(REMOTE_DIR)/
	rsync $(RSYNC_OPTS) --update $(REMOTE_HOST):$(REMOTE_DIR)/data .
	ssh $(REMOTE_HOST) "cd $(REMOTE_DIR);chmod -R g+w .;chgrp -R www-data ."
