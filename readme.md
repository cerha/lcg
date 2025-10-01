# LCG Framework

[![Tests](https://github.com/cerha/lcg/actions/workflows/tests.yml/badge.svg)](https://github.com/cerha/lcg/actions/workflows/tests.yml)

**LCG** is a Python framework for content abstraction and generic document
processing.  Documents are constructed as a hierarchy of Python objects.  LCG
defines standard content elements (paragraphs, sections, lists, formatted text,
etc.) and advanced constructs (multimedia, mathematics, interactive widgets),
and supports extensibility through third-party content elements.  Content can be
exported to multiple formats (HTML, PDF, Braille, IMS, EPUB, etc.) and imported
from various source formats (text markup, internal serialization, etc.).

LCG is primarily intended for software developers who need to programmatically
build structured documents or import them from different sources and export
them to multiple formats.  Documents can contain generic content elements
(defined by LCG) or custom elements (defined by the developer).  LCG can also be
used directly by end-users to process documents written in a simple,
human-readable source format into various target formats (such as HTML or PDF).


## Key Features

- **Separation of content and presentation**: Keeps structure and formatting
  independent.
- **Multimedia and interactive content**: Supports rich, dynamic elements.
- **Accessibility**: Designed for users of assistive technologies.
- **Extensibility**: Easily define new content elements or customize output for
  existing elements.
- **Standards compliance**: Adheres to relevant standards, notably W3C specs.
- **Internationalization**: Supports multiple language variants in one document
  and mixed-language content.


## License

LCG is Free Software, distributed under the terms of the **GNU General Public
License v2 (GPLv2)**.  See the `COPYING` file for details.


## History

**LCG** stands for *Learning Content Generator*.  It was initially developed to
generate online e-learning material for the [Eurochance project](https://langschool.eu).


## Changelog

For a history of changes in each version, see the
[changelog](https://github.com/cerha/lcg/blob/main/changelog.md).


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

Documentation is included in the package.  To generate the HTML version, run
`make doc` from the package root directory.
