# -*- coding: iso8859-2 -*-
#
# Copyright (C) 2004, 2005, 2006 Brailcom, o.p.s.
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
    
    def meta(self):
        author = 'Lawton Idiomas (http://www.lawtonschool.com)'
        copyright = "Copyright (c) 2004-2005 Lawton Idiomas (content), "
        if self.language() == 'de':
            author += ', BFI Steiermark (http://www.bfi-stmk.at)'
            copyright += ("BFI Steiermark (translation and "
                          "adaptations for German language), ")
        copyright += "Brailcom, o.p.s. (presentation)"
        return (('author', author),
                ('copyright', copyright))
    
    def resource(self, cls, file, *args, **kwargs):
        if cls is Media:
            basename, ext = os.path.splitext(file)
            file = basename + '.mp3'
        return super(EurochanceNode, self).resource(cls, file, *args, **kwargs)

    def _localized_wiki_content(self, filename, macro=False):
        ulang = self.root().users_language()
        content = self.parse_wiki_file(filename, lang=ulang, macro=macro)
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
                    title = _("Section %d") % (len(pieces)+1)  + ": " + title
                    pieces.append((title, x))
            else:
                title = x[0]
        return pieces
    
    def _create_exercises(self):
        filename = self._input_file('exercises')
        text = self._read_file('exercises', comment='^#')
        splittable = SplittableText(text, input_file=filename)
        pieces = splittable.split(self._EXERCISE_SECTION_SPLITTER)
        return [Section(self, title, feed.ExerciseFeeder(piece).feed(self))
                for title, piece in self._exercise_sections(pieces)]

    def _create_content(self):
        aims = Section(self, _("Aims and Objectives"),
                       self.parse_wiki_file('aims'))
        exercises = self._create_exercises()
        checklist = Section(self, _("Checklist"),
                            self.parse_wiki_file('checklist'))
        return SectionContainer(self, (aims,) + tuple(exercises) + (checklist,))

    
class IntermediateUnit(Unit):
    """Unit is a collection of sections (Vocabulary, Grammar, Exercises...)."""

    def _read_splittable_text(self, name, lang=None):
        filename = self._input_file(name, lang=lang)
        text = self._read_file(name, lang=lang)
        return SplittableText(text, input_file=filename)

    def _create_vocab(self):
        ulang = self.root().users_language()
        text = self._read_splittable_text('vocabulary', lang=ulang)
        return feed.VocabFeeder(text, ulang).feed(self)

    def _exercise_sections(self, pieces):
        pieces = [p for p in pieces if isinstance(p, SplittableText)]
        assert len(pieces) == 5, \
               "5 sections expected! (%d found)" % len(pieces)
        titles = [_("Section %d") +': '+ t 
                  for t in (_("Vocabulary Practice"),
                            _("Listening Comprehension"),
                            _("General Comprehension"),
                            _("Grammar Practice"),
                            _("Consolidation"))]
        return zip(titles, pieces)
    
    def _create_exercises(self):
        self.vocab = self._create_vocab()
        e = super(IntermediateUnit, self)._create_exercises()
        return (VocabSection(self, _("Vocabulary"), self.vocab),
                Section(self, _("Exercises"), anchor='exercises', content=e))

    
class Instructions(EurochanceNode):
    """A general set of pre-course instructions."""
    _TITLE = _("General Course Instructions")

    def _create_content(self):
        return self._localized_wiki_content('instructions', macro=True)
    
    
class ExerciseHelp(EurochanceNode):
    """Exercise instructions."""
    
    def __init__(self, parent, id, type, template, *args, **kwargs):
        assert issubclass(type, Exercise)
        self._type = type
        self._template = template
        type.set_help_node(self)
        super(ExerciseHelp, self).__init__(parent, id, *args, **kwargs)
        
    def _create_content(self):
        g = dict(type=self._type, **self._type.typedict())
        content = self.parse_wiki_text(self._template, macro=True, globals=g)
        return SectionContainer(self, content,
                                lang=self.root().users_language())

    def title(self, abbrev=False):
        return _("Instructions for %s") % self._type.name()


class GrammarBank(EurochanceNode):
    _TITLE = _("Grammar Bank")

    def _create_content(self):
        return self._localized_wiki_content('grammar')


class _Index(EurochanceNode):

    def __init__(self, parent, id, units, *args, **kwargs):
        self._units = units
        super(_Index, self).__init__(parent, id, *args, **kwargs)

        
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
        return [self._create_child(AnswerSheet, 'answers%02d' % (i+1), u)
                for i, u in enumerate(self._units)]

    
class AnswerSheet(EurochanceNode):
    
    def __init__(self, parent, id, unit, *args, **kwargs):
        self._unit = unit
        super(AnswerSheet, self).__init__(parent, id, *args, **kwargs)
        
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
        lng = self.root().users_language() or self.language()
        template = self._read_file('help', lang=lng, dir=config.translation_dir)
        return [self._create_child(ExerciseHelp, 'help%02d'%(i+1), t, template)
                for i, t in enumerate(Exercise.used_types())]

    
class EurochanceCourse(EurochanceNode):
    """The course is a root node which comprises a set of 'Unit' instances."""

    def __init__(self, dir, language, **kwargs):
        if '-' in language:
            language, users_language = language.split('-')
            assert len(language) == len(users_language) == 2
            self._users_language = users_language
            self._unit_cls = IntermediateUnit
        else:
            self._users_language = None
            self._unit_cls = Unit
        super(EurochanceCourse, self).__init__(None, 'index', dir,
                                               language=language, **kwargs)

    def users_language(self):
        return self._users_language
        
    def _title(self):
        return self._read_file('title')

    def _unit_dirs(self):
        dirs = [d for d in os.listdir(self.src_dir())
                if os.path.isdir(os.path.join(self.src_dir(), d)) \
                and d[0].isdigit()]
        dirs.sort()
        return dirs

    def _create_content(self):
        return (self._localized_wiki_content('intro'),
                TableOfContents(self, item=self, title=_("Table of Contents:")))
    
    def _create_children(self):
        units = [self._create_child(self._unit_cls, 'unit%02d'%(i+1), subdir=d)
                 for i, d in enumerate(self._unit_dirs())]
        children = [self._create_child(Instructions, 'instructions')] + units
        if issubclass(self._unit_cls, IntermediateUnit):
            children.extend((self._create_child(GrammarBank, 'grammar'),
                             self._create_child(VocabIndex, 'vocab', units)))
        children.extend((self._create_child(AnswerSheets, 'answers', units),
                         self._create_child(Help, 'help')))
        return children
    

    
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

