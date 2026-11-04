Changelog rules
===============

User visible changes are recorded in [`changelog.md`](../../changelog.md) in
the root of the repository, following the
[changelog rules of Pytis](https://github.com/cerha/pytis/blob/master/doc/standards/changelog.md).
This document only adds or overrides the rules specific to LCG.

**Audience**

- The developers of applications using LCG (including Pytis and Wiking) and
  the readers of the documents produced by LCG (such as the users of the
  JavaScript widgets in HTML output).

**Subsections**

- Subsections by area, in this order:
  - `### Common` -- content elements, structured text and other readers,
    localization, utilities, the `lcg.make` tool, packaging and
    dependencies,
  - `### HTML` -- HTML export and generator, JavaScript widgets and style
    sheets,
  - `### Other formats` -- PDF, EPUB, Braille, plain text and other export
    formats.
- The section `### HTML` ends with the subsection `#### Accessibility`
  listing all changes related to accessibility.  These changes are not
  repeated elsewhere.
- LCG is used by Pytis and Wiking, whose changelogs record the changes of
  LCG visible to their users and the required LCG versions.  When a change of
  LCG is made for them, its entry here describes it generally, without
  referring to them.
