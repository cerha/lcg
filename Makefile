src = data/intermediate
dst = out/intermediate

all:
	bin/generate.py $(src) $(dst)
	(cd $(dst); rm -f ../intermediate.zip; zip -qr ../intermediate.zip .)

test:
	lcg/_test.py