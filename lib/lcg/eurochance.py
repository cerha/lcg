# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005 Brailcom, o.p.s.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""A Concrete implemantation of Eurochance course structure.

This module defines classes which create the actual course from the source
data.  It can be used as an example of LCG usage.

"""

from lcg import *

class EurochanceNode(ContentNode):

    def __init__(self, *args, **kwargs):
        super(EurochanceNode, self).__init__(*args, **kwargs)
        self.resource(Stylesheet, 'default.css')

class Unit(EurochanceNode):
    """Unit is a collection of sections (Vocabulary, Grammar, Exercises...)."""
    _EXERCISE_SECTION_SPLITTER = re.compile(r"\r?\n====+\s*\r?\n")

    def _abbrev_title(self, abbrev=False):
        return _("Unit %d") % self._parent.index(self)

    def _title(self, abbrev=False):
        return self._read_file('title')

    def _read_xls_vocab(self):
        file = self._input_file('vocabulary', 'xls',
                                lang=self.root_node().users_language())
        command = 'xls2csv -q0 -c\| %s' % self._filename
        status, output = commands.getstatusoutput(command)
        if status: raise Exception(output)
        return 

    def _read_splittable_text(self, name, lang=None):
        filename = self._input_file(name, lang=lang)
        text = self._read_file(name, lang=lang)
        return SplittableText(text, input_file=filename)

    def _create_vocab(self):
        ulang = self.root_node().users_language()
        text = self._read_splittable_text('vocabulary', lang=ulang)
        f = feed.VocabFeeder(text, ulang, input_encoding=self._input_encoding)
        return f.feed(self)
    
    def _create_exercises(self):
        filename = self._input_file('exercises')
        text = self._read_file('exercises', comment='^//')
        splittable = SplittableText(text, input_file=filename)
        pieces = splittable.split(self._EXERCISE_SECTION_SPLITTER)
        assert len(pieces) == 5, \
               "%s: 5 sections expected, %d found." % (filename, len(pieces))
        titles = (_("Vocabulary Practice"),
                  _("Listening Comprehension"),
                  _("General Comprehension"),
                  _("Grammar Practice"),
                  _("Consolidation"))
        enc = self._input_encoding
        return [Section(self, _("Section %d") + ': ' + title,
                        feed.ExerciseFeeder(piece, vocabulary=self.vocab,
                                            input_encoding=enc).feed(self))
                for title, piece in zip(titles, pieces)]
    
    def _create_content(self):
        self.vocab = self._create_vocab()
        sections = (Section(self, _("Aims and Objectives"),
                            self._parse_wiki_file('aims')),
                    VocabSection(self, _("Vocabulary"), self.vocab),
                    Section(self, _("Grammar"), anchor='grammar', toc_depth=9,
                            content=self._parse_wiki_file('grammar')),
                    Section(self, _("Exercises"), anchor='exercises',
                            content=self._create_exercises(), toc_depth=1),
                    Section(self, _("Checklist"),
                            self._parse_wiki_file('checklist')))
        return SectionContainer(self, sections)


    
class Instructions(EurochanceNode):
    """A general set of pre-course instructions."""
    _TITLE = _("General Course Instructions")

    def _create_content(self):
        return self._parse_wiki_file('instructions')
    
    
class ExerciseInstructions(EurochanceNode):
    """Exercise instructions."""
    
    def __init__(self, parent, type, *args, **kwargs):
        assert issubclass(type, Exercise)
        self._type = type
        super(ExerciseInstructions, self).__init__(parent, *args, **kwargs)
        
    def _create_content(self):
        try:
            pre = self._parse_wiki_file(self._id())
        except IOError, e:
            pre = None
        return self._type.help(self, pre)

    def title(self, abbrev=False):
        return _("Instructions for %s") % self._type.name()

    def _id(self):
        return camel_case_to_lower(self._type.__name__)

    
class _Index(EurochanceNode):

    def __init__(self, parent, units, *args, **kwargs):
        self._units = units
        super(_Index, self).__init__(parent, *args, **kwargs)

    
class CourseIndex(_Index):
    _TITLE = _("Detailed Course Index")

    def _create_content(self):
        return TableOfContents(self, item=self.parent(), depth=99)

    
class GrammarIndex(_Index):
    _TITLE = _("Grammar Index")

    def _create_content(self):
        all = reduce(lambda a,b: a+b, [u.find_section('grammar').sections()
                                       for u in self._units])
        return TableOfContents(self, all, depth=99)

    
class VocabIndex(_Index):
    _TITLE = _("Vocabulary Index")

    def _create_content(self):
        vocab = reduce(lambda a,b: a+b, [u.vocab for u in self._units])
        rev = vocab[:]
        vocab.sort(lambda a,b: cmp(a.word().lower(), b.word().lower()))
        rev.sort(lambda a,b:
                 cmp(a.translation().lower(), b.translation().lower()))
        s = (VocabSection(self, _("Ordered by the English term"), vocab),
             VocabSection(self, _("Ordered by the translation"), rev,
                          reverse=True))
        return SectionContainer(self, s)

    
class AnswerSheets(_Index):
    _TITLE = _("Answer Sheets")

    def _create_content(self):
        return TableOfContents(self, title=_("Table of Contents:"))
    
    def _create_children(self):
        return [self._create_child(AnswerSheet, u) for u in self._units]

    
class AnswerSheet(EurochanceNode):
    _PARENT_ID_PREFIX = False
    
    def __init__(self, parent, unit, *args, **kwargs):
        self._unit = unit
        super(AnswerSheet, self).__init__(parent, *args, **kwargs)
        
    def _title(self):
        return _("Answer Sheet for %s") % self._unit.title(abbrev=True)

    def _create_content(self):
        x = [Section(self, sec.title(),
                     [Section(self, e.title(), e.answer_sheet(self))
                      for e in sec.sections() if isinstance(e, Exercise) \
                      and hasattr(e, 'answer_sheet')])
             for sec in self._unit.find_section('exercises').sections()]
        return SectionContainer(self, x)

    
class Help(EurochanceNode):
    _TITLE = _("Help Index")

    def _create_content(self):
        return TableOfContents(self, title=_("Table of Contents:"))

    def _create_children(self):
        return [self._create_child(ExerciseInstructions, t, 'help')
                for t in Exercise.used_types()]

    
class EurochanceCourse(EurochanceNode):
    """The course is a root node which comprises a set of 'Unit' instances."""

    def __init__(self, dir, course_language, users_language, **kwargs):
        assert isinstance(users_language, types.StringType) and \
               len(users_language) == 2
        self._users_language = users_language
        super(EurochanceCourse, self).__init__(None, dir,
                                               language=course_language,
                                               **kwargs)

    def users_language(self):
        return self._users_language
    
    def _title(self):
        return self._read_file('title')

    def _create_content(self):
        return self._parse_wiki_file('intro') + \
               [TableOfContents(self, item=self, title=_("Table of Contents:"))]
                         
    
    def _create_children(self):
        units = [self._create_child(Unit, subdir=d)
                 for d in list_subdirs(self.src_dir())
                 if d[0] in map(str, range(0, 9))]
        return [self._create_child(Instructions)] + units + \
               [self._create_child(CourseIndex, units),
                self._create_child(GrammarIndex, units),
                self._create_child(VocabIndex, units),
                self._create_child(AnswerSheets, units),
                self._create_child(Help)]
    
    def meta(self):
        return {'author': 'Eurochance Team',
                'copyright': "Copyright (c) 2004 Eurochance Team"}


class Formatter(wiki.Formatter):

    _MARKUP = [(type, markup) for type, markup in wiki.Formatter._MARKUP
               if type not in ('italic', 'fixed')]
    
    def _citation_formatter(self, groups, close=False):
        if not close:
            return '<span class="citation" lang="%s">' % self._parent.language()
        else:
            return '</span>'
    
wiki.Formatter = Formatter
