LCG Installation Instructions

Dependencies:

  * Python 2.6 or later 2.x.

  * To use the PDF output, you also need:
    - Python module `reportlab',
    - Fontconfig (the package name in Debian is `fontconfig'),
    - the default font `Freefont' if you don't specify another font explicitly.
      (the package is ttf-freefont in Debian and fonts-freefont-ttf in Ubuntu)

  * To use the Braille output, you also need:
    - Python module `louise' (for liblouise 2.5.4)

The currently supported model of using LCG is running it directly out of the
checked out tree, being able to check out a newer version at any time and using
this new version right away.  The provided Makefile will update the generated
files after checking out new versions of source files, so you need to run
'make' after each checkout.  LCG is a pure Python library so the setup is quite
simple.  Two typical use cases are described below.

WIKING WEB APPLICATIONS

LCG is often used in web applications in combination with Pytis and Wiking
which use the same approach and their versions typically need to be
synchronized.  You will need to setup the web application to find LCG's `lib'
subdirectory in its Python path and set the following Wiking configuration
options:
  - `resource_path' to include the LCG's `resources' subdirectory
  - `translation_path' to include the `translations' subdirectory
  - `doc_dirs' to map `lcg' to `doc/src' subdirectory

STANDALONE USAGE

To use LCG as a standalone program, you need too setup your environment to find
LCG.  Let's suppose that you have unpacked LCG to `/home/bob/lcg':

  1. Create or update the generated files from the source files (this step can
     be omitted if you downloaded an LCG release package).

     $ make all

  2. Tell Python where to find the libraries:

     $ export PYTHONPATH=/home/bob/lcg/lib:$PYTHONPATH

  3. Tell LCG where to find its data:

     $ export LCGDIR=/home/bob/lcg

  4. If you need to use LCG executables, such as `lcgmake.py', use their full
     path, link them manually somewhere to your PATH or setup your PATH to
     include the LCG's `bin' subdirectory:
     	     
     $ export PATH=/home/bob/lcg/bin:$PATH

