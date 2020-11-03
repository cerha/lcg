LCG Installation Instructions
=============================

LCG is a pure Python library running on Python 2.7 or Python 3.5 or later.  It
can be used directly from the checked out tree.  You need to:

  * Add the `lib` subdirectory to PYTHONPATH.
  * Run `make` after each checkout to update generated files.
  * Create a Python virtual environment and install required packages as
    described below.

All needed Python packages are defined in the file requirements.txt.
Some of the dependencies are optional and you may wish to edit the file
according to the features you are going to use (such as PDF or Braille output).
To install them run the following command in your virtual environment:

```
$ pip install -r requirements.txt
```

When using PDF output, you additionally need Fontconfig (the package
`fontconfig` in Debian) and the default font Freefont (the package
`ttf-freefont` in Debian and `fonts-freefont-ttf` in Ubuntu)

To use lcgmake.py you may also need to add the `bin` subdirectory to your PATH
and set the environment variable LCGDIR to the directory where you checked out
LCG.

```
$ export PATH=~/git/lcg/bin:$PATH
$ export LCGDIR=~/git/lcg
```
