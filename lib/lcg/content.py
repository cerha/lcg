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

"""Course content abstraction.

This module provides classes for representation of content elements in an
abstract container capable of HTML export.

"""

import string
import re
import types
import unicodedata

from lcg import *
from _html import *


class Content(object):
    """Generic base class for all types of content.

    One instance always makes a part of one document -- it cannot be split over
    multiple output documents.  On the other hand, one document usually
    consists of multiple 'Content' instances (elements).

    Each content element may be contained in another content element (see the
    'Container' class) and thus they make a hierarchical structure.  All the
    elements within this structure have the same parent 'ContentNode' instance
    and through it are able to gather some context information and access other
    objects (i.e. the resources).

    """
    def __init__(self, parent):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.

        """
        assert isinstance(parent, ContentNode), \
               "Not a 'ContentNode' instance: %s" % parent
        self._parent = parent
        self._container = None

    def sections(self):
        """Return the contained sections as a sequence of 'Section' instances.

        This method allows creation of tables of contents and introcpection of
        content hierarchy.
        
        An empty list is returned in the base class.  The derived
        classes, however, can override this method to return the list of
        contained subsections.

        """
        return ()
        
    def parent(self):
        """Return the parent 'ContentNone' of this content element."""
        return self._parent

    def set_container(self, container):
        assert isinstance(container, Container), \
               "Not a 'Container' instance: %s" % container
        self._container = container

    def _container_path(self):
        path = [self]
        while path[0]._container is not None:
            path.insert(0, path[0]._container)
        return tuple(path)
    
    def export(self):
        """Return the HTML formatted content as a string."""
        return ''


class TextContent(Content):
    """A simple piece of text."""

    def __init__(self, parent, text):
        """Initialize the instance.

        Arguments:

          parent -- same as in the parent class.
          text -- the actual text content of this element as a string.

        """
        assert isinstance(text, types.StringTypes)
        super(TextContent, self).__init__(parent)
        self._text = text

    def export(self):
        return self._text

        
class WikiText(TextContent):
    """Structured text in Wiki formatting language (on input)."""
        
    def export(self):
        return wiki.InlineFormatter(self._parent).format(self._text)

    
class Container(Content):
    """Container of multiple parts, each of which is a 'Content' instance.

    Containers allow to build a hierarchy of 'Content' instances inside the
    scope of one node.  This is an addition to the hierarchy of the actual
    nodes (separate pages).

    All the contained (wrapped) content elements will be notified about the
    fact, that they are contained within this container and thus belong to the
    hierarchy.

    """

    def __init__(self, parent, content):
        """Initialize the instance.

        Arguments:
        
          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          content -- the actual content wrapped into this container as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.

        """
        super(Container, self).__init__(parent)
        if operator.isSequenceType(content):
            assert is_sequence_of(content, Content), \
                   "Not a 'Content' instances sequence: %s" % (content,)
            self._content = tuple(content)
        else:
            assert isinstance(content, Content)
            self._content = (content,)
        for c in self._content:
            c.set_container(self)

    def export(self):
        return "".join([p.export() for p in self._content])


class Paragraph(Container):
    """A paragraph of text, where the text can be any 'Content'."""

    def export(self):
        return "<p>\n"+ super(Paragraph, self).export() +"</p>\n\n"


class ListItem(Container):
    """One item of an itemized list (can contain any subcontent)."""

    def export(self):
        return "<li>"+ super(ListItem, self).export() +"</li>\n"

    
class ItemizedList(Container):
    """An itemized list (sequence of `ListItem' instances)."""

    TYPE_UNORDERED = 'UNORDERED'
    TYPE_ALPHA = 'ALPHA'
    TYPE_NUMERIC = 'NUMERIC'
    
    def __init__(self, parent, content, type=TYPE_UNORDERED):
        assert is_sequence_of(content, ListItem)
        assert type in (self.TYPE_UNORDERED,
                        self.TYPE_ALPHA,
                        self.TYPE_NUMERIC)
        self._type = type
        super(ItemizedList, self).__init__(parent, content)
        

    def export(self):
        mapping = {self.TYPE_UNORDERED: ('ul', ''),
                   self.TYPE_NUMERIC: ('ol', ''),
                   self.TYPE_ALPHA: ('ol',
                                     ' style="list-style-type: lower-alpha"')}
        tag, attr = mapping[self._type]
        return "<%s%s>%s</%s>\n" % \
               (tag, attr, super(ItemizedList, self).export(), tag)

class TableCell(Container):
    """One cell in a table."""

    def export(self):
        return "<td>%s</td>" % super(TableCell, self).export()
    
class TableRow(Container):
    """One row in a table."""

    def __init__(self, parent, content):
        assert is_sequence_of(content, TableCell)
        super(TableRow, self).__init__(parent, content)
        
    def export(self):
        return "<tr>%s</tr>\n" % super(TableRow, self).export()
    
class Table(Container):
    """One row in a table."""

    def __init__(self, parent, content):
        assert is_sequence_of(content, TableRow)
        super(Table, self).__init__(parent, content)
        
    def export(self):
        return '<table class="">%s</table>\n' % super(Table, self).export()
    
    
class SectionContainer(Container):
    """A 'Container' which recognizes contained sections.

    'SectionContainer' acts as a 'Container', but for any contained 'Section'
    instances, a local 'TableOfContents' can be created automatically,
    preceeding the actual content (depending on the 'toc_depth' constructor
    argument).  The contained sections are also returned by the 'sections()'
    method to allow builbing a global `TableOfContents'.

    """

    def __init__(self, parent, content, toc_depth=99):
        """Initialize the instance.

        Arguments:

          parent, content -- same as in the parent class.
          toc_depth -- the depth of local table of contents.  Corresponds to
            the same constructor argument of 'TableOfContents'.

        """
        super(SectionContainer, self).__init__(parent, content)
        self._sections = [s for s in self._content if isinstance(s, Section)]
        toc_sections = [s for s in self._sections if s.in_toc()]
        if len(toc_sections) > 0 and toc_depth > 0:
            self._toc = TableOfContents(parent, self, title=_("Index:"),
                                        depth=toc_depth)
        else:
            self._toc = Content(parent)

    def sections(self):
        return self._sections
    
    def export(self):
        return "\n".join([p.export() for p in (self._toc,) + self._content])

    
class Section(SectionContainer):
    """Section wraps the subordinary contents into an inline section.

    Section is very simillar to a 'SectionContainer', but there are a few
    differences:

      * Every section has a title, which appears in the output document as a
        heading.

      * Section can be referenced using an HTML anchor.

      * Sections are numbered.  Each section knows it's number within it's
        container.
    
    """
    def __init__(self, parent, title, content, anchor=None, toc_depth=0,
                 in_toc=True):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          title -- section title as a string.
          content -- the actual content wrapped into this section as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
          anchor -- section anchor name as a string.  If None (default) the
            anchor name will be generated automatically.  If you want to refer
            to a section explicitly from somewhere, you will probably not rely
            on the default anchor name, so that's how you can define your own.
            This also allows you to find a section by it's anchor name in the
            hierarchy (see 'ContentNode.find_section()').
          toc_depth -- The depth of the local Table of Contents (see
            'SectionContainer').
          in_toc -- a boolean flag indicating whether this section is supposed
            to be included in the Table of Contets.
            
        """
        assert isinstance(title, types.StringTypes)
        assert isinstance(anchor, types.StringTypes) or anchor is None
        assert isinstance(in_toc, types.BooleanType)
        self._title = title
        self._in_toc = in_toc
        self._anchor = anchor
        super(Section, self).__init__(parent, content, toc_depth=toc_depth)
        

    def _section_path(self):
        return [c for c in self._container_path() if isinstance(c, Section)]
        
    def section_number(self):
        """Return the number of this section within it's container as int."""
        return self._container.sections().index(self) + 1
    
    def title(self):
        """Return the section title as a string."""
        title = self._title
        if self._container is not None and title.find("%d") != -1:
            title = title % self.section_number()
        return title

    def in_toc(self):
        """Return True if the section is supposed to appear in TOC."""
        return self._in_toc
    
    def anchor(self):
        """Return the anchor name for this section."""
        if self._anchor is not None:
            return self._anchor
        else:
            numbers = [str(x.section_number()) for x in self._section_path()]
            return 'sec-' + '-'.join(numbers)

    def url(self):
        """Return the URL of the section relative to the course root."""
        return self._parent.url() + "#" + self.anchor()
    
    def _header(self):
        l = len(self._section_path()) + 1
        return '<a name="%s"></a>\n' % self.anchor() + h(self.title(), l)
               
    def export(self):
        return "\n".join((self._header(), super(Section, self).export()))

    
class TableOfContents(Content):
    """A contained Table of Contents."""
    
    def __init__(self, parent, item=None, title=None, depth=1, detailed=True):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          item -- the place where to start in the content hierarchy tree.
            'ContentNode' or 'Content' instances are allowed.  None means that
            'parent' should be used.  See 'Section' documentation for more
            information how the content tree is built.
          title -- the title of the TOC as a string.
          depth -- how deep in the hierarchy should we go.
          detailed -- A True (default) value means that the 'Content' hierarchy
            within the leave nodes of the node tree will be included in the
            TOC.  False means to consider only 'ContentNode' hierarchy.

        """
        super(TableOfContents, self).__init__(parent)
        if item is None:
            item = parent
        assert isinstance(item, (ContentNode, Content)) or \
               is_sequence_of(item, Content)
        assert title is None or isinstance(title, types.StringTypes)
        assert isinstance(depth, types.IntType)
        assert isinstance(detailed, types.BooleanType)
        self._item = item
        self._title = title
        self._depth = depth
        self._detailed = detailed
        
    def export(self):
        toc = self._make_toc(self._item, depth=self._depth)
        if self._title is not None:
            return div((b(self._title), toc), cls="table-of-contents")
        else:
            return toc
        
    def _make_toc(self, item, indent=0, depth=1):
        if depth <= 0:
            return ''
        items = ()
        if isinstance(item, ContentNode):
            items = item.children()
        if len(items) == 0 and self._detailed:
            if isinstance(item, (types.ListType, types.TupleType)):
                items = item
            else:
                items = [s for s in item.sections() if s.in_toc()]
        if len(items) == 0:
            return ''
        links = [link(i.title(), i.url()) + \
                 self._make_toc(i, indent=indent+4, depth=depth-1)
                 for i in items]
        return "\n" + ul(links, indent=indent) + "\n" + ' '*(indent-2)

    
class VocabList(Content):
    """Vocabulary listing consisting of multiple 'VocabItem' instances."""

    
    def __init__(self, parent, items, reverse=False):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          items -- sequence of 'VocabItem' instances.
          reverse -- a boolean flag indicating, that the word pairs should be
            printed in reversed order - translation first.

        """
        super(VocabList, self).__init__(parent)
        assert is_sequence_of(items, VocabItem)
        assert isinstance(reverse, types.BooleanType)
        self._items = items
        self._reverse = reverse
        parent.resource(Script, 'audio.js')

    def export(self):
        pairs = [(speaking_text(i.word(), i.media())+" "+i.note(),
                  i.translation()) for i in self._items]
        rows = ['<tr><td>%s</td><td>%s</td></tr>' % \
                (self._reverse and (b,a) or (a,b)) for a,b in pairs]
        return '<table>\n' + '\n'.join(rows) + "\n</table>\n"

    
class VocabItem(Record):
    """One item of vocabulary listing."""
    _DIACRITICS_MATCHER = re.compile(r" WITH .*")
    _DANGER_CHAR_MATCHER = re.compile(r"[^a-zA-Z0-9-]")
    
    def __init__(self, parent, word, note, translation):
        """Initialize the instance.
        
        Arguments:
          word -- The actual piece of vocabulary as a string
          note -- Notes in parens as a string.  Can contain multiple notes
            in parens separated by spaces.  Typical notes are for example
            (v) for verb etc.
          translation -- the translation of the word into target language.
        
        """
        def safe_char(match):
            char = match.group(0)
            if char in ('.', ',', '?', '!', ':', ';', '(', ')'):
                return ''
            base_name = self._DIACRITICS_MATCHER.sub('', unicodedata.name(char))
            base_char = unicodedata.lookup(base_name)
            if self._DANGER_CHAR_MATCHER.match(base_char):
                return '-'
            return base_char
        assert isinstance(word, types.UnicodeType)
        assert isinstance(note, types.UnicodeType)
        assert isinstance(translation, types.UnicodeType)
        self._word = word
        self._note = note
        self._translation = translation
        name = self._DANGER_CHAR_MATCHER.sub(safe_char, word.replace(' ', '-'))
        filename = os.path.join('vocabulary', name + '.ogg')
        self._media = parent.resource(Media, filename, tts_input=word)


    def word(self):
        return self._word
    
    def translation(self):
        return self._translation
    
################################################################################
################################     Tasks     #################################
################################################################################

class Task(object):
    """This class an abstract base class for various concrete tasks.

    A set of concrete tasks is a part of each 'Exercise'.

    """
    pass


class Choice(Record):
    """Answer text with an information whether it is correct or not.

    One of the choices for 'MultipleChoiceQuestion'.

    """
    
    def __init__(self, answer, correct=False):
        assert isinstance(answer, types.UnicodeType)
        assert isinstance(correct, types.BooleanType)
        self._answer = answer
        self._correct = correct

        
class _ChoiceTask(Task):
    """Select the correct statement out of a list of predefined choices."""
    
    def __init__(self, prompt, choices):
        """Initialize the instance.

        Arguments:
        
          choices -- sequence of 'Choice' instances related to this Task.
          
        """
        super(_ChoiceTask, self).__init__()
        assert isinstance(prompt, types.StringTypes)
        assert is_sequence_of(choices, Choice)
        assert len([ch for ch in choices if ch.correct()]) == 1
        self._prompt = prompt
        self._choices = list(choices)

    def prompt(self):
        return self._prompt
    
    def choices(self):
        return self._choices

    def correct_choice(self):
        for choice in self._choices:
            if choice.correct():
                return choice
        raise Exception("No correct choice found!")

    def choice_index(self, choice):
        return self._choices.index(choice)
        
        
class MultipleChoiceQuestion(_ChoiceTask):
    pass


class Selection(_ChoiceTask):
    
    def __init__(self, choices):
        super(Selection, self).__init__('', choices)

        
class GapFillStatement(_ChoiceTask):

    _REGEXP = re.compile(r"(___+)")
    
    def __init__(self, prompt, choices):
        super(GapFillStatement, self).__init__(prompt, choices)
        matches = len(self._REGEXP.findall(prompt))
        assert matches == 1, \
               "GapFillStatement must include just one gap " + \
               "marked by three or more underscores. %d found." % matches

    def substitute_gap(self, replacement):
        return self._REGEXP.sub(replacement, self.prompt())
    

class TrueFalseStatement(_ChoiceTask):
    """The goal is to indicate whether the statement is true or false."""
    
    def __init__(self, statement, correct=True):
        """Initialize the instance.

        Arguments:
        
          statement --  exercise within the containing section.
          correct -- boolean flag indicating whether the statement is correct
            or not (true when it is correct).
          
        """
        assert isinstance(correct, types.BooleanType)
        choices = (Choice(_('TRUE'), correct), Choice(_('FALSE'), not correct))
        super(TrueFalseStatement, self).__init__(statement, choices)


class ClozeTask(Task):

    _REGEXP = re.compile(r"\[([^\]]+)\]")
    
    def __init__(self, text):
        super(ClozeTask, self).__init__()
        assert isinstance(text, types.UnicodeType)
        self._text = text

    def answers(self):
        return self._REGEXP.findall(self._text)

    def text(self, field_formatter):
        return self._REGEXP.sub(field_formatter, self._text)

    def plain_text(self):
        return self._REGEXP.sub(lambda match: match.group(1), self._text)

    
class TransformationTask(ClozeTask):

    def __init__(self, orig, transformed):
        super(TransformationTask, self).__init__(transformed)
        assert isinstance(orig, types.UnicodeType)
        self._orig = orig

    def orig(self):
        return self._orig

    
################################################################################
################################   Exercises   #################################
################################################################################

    
class Exercise(Section):
    """Exercise consists of an assignment and a set of tasks."""

    _TASK_TYPE = Task
    _NAME = None
    _RECORDING_REQUIRED = False
    _AUDIO_VERSION_REQUIRED = False

    _used_types = []
    
    def __init__(self, parent, tasks, sound_file=None, audio_version=None,
                 transcript=None):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.

          tasks -- sequence of 'Task' instances related to this exercise.

          sound_file -- name of the file with a recording as a string.  Some
            exercise types may require a recording, some may not.
            
          audio_version -- name of the file with an audio version of this
            exercise
          
          transcript -- name of the file with a textual transcript of the
            recording (string).  The transcript file is required to exist
            whenever the 'sound_file' argument is supplied.  This argument
            doesn't have to be supplied, however, when a default value made out
            of the 'sound_file' filename using the '.txt' extension instead of
            the original sound file extension is ok.
            
        """
        title = "%s %%d: %s" % (_("Exercise"), self._NAME)
        super(Exercise, self).__init__(parent, title, Content(parent),
                                       in_toc=False)
        self.__class__._USED = True
        if self.__class__ not in Exercise._used_types:
            Exercise._used_types.append(self.__class__)
        assert is_sequence_of(tasks, self._TASK_TYPE), \
               "Tasks must be a sequence of '%s' instances!: %s" % \
               (self._TASK_TYPE.__name__, tasks)
        assert sound_file is None or isinstance(sound_file, types.StringTypes)
        if self._RECORDING_REQUIRED:
            assert sound_file is not None, \
            "'%s' requires a recording!" % self.__class__.__name__
        if self._AUDIO_VERSION_REQUIRED:
            assert audio_version is not None, \
            "'%s' requires an audio version!" % self.__class__.__name__
        self._tasks = list(tasks)
        if sound_file is not None:
            if transcript is None:
                transcript = os.path.splitext(sound_file)[0] + '.txt'
            assert isinstance(transcript, types.StringTypes)
            self._recording = parent.resource(Media, sound_file)
            self._transcript = self._create_transcript(transcript)
        else:
            self._recording = None
            self._transcript = None
        if audio_version is not None:
            self._audio_version = parent.resource(Media, audio_version)
        else:
            self._audio_version = None
        parent.resource(Script, 'audio.js')

    # Class methods
        
    def task_type(cls):
        return cls._TASK_TYPE
    task_type = classmethod(task_type)
    
    def name(cls):
        return cls._NAME
    name = classmethod(name)

    def id(cls):
        return camel_case_to_lower(cls.__name__)
    id = classmethod(id)
    
    def used_types(cls):
        return cls._used_types
    used_types = classmethod(used_types)

    # Instance methods

    def _create_transcript(self, file):
        return self._parent.resource(Transcript, file)

    def _form_name(self):
        return "exercise_%s" % id(self)
    
    def _instructions(self):
        return ""

    def _sound_controls(self, label, media, transcript=None):
        if transcript is not None:
            t = " " + link(_("show transcript"), transcript.url(),
                           target="transcript", brackets=True)
        else:
            t = ""
        f = ('<form class="sound-control" action="">%s:' % label,
             button(_("Play"), "play_audio('%s')" % media.url()),
             button(_("Stop"), 'stop_audio()'), t, '</form>')
        a = '%s: %s' % (label, link(_("Play"), media.url(), brackets=True))
        return script_write('\n'.join(f), p(a+t))

    def export(self):
        return "\n\n".join((self._header(),
                            self._export_instructions(),
                            '<form name="%s" action="">' % self._form_name(),
                            "\n".join(map(self._export_task, self._tasks)),
                            self._results(),
                            '</form>',
                            script(self._init_script())))
    
        
    
    def _export_task(self, task):
        raise Exception("This Method must be overriden")

    def _export_instructions(self):
        """Return the HTML formatted instructions for this type of exercise."""
        instructions = p(self._instructions(),
                         link(_("detailed instructions"),
                              "instructions-%s.html" % self.id(),
                              target='help', brackets=True))
        if self._recording is not None:
            instructions += '\n\n' + self._export_recording()
        if self._audio_version is not None:
            instructions += '\n\n' + self._export_audio_version()
        return instructions

    def _export_recording(self):
        return self._sound_controls(_("Recording"), self._recording,
                                    self._transcript)
    
    def _export_audio_version(self):
        label = _("This exercise can be also done purely aurally/orally")
        return self._sound_controls(label, self._audio_version)

    def _init_script(self):
        return ''
        
    def _results(self):
        return ''

    
class SentenceCompletion(Exercise):
    """Filling in gaps in sentences by typing in the correct completion."""

    _NAME = _("Sentence Completion")
    _AUDIO_VERSION_REQUIRED = True
    _TASK_TYPE = None

    def _instructions(self):
        return _("""This exercise can be only done purely aurally/orally.  You
        will hear some of the sentences from the previous exercise unfinished
        and your goal is to say the missing part.""")

    def _export_audio_version(self):
        return self._sound_controls(_("The exercise"), self._audio_version)


class _InteractiveExercise(Exercise):
    """A common super class for exercises which can be interactively evaluated.

    These exercises allow the user to indicate his answers and the computer
    gives him a feedback.
    
    """
    _RESPONSES = {'correct': ['correct-response-1.ogg',
                              'correct-response-2.ogg',
                              'correct-response-3.ogg'],
                  'incorrect': ['incorrect-response-1.ogg',
                                'incorrect-response-2.ogg',
                                'incorrect-response-3.ogg']}
    _RESPONSE_TTS = {'correct-response-1.ogg': _("Correct!"),
                     'correct-response-2.ogg': _("Perfect!"),
                     'correct-response-3.ogg': _("Well done!"),
                     'incorrect-response-1.ogg': _("You are wrong!"),
                     'incorrect-response-2.ogg': _("Oh no, I'm sorry."),
                     'incorrect-response-3.ogg': _("Try again!")}

    _FORM_HANDLER = 'Handler'
    
    def __init__(self, parent, *args, **kwargs):
        super(_InteractiveExercise, self).__init__(parent, *args, **kwargs)
        parent.resource(Script, 'exercises.js')
        parent.resource(Script, 'audio.js')
        a = [(key, [parent.resource(Media, f, shared=True,
                                    tts_input=self._RESPONSE_TTS.get(f))
                    for f in files])
             for key, files in self._RESPONSES.items()]
        self._responses = dict(a)

    def _response(self, selector):
        return self._responses[selector][0]
        
    def _answers(self):
        return ()

    def _init_script(self):
        responses = dict([(key, [media.url() for media in values])
                          for key, values in self._responses.items()])
        return "init_form(document.forms['%s'], new %s(), %s, %s)" % \
               (self._form_name(), self._FORM_HANDLER,
                js_array(self._answers()), js_dict(responses))

    def _buttons(self):
        return ()
    
    def _results(self):
        d = (_('Answered:'), field(name='answered', size=8, readonly=True), '<br/>',
             _('Correct:'),  field(name='result',   size=8, readonly=True))
        r = div((div(d, 'display'), div(self._buttons(), 'buttons')), 'results')
        return script_write(r, '')
    
    
################################################################################
################################################################################
  
class _ChoiceBasedExercise(_InteractiveExercise):
    "A superclass for all exercises based on choosing from predefined answers."

    _FORM_HANDLER = 'ChoiceBasedExerciseHandler'

    def _answers(self):
        return [t.choice_index(t.correct_choice()) for t in self._tasks]

    def _buttons(self):
        return (button(_('Fill'),  "this.form.handler.fill()"),
                reset( _('Reset'), "this.form.handler.reset()"))

    def _non_js_choice_control(self, task, choice):
        media = self._response(choice.correct() and 'correct' or 'incorrect')
        return link(choice.answer(), media.url())
    
    def _js_choice_control(self, task, choice):
        ctrl = radio('task-%d' % self._tasks.index(task),
                     "this.form.handler.eval_answer(this)",
                     value=task.choice_index(choice), cls='answer-control')
        return choice.answer() +'&nbsp;'+ ctrl

    def _format_choice(self, task, choice):
        label = chr(ord('a') + task.choice_index(choice)) + '.'
        ctrl = script_write(self._js_choice_control(task, choice),
                            self._non_js_choice_control(task, choice))
        return label + '&nbsp;' + ctrl + '<br/>'

    def _format_choices(self, task):
        formatted = [self._format_choice(task, ch) for ch in task.choices()]
        return div(formatted, 'choices')
    
    def _export_task(self, task):
        return p(task.prompt(), self._format_choices(task))

    
class MultipleChoiceQuestions(_ChoiceBasedExercise):
    """Choosing one of several answers for a given question."""
    
    _TASK_TYPE = MultipleChoiceQuestion
    _NAME = _("Multiple Choice Questions")
    
    def _instructions(self):
        return _("""For each of the %d questions below choose the correct
        answer from the list.""") % len(self._tasks)

    
class Selections(_ChoiceBasedExercise):
    """Selecting one of several statements/sentences (the correct one)."""
    
    _TASK_TYPE = Selection
    _NAME = _("Select the Correct One")
    
    def _instructions(self):
        return _("""For each of the %d pairs of statements below decide which
        one is correct.""") % len(self._tasks)

class _SelectBasedExercise(_ChoiceBasedExercise):

    _FORM_HANDLER = 'SelectBasedExerciseHandler'

    def _format_choices(self, task):
        choices = task.choices()
        js = select('task-%d' % self._tasks.index(task),
                    [(ch.answer(), task.choice_index(ch)) for ch in choices],
                    handler="this.form.handler.eval_answer(this)")
        nonjs = [self._non_js_choice_control(task, ch) for ch in task.choices()]
        return script_write(js, "("+"|".join(nonjs)+")")

    
class TrueFalseStatements(_SelectBasedExercise):
    """Deciding whether the sentence is true or false."""
    
    _TASK_TYPE = TrueFalseStatement
    _NAME = _("True/False Statements")
    
    def _instructions(self):
        return _("""For each of the %d statements below indicate whether you
        think they are true or false.""") % len(self._tasks)


class GapFilling(_SelectBasedExercise):
    """Choosing from a list of words to fill in a gap in a sentence."""

    _TASK_TYPE = GapFillStatement
    _NAME = _("Gap Filling")

    def _instructions(self):
        return _("""For each of the %d sentences below choose the correct piece
        of text from the list to fill in the gap.""") % len(self._tasks)

    def _export_task(self, task):
        return p(task.substitute_gap("%s") % self._format_choices(task))
    

################################################################################
################################################################################

class _FillInExercise(_InteractiveExercise):
    """A common base class for exercises based on writing text into fields."""

    _TASK_TYPE = ClozeTask
    
    _RESPONSES = {'all_correct': ['all-correct-response.ogg'],
                  'all_wrong': ['all-wrong-response.ogg'],
                  'some_wrong': ['some-wrong-response.ogg']}
    _RESPONSES.update(_InteractiveExercise._RESPONSES)
        
    _RESPONSE_TTS = \
         {'all-correct-response.ogg': _("Everything correct!"),
          'all-wrong-response.ogg':   _("All the answers are wrong!"),
          'some-wrong-response.ogg':  _("Some of the answers are wrong!")}
    _RESPONSE_TTS.update(_InteractiveExercise._RESPONSE_TTS)

    _FORM_HANDLER = 'FillInExerciseHandler'
    
    def _answers(self):
        return reduce(lambda a, b: a+b, [t.answers() for t in self._tasks])

    def _buttons(self):
        #_("Use the 'Evaluate' button to see the results.")
        return (button(_('Evaluate'), "this.form.handler.evaluate()"),
                button(_('Fill'),     "this.form.handler.fill()"),
                reset( _('Reset'),    "this.form.handler.reset()"))

    def _make_field(self, match):
        return field(cls='cloze', size=len(match.group(1))+1)
    
    def _export_task(self, task):
        return p(task.text(self._make_field))


class Cloze(_FillInExercise):
    """Paragraphs of text including text-fields for the marked words."""

    _NAME = _("Cloze")
    _RECORDING_REQUIRED = True

    def _create_transcript(self, file):
        text = "\n\n".join([t.plain_text() for t in self._tasks])
        return self._parent.resource(Transcript, file, text=text)
    
    def _instructions(self):
        if self._recording is not None:
            return _("""Listen to the recording carefully and then fill in the
            gaps in the text below using the same words.""")
        else:
            return _("""Fill in the gaps in the text below.  There is just one
            correct word for each gap.""")

        
class VocabExercise(_FillInExercise):
    """A small text-field for each vocabulary item on a separate row."""

    _NAME = _("Vocabulary Practice")

    def _instructions(self):
        return _("""You will hear a word or expression in your language.  Say
        it in English and listen to the model pronunciation.""")
    
    def _export_task(self, task):
        return task.text(self._make_field)+'<br/>'


class Transformation(_FillInExercise):
    """A prompt (a sentence) and a big text-field for each task."""

    _TASK_TYPE = TransformationTask
    _NAME = _("Transformation")

    def _instructions(self):
        return _("""Listen to the recording and transform each of the %d
        sentences below according to the instructions.""") % len(self._tasks)

    def _export_task(self, task):
        return p(task.orig(), '<br/>', task.text(self._make_field))

    
class Substitution(Transformation):
    """A prompt (a sentence) and a big text-field for each task."""

    _NAME = _("Substitution")

    def _instructions(self):

        return _("""Substitute a part of each sentence using the text in
        brackets.""")

        
class Dictation(_FillInExercise):
    """One big text-field for a whole exercise."""

    _NAME = _("Dictation")
    _RECORDING_REQUIRED = True
    
    def _instructions(self):
        return """This exercise type is not yet implemented..."""
