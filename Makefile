src = data/intermediate
dst = out/intermediate
stylesheet = style.css

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
	unison
