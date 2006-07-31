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

_ = TranslatableTextFactory('eurochance')

class EurochanceNode(ContentNode, FileNodeMixin):

    _INHERITED_ARGS = ('language', 'secondary_language', 'language_variants',
                       'input_encoding')
    
    def __init__(self, parent, id, subdir=None, input_encoding='ascii',
                 brief_title=None, language=None, **kwargs):
        """Initialize the instance.


        The other arguments are inherited from the parent class.
          
        """
        FileNodeMixin.__init__(self, parent, subdir,
                               input_encoding=input_encoding)
        if language is None or language == 'en':
            self._gettext = lambda x: x
        else:
            import gettext
            t = gettext.translation('lcg', config.translation_dir, (language,))
            self._gettext = lambda x: t.ugettext(re.sub('\s*\n', ' ', x))
        title = self._title_(brief_title=brief_title)
        content = self._create_content()
        super(EurochanceNode, self).__init__(parent, id, title=title,
                                             brief_title=brief_title,
                                             content=content,
                                             language=language, **kwargs)

    def _title_(self, brief_title=None):
        return self._TITLE

    def _create_content(self):
        pass

    def _localized_wiki_content(self, filename, macro=False):
        ulang = self.root().users_language()
        content = self.parse_wiki_file(filename, lang=ulang, macro=macro,
                                       subst=self._gettext)
        return SectionContainer(content, lang=ulang)
    
    def current_language_variant(self):
        return self.root().users_language()
        
    def meta(self):
        author = 'Lawton School S.L. (http://www.lawtonschool.com)'
        copyright = "Copyright (c) 2005-2006 Lawton School S.L. (content), "
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


    
class Unit(EurochanceNode):
    _EXERCISE_SECTION_SPLITTER = re.compile(r"^==(?P<title>.+)?==+\s*$", re.M)

    def _title_(self, brief_title=None):
        return concat(brief_title, ": ", self._read_file('title'))
    
    def _exercise_sections(self, split_result):
        title = ''
        pieces = []
        for x in split_result:
            if isinstance(x, SplittableText):
                if x.text().strip():
                    title = _("Section %d", len(pieces)+1) + ": " + title
                    pieces.append((title, x))
            else:
                title = x[0]
        return pieces
    
    def _create_exercises(self):
        filename = self._input_file('exercises')
        text = self._read_file('exercises', comment='^#')
        splittable = SplittableText(text, input_file=filename)
        pieces = splittable.split(self._EXERCISE_SECTION_SPLITTER)
        return [Section(title, feed.ExerciseFeeder(piece).feed(self))
                for title, piece in self._exercise_sections(pieces)]

    def _create_content(self):
        aims = Section(_("Aims and Objectives"), self.parse_wiki_file('aims'))
        exercises = self._create_exercises()
        checklist = Section(_("Checklist"), self.parse_wiki_file('checklist'))
        return SectionContainer((aims,) + tuple(exercises) + (checklist,))

    
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
        titles = [_("Section %d", i+1) +': '+ t 
                  for i, t in enumerate((_("Vocabulary Practice"),
                                         _("Listening Comprehension"),
                                         _("General Comprehension"),
                                         _("Grammar Practice"),
                                         _("Consolidation")))]
        return zip(titles, pieces)
    
    def _create_exercises(self):
        self.vocab = self._create_vocab()
        e = super(IntermediateUnit, self)._create_exercises()
        return (VocabSection(_("Vocabulary"), self.vocab),
                Section(_("Exercises"), anchor='exercises', content=e))

    
class Instructions(EurochanceNode):
    """A general set of pre-course instructions."""
    _TITLE = _("General Course Instructions")

    def _create_content(self):
        return self._localized_wiki_content('instructions', macro=True)
    
class CopyrightInfo(EurochanceNode):
    """A general set of pre-course instructions."""
    _TITLE = _("Copyright and License Information")

    def _create_content(self):
        return self.parse_wiki_file('copyright')
    
    
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
        content = self.parse_wiki_text(self._template, macro=True, globals=g,
                                       subst=self._gettext)
        return SectionContainer(content,
                                lang=self.root().users_language())

    def _title_(self, brief_title=None):
        return _("Instructions for %s", self._type.name())


class GrammarBank(EurochanceNode):
    _TITLE = _("Grammar Bank")

    def _create_content(self):
        return self._localized_wiki_content('grammar')


class _Index(EurochanceNode):

    def __init__(self, parent, id, units, *args, **kwargs):
        self._units = units
        super(_Index, self).__init__(parent, id, *args, **kwargs)

        
class VocabIndex(_Index):
    _TITLE = _("Vocabulary Index")

    def _create_content(self):
        seen = {}
        vocab = []
        for i in reduce(lambda a,b: a+b, [u.vocab for u in self._units]):
            # Ignore duplicate items.
            key = (i.word(), i.note(), i.translation())
            if not seen.has_key(key):
                seen[key] = True
                vocab.append(i)
        rev = vocab[:]
        vocab.sort(lambda a,b: cmp(a.word().lower(), b.word().lower()))
        rev.sort(lambda a,b:
                 cmp(a.translation().lower(), b.translation().lower()))
        s = (VocabIndexSection(_("Ordered by the English term"), vocab),
             VocabIndexSection(_("Ordered by the translation"), rev,
                               reverse=True))
        return SectionContainer(s)

    
class AnswerSheets(_Index):
    _TITLE = _("Answer Sheets")

    def _create_content(self):
        return TableOfNodes(title=_("Table of Contents:"))
    
    def _create_children(self):
        return [self._create_child(AnswerSheet, 'answers%02d' % (i+1), u)
                for i, u in enumerate(self._units)]

    
class AnswerSheet(EurochanceNode):
    
    def __init__(self, parent, id, unit, *args, **kwargs):
        self._unit = unit
        super(AnswerSheet, self).__init__(parent, id, *args, **kwargs)
        
    def _title_(self, brief_title=None):
        return _("Answer Sheet for %s", self._unit.title(brief=True))

    def _answer_sheets(self, section):
        return [Section(e.title(), e.answer_sheet(self))
                for e in section.sections()
                if isinstance(e, Exercise) and hasattr(e, 'answer_sheet')]

    def _create_content(self):
        parent = self._unit.find_section('exercises')
        if parent is None:
            # For the advanced course
            parent = self._unit
        sections = [Section(sec.title(), self._answer_sheets(sec))
                    for sec in parent.sections()]
        return SectionContainer(sections)

    
class Help(EurochanceNode):
    _TITLE = _("Help Index")

    def _create_content(self):
        return TableOfNodes(title=_("Table of Contents:"))

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
            variants = [os.path.splitext(os.path.splitext(f)[0])[1][1:]
                        for f in glob.glob(os.path.join(dir, 'intro.*.txt'))]
        else:
            self._users_language = None
            self._unit_cls = Unit
            variants = ()
        super(EurochanceCourse, self).__init__(None, 'index', dir,
                                               language=language,
                                               secondary_language=language,
                                               language_variants=variants,
                                               **kwargs)

    def users_language(self):
        return self._users_language

    def version(self):
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M %Z")
        return self._read_file('version') + ' (%s)' % timestamp  
        
    def _title_(self, brief_title=None):
        return self._read_file('title')

    def _unit_dirs(self):
        dirs = [d for d in os.listdir(self.src_dir())
                if os.path.isdir(os.path.join(self.src_dir(), d)) \
                and d[0].isdigit()]
        dirs.sort()
        return dirs

    def _create_content(self):
        return (self._localized_wiki_content('intro'),
                TableOfNodes(title=_("Table of Contents:")))

    def _create_children(self):
        units = [self._create_child(self._unit_cls, 'unit%02d'%(i+1), subdir=d,
                                    brief_title=_("Unit %d", i+1))
                 for i, d in enumerate(self._unit_dirs())]
        children = [self._create_child(Instructions, 'instructions')] + units
        if issubclass(self._unit_cls, IntermediateUnit):
            children.extend((self._create_child(GrammarBank, 'grammar'),
                             self._create_child(VocabIndex, 'vocab', units)))
        children.extend((self._create_child(AnswerSheets, 'answers', units),
                         self._create_child(Help, 'help'),
                         self._create_child(CopyrightInfo, 'copyright')))
        return children

    
class EurochanceExporter(HtmlStaticExporter):
    _INDEX_LABEL = _('Course Index')
    _BODY_PARTS = ('heading',
                   'language_selection',
                   'content',
                   'rule',
                   'navigation',
                   'copyright',
                   'version',
                   )
    
    def _version(self, node):
        return _("Version %s", node.root().version())

    def _copyright(self, node):
        copyright = node.root().find_node('copyright')
        if copyright is not node:
            return Link(copyright).export(self)
        else:
            return None
            
 
class _Section(Parser._Section):
    def __init__(self, title, *args, **kwargs):
        title = title.replace('>>', '<span class="citation" lang="%s">' % 'de')
        title = title.replace('<<', '</span>')
        super(Parser._Section, self).__init__(title, *args, **kwargs)
        
# Just a quick hack...
Parser._Section = _Section

