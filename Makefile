src = data/intermediate
dst = output/intermediate
stylesheet = style.css
remote_host = cesnet
remote_dir = /var/www/hosts/eurochance.brailcom.org/share/lcg/
rsync_opts = -avC -e ssh --copy-unsafe-links --exclude "*~"

LCG_TTS_COMMAND = echo "%(text)s" | festival_client --ttw 2>/dev/null | oggenc -q 2 --quiet - -o %(file)s

all:
	rm -f $(dst)/*.html
	export LCG_TTS_COMMAND='$(LCG_TTS_COMMAND)'
	bin/generate.py $(src) $(dst) $(stylesheet)
#	rm -f $(dst)/intermediate.zip
#	(cd $(dst); zip -qr intermediate.zip .)

tts-command:

test:
	lcg/_test.py

sync:
	rsync $(rsync_opts) --delete doc output $(remote_host):$(remote_dir)
	ssh $(remote_host) "cd $(remote_dir);chmod -R g+w .;chgrp -R www-data ."

# unison ?
sync-data:
	rsync $(rsync_opts) --update data $(remote_host):$(remote_dir)
	rsync $(rsync_opts) --update $(remote_host):$(remote_dir) data
	ssh $(remote_host) "cd $(remote_dir);chmod -R g+w .;chgrp -R www-data ."
