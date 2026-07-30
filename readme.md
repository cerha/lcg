# LCG Framework

[![PyPI](https://img.shields.io/pypi/v/lcg-framework.svg)](https://pypi.org/project/lcg-framework/)
[![Tests](https://github.com/cerha/lcg/actions/workflows/tests.yml/badge.svg)](https://github.com/cerha/lcg/actions/workflows/tests.yml)

**LCG** is a Python framework for content abstraction and generic document
processing.  A document is built as a hierarchy of Python objects, independent
of any output format, and exported to HTML, PDF, EPUB, Braille and others.

It is meant for developers who need to produce structured documents
programmatically -- or read them from a source format -- and publish them in
several formats at once.  It can also be used directly, as a command line tool
turning documents written in a human readable markup into the target format.


## What LCG provides

- **One document, many formats.**  Write the content once and export it to
  HTML, PDF, EPUB, plain text, MS HTML Help or an IMS package for e-learning
  systems.  Each exporter can be extended or replaced.
- **Content, not markup.**  Documents are composed of content elements --
  paragraphs, sections, tables, definition lists, quotations, figures,
  mathematics (MathML), inline SVG, plots, audio and video.  Custom elements
  are just new classes, so the framework grows with the application.
- **Braille output that means it.**  Text is translated through
  [liblouis](https://liblouis.io) with the document layout handled by
  louisutdml, and mathematics is transcribed in the Nemeth code.  Documents can
  be embossed, not just approximated.
- **Accessibility as a design goal.**  The HTML output follows the W3C
  standards, and the interactive widgets -- foldable trees, notebooks, popup
  menus, collapsible sections, an audio player -- are operable by keyboard and
  announced properly by screen readers.
- **Internationalization beyond gettext.**  Translation is deferred until
  export, so one document tree serves several language variants and may mix
  languages within a single page.  Dates, times, decimal and monetary values
  are localized, plural forms included.
- **Presentation kept apart.**  Layout and styling are described by
  presentation sets matched against the content, so the same document can be
  published in different looks without touching it.
- **E-learning exercises.**  Multiple choice questions, selections, true/false
  statements, gap filling and other interactive exercise types are built in --
  the framework's original purpose, still supported.


## License

LCG is Free Software, distributed under the terms of the **GNU General Public
License v2 (GPLv2)**.  See the `COPYING` file for details.


## History

**LCG** stands for *Learning Content Generator*.  It was initially developed to
generate online e-learning material for the [Eurochance project](https://langschool.eu).


## Changelog

For a history of changes in each version, see the
[changelog](https://github.com/cerha/lcg/blob/master/changelog.md).


## Installation

LCG is a pure Python library running on Python 2.7 or Python 3.5 or later and
may be installed by `pip install lcg-framework[all]`.

When using PDF output, you additionally need the following system packages:
- Fontconfig (Debian/Ubuntu package `fontconfig`)
- Freefont (Debian/Ubuntu package `fonts-freefont-ttf` or `ttf-freefont`)


## Usage

LCG comes with a command line tool which can be run directly using `python -m
lcg.make` to build and export documents into different output formats.  Run
with `--help` to find out how to use it.

LCG is also used as a content abstraction layer in the
[Wiking](https://github.com/cerha/wiking) web application development framework
and for document construction and as a print backend in
[Pytis](https://github.com/cerha/pytis) information systems development
framework.


## Documentation

The documentation is published at
[cerha.github.io/lcg](https://cerha.github.io/lcg/).

Its source is also included in the package.  To generate the HTML version
locally, run `make doc` from the package root directory.
