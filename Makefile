src = data/intermediate
dst = out/intermediate

LCG_TTS_COMMAND = echo "%(text)s" | festival_client --ttw | oggenc -q 2 --quiet - -o %(file)s

all:
	bin/generate.py $(src) $(dst)
	(cd $(dst); rm -f ../intermediate.zip; zip -qr ../intermediate.zip .)

test:
	lcg/_test.py

