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
import wiki
import re
import types
import unicodedata

from util import *
from course import *
from _html import *


class Content(object):
    """Generic base class for all types of content.

    One instance always makes a part of one document -- it cannot be split over
    multiple output documents.  On the other hand, one document may consist of
    multiple 'Content' instances (in theory).

    Each content element may contain other content elements and thus they make
    a tree structure.  All the elements within this structure have the same
    parent 'ContentNode' instance and through it are able to gather some
    context information, such as input/output directory etc.  This is sometimes
    necessary to generete correct HTML output (e.g. URI for links etc.).

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
        self._container = container

    def _container_path(self):
        path = [self]
        while path[0]._container is not None:
            path.insert(0, path[0]._container)
        return tuple(path)
    
    def export(self):
        """Return the HTML formatted content as a string."""
        return ''

    
class Container(Content):
    """Container of multiple parts, each of which is a 'Content' instance.

    Containers allow to build a hierarchy of 'Content' instances inside the
    scope of one node.  This is an addition to the hierarchy of the actual
    nodes (separate pages).

    All the contained (wrapped) content elements will be notified about the
    fact, that they are contained within this container and thus belong to the
    hierarchy.

    'Container' exports all the parts concatenated in unchanged order.  For any
    contained 'Section' instances, a local 'TableOfContents' is created
    automatically, preceeding the actual content.

    """

    def __init__(self, parent, content, toc_depth=99):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          content -- the actual content wrapped into this container as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
          toc_depth -- the depth of local table of contents.  Corresponds to
            the same constructor argument of 'TableOfContents'.

        """
        super(Container, self).__init__(parent)
        if operator.isSequenceType(content):
            assert is_sequence_of(content, Content)
            self._content = tuple(content)
        else:
            assert isinstance(content, Content)
            self._content = (content,)
        self._sections = [p for p in self._content if isinstance(p, Section)]
        if len(self._sections) > 1 and toc_depth > 0:
            self._toc = TableOfContents(parent, self, title=_("Index:"),
                                        depth=toc_depth)
        else:
            self._toc = Content(parent)
        for c in self._content:
            c.set_container(self)

    def sections(self):
        return self._sections
    
    def export(self):
        return "\n".join([p.export() for p in (self._toc,) + self._content])

    
class Section(Container):
    """Section wraps the subordinary contents into an inline section.

    Section is very simillar to a 'Container', but there are a few differences:

      * Every section has a title, which appears in the output document as a
        heading.

      * Section can be referenced using an HTML anchor.

      * Sections are numbered.  Each section knows it's number within it's
        container.
    
    """
    def __init__(self, parent, title, content, toc_depth=0):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          title -- section title as a string.
          content -- the actual content wrapped into this section as a
            sequence of 'Content' instances in the order in which they should
            appear in the output.
            
        """
        super(Section, self).__init__(parent, content, toc_depth=toc_depth)
        assert isinstance(title, types.StringTypes)
        self._title = title

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

    def anchor(self):
        """Return the anchor name for this section."""
        return 'sec-' + '-'.join([str(c.section_number())
                                  for c in self._section_path()])

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
        assert isinstance(item, (ContentNode, Content))
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
            items = item.sections()
        if len(items) == 0:
            return ''
        links = [link(i.title(), i.url()) + \
                 self._make_toc(i, indent=indent+4, depth=depth-1)
                 for i in items]
        return "\n" + ul(links, indent=indent) + "\n" + ' '*(indent-2)

    
class GenericText(Content):
    """Generic parent class for content generated from a piece of text."""

    def __init__(self, parent, text):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          text -- the actual text content of this element as a string.

        """
        super(GenericText, self).__init__(parent)
        self._text = text

    def export(self):
        return self._text

        
class WikiText(GenericText):
    """Structured text in Wiki formatting language (on input)."""
    
    def export(self):
        return wiki.format(self._text)
    
    
class VocabList(Content):
    """Vocabulary listing consisting of multiple 'VocabItem' instances."""

    
    def __init__(self, parent, items):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          items -- Sequence of 'VocabItem' instances.

        """
        super(VocabList, self).__init__(parent)
        assert is_sequence_of(items, VocabItem)
        self._items = items
        parent.resource(Script, 'audio.js')

    def export(self):
        rows = ['<tr><td>%s %s</td><td>%s</td></tr>' % \
                (speaking_text(i.word(), i.media()), i.note(), i.translation())
                for i in self._items]
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
        self._prompt = prompt
        self._choices = list(choices)

    def prompt(self):
        return self._prompt
    
    def choices(self):
        return self._choices

    def choice_index(self, choice):
        return self._choices.index(choice)
        
        
class MultipleChoiceQuestion(_ChoiceTask):
    pass


class Selection(_ChoiceTask):
    
    def __init__(self, choices):
        super(Selection, self).__init__('', choices)

        
class GapFillStatement(_ChoiceTask):
    pass


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
    _AUDIO_VERSION_LABEL = \
                       _("This exercise can be also done purely aurally/orally")
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
        super(Exercise, self).__init__(parent, title, Content(parent))
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
        parent.resource(Script, 'exercises.js')

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

    def export(self):
        return "\n\n".join((self._header(),
                            self._export_instructions(),
                            '<form name="%s" action="">' % self._form_name(),
                            "\n".join(map(self._export_task, self._tasks)),
                            self._results(),
                            '</form>',
                            script(self._init_script())))
    
    def _form_name(self):
        return "exercise_%s" % id(self)
    
    def _form(self):
        return "document.forms['%s']" % self._form_name()
    
    def _instructions(self):
        return ""

    def _sound_controls(self, label, media, transcript=None):
        if transcript is not None:
            t = link(_("show transcript"), transcript.url(),
                     target="transcript", brackets=True)
        else:
            t = ""
        f = ('<form class="sound-control" action="">%s:' % label,
             button(_("Play"), "play_audio('%s')" % media.url()),
             button(_("Stop"), 'stop_audio()'), t, '</form>')
        a = '<p>%s: %s %s</p>' % \
            (label, link(_("Play"), media.url(), brackets=True), t)
        return script_write('\n'.join(f), a)
        
    
    def _export_instructions(self):
        """Return the HTML formatted instructions for this type of exercise."""
        result = "<p>" + self._instructions() + ' ' + \
                 link(_("detailed instructions"),
                      "instructions-%s.html" % self.id(),
                      target='help', brackets=True) + "</p>"
        if self._recording is not None:
            result += '\n\n' + self._sound_controls(_("Recording"),
                                                    self._recording,
                                                    self._transcript)
        if self._audio_version is not None:
            label = self._AUDIO_VERSION_LABEL
            result += '\n\n' + self._sound_controls(label, self._audio_version)
        return result

    def _init_script(self):
        return ''
        
    def _export_task(self, task):
        raise "This Method must be overriden"

    def _results(self):
        return ""

    
class SentenceCompletion(Exercise):
    """Filling in gaps in sentences by typing in the correct completion."""

    _NAME = _("Sentence Completion")
    _AUDIO_VERSION_REQUIRED = True
    _AUDIO_VERSION_LABEL = _("The exercise")

    def _instructions(self):
        
        return _("""This exercise can be only done purely aurally/orally.  You
        will hear some of the sentences from the previous exercise unfinished
        and your goal is to say the missing part.""")

    def _export_task(self, task):
        return ""

    
class _Cloze(Exercise):

    _TASK_TYPE = ClozeTask
    
    def __init__(self, parent, *args, **kwargs):
        super(_Cloze, self).__init__(parent, *args, **kwargs)
        parent.resource(Media, 'all-correct-response.ogg', shared=True,
                        tts_input='everything correct!')
        parent.resource(Media, 'all-wrong-response.ogg', shared=True,
                        tts_input='all the answers are wrong!')
        parent.resource(Media, 'some-wrong-response.ogg', shared=True,
                        tts_input='some of the answers are wrong!')

    def _init_script(self):
        answers = ",".join(map(lambda a: "'%s'" % a.replace("'", "\\'"),
                               reduce(lambda a, b: a + b,
                                      map(lambda t: t.answers(), self._tasks))))
        return "init_cloze_form(%s, [%s])" % (self._form(), answers)

    def _results(self):
        r = ('<p class="results">Results: ', 
             field('Use the Evaluate button to see the results.',
                   name='result', size=70, readonly=True), '<br/>',
             button('Evaluate', "eval_cloze(%s)" % self._form()),
             button('Fill', "fill_cloze(%s)" % self._form()),
             '<input type="reset" value="Reset">',
             '</p>')
        return script_write("\n".join(r))

    def _make_field(self, match):
        return field(cls='cloze', size=len(match.group(1))+1)
    
    def _export_task(self, task):
        return "\n".join(('<p>', task.text(self._make_field), '</p>'))
    
class Cloze(_Cloze):
    """Filling in gaps in text by typing the correct word."""

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

        
class _ChoiceBasedExercise(Exercise):

    _TASK_FORMAT = '<p>%s\n<div class="choices">\n%s\n</div></p>\n'

    def _answer_control(self, task, text, correct):
        self._parent.resource(Script, 'audio.js')
        if correct: 
            media = self._parent.resource(Media, 'correct-response.ogg',
                                          shared=True,
                                          tts_input=_('Correct'))
        else:
            media = self._parent.resource(Media, 'incorrect-response.ogg',
                                          shared=True,
                                          tts_input=_('You are wrong!'))
        handler = "eval_choice(%s, %d, %d, %d, '%s')" % \
                  (self._form(), self._tasks.index(task), len(self._tasks),
                   correct and 1 or 0, media.url())
        b = button(text, handler, cls='answer-control')
        a = link(text, media.url())
        return script_write(b, a)
    
    def _results(self):
        r = '<p class="results">Answered: %s<br/>\nCorrect: %s %s</p>' % \
            (field(name='answered', size=5, readonly=True),
             field(name='result', size=8, readonly=True),
             button('Reset', "reset_choices(%s, %d)" % \
                    (self._form(), len(self._tasks))))
        return script_write(r, '')

    def _format_choice(self, task, choice):
        a = chr(ord('a') + task.choice_index(choice)) + ')'
        ctrl = self._answer_control(task, a, choice.correct())
        return '&nbsp;' + ctrl + '&nbsp;' + choice.answer() + '<br/>'
        
    def _export_task(self, task):
        choices = "\n".join(map(lambda ch: self._format_choice(task, ch),
                                task.choices()))
        return self._TASK_FORMAT % (task.prompt(), choices)
        
    
class TrueFalseStatements(_ChoiceBasedExercise):
    """Exercise Comprising of a list of statements.

    This class overrides the constructor to provide a more comfortable way to
    specify this concrete type of exercise and to allow more detailed checking
    of this specification.
    
    """
    _TASK_TYPE = TrueFalseStatement
    _NAME = _("True/False Statements")
    _TASK_FORMAT = "<p>%s\n%s</p>\n"
    
    def _instructions(self):
        return _("""For each of the %d statements below indicate whether you
        think they are true or false.""") % len(self._tasks)

    def _format_choice(self, task, choice):
        return self._answer_control(task, choice.answer(), choice.correct())
    
    
class MultipleChoiceQuestions(_ChoiceBasedExercise):
    """An Exercise with MultipleChoiceQuestion tasks."""
    
    _TASK_TYPE = MultipleChoiceQuestion
    _NAME = _("Multiple Choice Questions")
    
    def _instructions(self):
        return _("""For each of the %d questions below choose the correct
        answer from the list.""") % len(self._tasks)

    
class Selections(_ChoiceBasedExercise):
    """An Exercise with Selection tasks."""
    
    _TASK_TYPE = Selection
    _NAME = _("Select the Correct One")
    
    def _instructions(self):
        return _("""For each of the %d pairs of statements below decide which
        one is correct.""") % len(self._tasks)

    
class GapFilling(_ChoiceBasedExercise):
    """An exercise composed of GapFillStatement tasks."""

    _TASK_TYPE = GapFillStatement
    _NAME = _("Gap Filling")

    def _instructions(self):
        return _("""For each of the %d sentences below choose the correct piece
        of text from the list to fill in the gap.""") % len(self._tasks)

    
class VocabExercise(_Cloze):
    _NAME = _("Vocabulary Practice")

    def _instructions(self):
        return _("""You will hear a word or expression in your language.  Say
        it in English and listen to the model pronunciation.""")
    
    def _export_task(self, task):
        return task.text(self._make_field)+'<br/>'

    
class Transformation(_Cloze):
    """Transform a whole sentence and write it down."""

    _TASK_TYPE = TransformationTask
    _NAME = _("Transformation")

    def _instructions(self):
        return _("""Listen to the recording and transform each of the %d
        sentences below according to the instructions.""") % len(self._tasks)

    def _export_task(self, task):
        return "\n".join(('<p>',
                          task.orig(), '<br/>',
                          task.text(self._make_field),
                          '</p>'))

    
class Substitution(Transformation):
    _NAME = _("Substitution")

    def _instructions(self):

        return _("""Substitute a part of each sentence using the text in
        brackets.""")
    
class Dictation(_Cloze):
    _NAME = _("Dictation")
    
    def _instructions(self):
        return """This exercise type is not yet implemented..."""
