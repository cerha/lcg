src = data/intermediate
dst = out/intermediate

LCG_TTS_COMMAND = echo "%(text)s" | festival_client --ttw 2>/dev/null | oggenc -q 2 --quiet - -o %(file)s

all:
	rm -f $(dst)/*.html
	bin/generate.py $(src) $(dst)
#	rm -f $(dst)/intermediate.zip
#	(cd $(dst); zip -qr intermediate.zip .)

test:
	lcg/_test.py

sync:
	unison
