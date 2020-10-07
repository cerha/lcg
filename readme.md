LCG framework
=============

LCG is a Python framework for content abstraction and generic document
processing.  Documents can be constructed as a structure of Python objects.
LCG defines standard content elements (paragraphs, sections, formatted text,
etc...) as well as many advanced constructs (multimedia, mathematics,
interactive widgets) and supports extensibility through definition of third
party content elements.  Content can be exported into different output formats,
such as HTML, PDF, Braille, IMS, EPUB and others and imported from different
source formats (text markup, internal serialization, etc.).

LCG is mostly a tool for software developers who need to build structured
documents programatically or import them from different source formats and want
to export those documents into different output formats.  These documents can
consist of generic content elements (defined by LCG itself) or custom content
elements (defined by the developer).  LCG can also be directly used by end
users as a tool for processing documents written in a simple and well readable
source format into various target formats (such as HTML or PDF).

Some key requirements leading to developing LCG were:
* True separation of content and its presentation.
* Support for multimedia and interactive content.
* Accessibility for users of assistive technologies.
* Extensibility allowing definition of new content elements and customizing the
  output presentation of pre-defined elements.
* Respect to standards (namely W3C standards for the relevant output formats).
* Internationalization (support for several language variants of one document,
  as well as intermixing more languages in one document).

LCG is a Free Software distributed under the terms of GNU General Public
License.

The name LCG comes from Learning Content Generator as LCG was initially
developed to generate on-line e-learning courses for the Eurochance project
(https://langschool.eu).

LCG is used as content abstraction layer in Wiking
(https://github.com/cerha/wiking) web application development framework.

LCG documentation is included in the package.  To generate the HTML version run
"make doc" within the package root directory.
