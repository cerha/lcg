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

"""A Concrete implementation of Eurochance course structure.

This module defines classes which create the actual course from the source
data.  It can be used as an example of LCG usage.

"""

from lcg import *

class EurochanceNode(ContentNode):

    def __init__(self, *args, **kwargs):
        super(EurochanceNode, self).__init__(*args, **kwargs)
        self.resource(Stylesheet, 'default.css')
    
    def resource(self, cls, file, *args, **kwargs):
        if cls is Media:
            basename, ext = os.path.splitext(file)
            file = basename + '.mp3'
        return super(EurochanceNode, self).resource(cls, file, *args, **kwargs)

    def _user_lang(self):
        if isinstance(self.root(), IntermediateCourse):
            return self.root().users_language()
        else:
            return None

    def _localized_wiki_content(self, filename):
        ulang = self._user_lang()
        content = self.parse_wiki_file(filename, lang=ulang)
        return SectionContainer(self, content, lang=ulang)
        
    
class Unit(EurochanceNode):
    _EXERCISE_SECTION_SPLITTER = re.compile(r"^==(?P<title>.+)?==+\s*$", re.M)

    def _abbrev_title(self, abbrev=False):
        return _("Unit %d") % self._parent.index(self)

    def _title(self, abbrev=False):
        return self._read_file('title')
    
    def _exercise_sections(self, split_result):
        title = ''
        pieces = []
        for x in split_result:
            if isinstance(x, SplittableText):
                if x.text().strip():
                    pieces.append((title, x))
            else:
                title = x[0]
        return pieces
    
    def _create_exercises(self):
        filename = self._input_file('exercises')
        text = self._read_file('exercises', comment='^#')
        splittable = SplittableText(text, input_file=filename)
        pieces = splittable.split(self._EXERCISE_SECTION_SPLITTER)
        return [Section(self, _("Section %d") +': '+ title,
                        feed.ExerciseFeeder(piece).feed(self))
                for title, piece in self._exercise_sections(pieces)]

    def _create_content(self):
        return SectionContainer(self, self._create_exercises())

    
class IntermediateUnit(Unit):
    """Unit is a collection of sections (Vocabulary, Grammar, Exercises...)."""

    def _id(self):
        return 'unit'
    
    def _read_splittable_text(self, name, lang=None):
        filename = self._input_file(name, lang=lang)
        text = self._read_file(name, lang=lang)
        return SplittableText(text, input_file=filename)

    def _create_vocab(self):
        ulang = self._user_lang()
        text = self._read_splittable_text('vocabulary', lang=ulang)
        return feed.VocabFeeder(text, ulang).feed(self)

    def _exercise_sections(self, pieces):
        pieces = [p for p in pieces if isinstance(p, SplittableText)]
        assert len(pieces) == 5, \
               "5 sections expected! (%d found)" % len(pieces)
        titles = (_("Vocabulary Practice"),
                  _("Listening Comprehension"),
                  _("General Comprehension"),
                  _("Grammar Practice"),
                  _("Consolidation"))
        return zip(titles, pieces)
    
    def _create_content(self):
        self.vocab = self._create_vocab()
        sections = (Section(self, _("Aims and Objectives"),
                            self.parse_wiki_file('aims')),
                    VocabSection(self, _("Vocabulary"), self.vocab),
                    Section(self, _("Exercises"), anchor='exercises',
                            content=self._create_exercises()),
                    Section(self, _("Checklist"),
                            self.parse_wiki_file('checklist')))
        return SectionContainer(self, sections)

    
class Instructions(EurochanceNode):
    """A general set of pre-course instructions."""
    _TITLE = _("General Course Instructions")

    def _create_content(self):
        return self._localized_wiki_content('instructions')
    
    
class ExerciseInstructions(EurochanceNode):
    """Exercise instructions."""
    
    def __init__(self, parent, type, template, *args, **kwargs):
        assert issubclass(type, Exercise)
        self._type = type
        self._template = template
        type.set_help_node(self)
        super(ExerciseInstructions, self).__init__(parent, *args, **kwargs)
        
    def _create_content(self):
        mp = wiki.MacroParser(substitution_provider=_)
        mp.add_globals(type=self._type, **self._type.typedict())
        content = self.parse_wiki_text(mp.parse(self._template))
        return SectionContainer(self, content, lang=self._user_lang())

    def title(self, abbrev=False):
        return _("Instructions for %s") % self._type.name()

    def _id(self):
        return camel_case_to_lower(self._type.__name__)


class GrammarBank(EurochanceNode):
    _TITLE = _("Grammar Bank")

    def _create_content(self):
        return self._localized_wiki_content('grammar')


class _Index(EurochanceNode):

    def __init__(self, parent, units, *args, **kwargs):
        self._units = units
        super(_Index, self).__init__(parent, *args, **kwargs)

        
class CourseIndex(_Index):
    _TITLE = _("Detailed Course Index")

    def _create_content(self):
        return TableOfContents(self, item=self.parent(), depth=99)

    
class VocabIndex(_Index):
    _TITLE = _("Vocabulary Index")

    def _create_content(self):
        vocab = reduce(lambda a,b: a+b, [u.vocab for u in self._units])
        rev = vocab[:]
        vocab.sort(lambda a,b: cmp(a.word().lower(), b.word().lower()))
        rev.sort(lambda a,b:
                 cmp(a.translation().lower(), b.translation().lower()))
        s = (VocabIndexSection(self, _("Ordered by the English term"), vocab),
             VocabIndexSection(self, _("Ordered by the translation"), rev,
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

    def _answer_sheets(self, section):
        return [Section(self, e.title(), e.answer_sheet(self))
                for e in section.sections()
                if isinstance(e, Exercise) and hasattr(e, 'answer_sheet')]

    def _create_content(self):
        parent = self._unit.find_section('exercises')
        if parent is None:
            # For the advanced course
            parent = self._unit
        sections = [Section(self, sec.title(), self._answer_sheets(sec))
                    for sec in parent.sections()]
        return SectionContainer(self, sections)

    
class Help(EurochanceNode):
    _TITLE = _("Help Index")

    def _create_content(self):
        return TableOfContents(self, title=_("Table of Contents:"))

    def _create_children(self):
        template = self._read_file('help', lang=self._user_lang(),
                                   dir=config.translation_dir)
        return [self._create_child(ExerciseInstructions, t, template)
                for t in Exercise.used_types()]

    
class EurochanceCourse(EurochanceNode):
    """The course is a root node which comprises a set of 'Unit' instances."""

    def _title(self):
        return self._read_file('title')

    def _unit_dirs(self):
        return [d for d in list_dir(self.src_dir())
                if os.path.isdir(os.path.join(self.src_dir(), d)) \
                and d[0].isdigit()]

    
    def _create_content(self):
        return (self._localized_wiki_content('intro'),
                TableOfContents(self, item=self, title=_("Table of Contents:")))
    
    def meta(self):
        return {'author': 'Eurochance Team',
                'copyright': "Copyright (c) 2004-2005 Eurochance Team"}

    
class AdvancedCourse(EurochanceCourse):

    def __init__(self, *args, **kwargs):
        super(EurochanceCourse, self).__init__(None, *args, **kwargs)
        
    def _create_children(self):
        units = [self._create_child(Unit, subdir=d) for d in self._unit_dirs()]
        return [self._create_child(Instructions)] + units + \
               [self._create_child(AnswerSheets, units),
                self._create_child(Help)]

    
class IntermediateCourse(EurochanceCourse):
    
    def __init__(self, dir, course_language, users_language, **kwargs):
        assert isinstance(users_language, types.StringType) and \
               len(users_language) == 2
        self._users_language = users_language
        super(EurochanceCourse, self).__init__(None, dir,
                                               language=course_language,
                                               **kwargs)

    def users_language(self):
        return self._users_language

    def _create_children(self):
        units = [self._create_child(IntermediateUnit, subdir=d)
                 for d in self._unit_dirs()]
        return [self._create_child(Instructions)] + units + \
               [self._create_child(GrammarBank),
                self._create_child(VocabIndex, units),
                self._create_child(AnswerSheets, units),
                self._create_child(Help)]
    
    
class EurochanceExporter(StaticExporter):
    _INDEX_LABEL = _('Course Index')
    
class Formatter(wiki.Formatter):
    def _citation_formatter(self, groups, close=False):
        if not close:
            return '<span class="citation" lang="%s">' % self._parent.language()
        else:
            return '</span>'
wiki.Formatter = Formatter

class _Section(wiki.Parser._Section):
    def __init__(self, title, *args, **kwargs):
        title = title.replace('>>', '<span class="citation" lang="%s">' % 'de')
        title = title.replace('<<', '</span>')
        super(wiki.Parser._Section, self).__init__(title, *args, **kwargs)
# Just a quick hack...
wiki.Parser._Section = _Section

