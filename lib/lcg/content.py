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

    def _field(self, text='', name='', size=20, cls=None, readonly=False):
        f = '<input type="text" name="%s" class="%s" value="%s" size="%d"%s>'
        return f % (name, cls and 'text ' + cls or 'text', text, size,
                    readonly and ' readonly' or '')

    def _button(self, label, handler, cls=None):
        cls = cls and 'button ' + cls or 'button'
        return '<input type="button" value="%s"' % label + \
               ' class="%s" onClick="javascript: %s">' % (cls, handler)

    def _script(self, code, noscript=None):
        noscript = noscript and '<noscript>'+ noscript +'</noscript>' or ''
        return '<script type="text/javascript" language="Javascript"><!--\n' + \
               code +' //--></script>' + noscript
        
    def _script_write(self, content, noscript=None):
        c = content.replace('"','\\"').replace('\n','\\n').replace("'","\\'")
        return self._script('document.write("'+ c +'");', noscript)

    def _speaking_text(self, text, media):
        self._parent.script('audio.js')
        a1 = '<a class="speaking-text"' + \
             ' href="javascript: play_audio(\'%s\')">%s</a>' % \
             (media.url(), text)
        a2 = '<a href="%s">%s</a>' % (media.url(), text)
        return self._script_write(a1, a2)

    def export(self):
        """Return the HTML formatted content as a string."""
        return ''
 
    
class Container(Content):
    """Container of multiple parts, each of which is a 'Content' instance.

    'Container' exports all the parts concatenated in unchanged order.

    """

    def __init__(self, parent, parts):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          parts -- Sequence of 'Content' instances in the order in which they
            should appear in the output..

        """
        super(Container, self).__init__(parent)
        self._parts = parts
        
    def export(self):
        return '\n'.join(map(lambda p: p.export(), self._parts))

    
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

    def export(self):
        rows = map(lambda i: '<tr><td>%s %s</td><td>%s</td></tr>' % \
                   (self._speaking_text(i.word(), i.media()),
                    i.note(), i.translation()),
                   self._items)
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
        self._media = parent.media(filename, tts_input=word)


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

    
class Exercise(Content):
    """Exercise consists of an assignment and a set of tasks."""

    _TASK_TYPE = Task
    _NAME = None
    
    def __init__(self, parent, tasks, sound_file=None, transcript=None):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this content element is part of.
          tasks -- sequence of 'Task' instances related to this exercise.
          sound_file -- name of the file with a recording (string).  Some
            exercises may not include a recording, so this argument is not
            mandatory.  When specified, the 'transcript' arguemnt below must be
            also given.
          transcript -- name of the file with a textual transcript of the
            recording (string).  This argument is mandatory when the
            'sound_file' arguemnt is specified (and not None).
          
        """
        super(Exercise, self).__init__(parent)
        assert is_sequence_of(tasks, self._TASK_TYPE), \
               "Tasks must be a sequence of '%s' instances!: %s" % \
               (self._TASK_TYPE.__name__, tasks)
        assert sound_file is None or isinstance(sound_file, types.StringTypes)
        self._number = parent.counter().next()
        self._tasks = list(tasks)
        if sound_file is not None:
            if transcript is None:
                transcript = os.path.splitext(sound_file)[0] + '.txt'
            assert isinstance(transcript, types.StringTypes)
            transcript_filename = os.path.join(parent.src_dir(), transcript)
            assert os.path.exists(transcript_filename), \
                   "Transcript file not found: %s" % transcript_filename
            self._recording = parent.media(sound_file)
        else:
            self._recording = None
        self._transcript = transcript
        parent.script('audio.js')
        parent.script('exercises.js')

    def task_type(self):
        return self._TASK_TYPE
    task_type = classmethod(task_type)

    def export(self):
        return "\n\n".join((self._header(),
                            self._export_instructions(),
                            '<form name="%s" action="">' % self._form_name(),
                            "\n".join(map(self._export_task, self._tasks)),
                            self._results(),
                            '</form>',
                            self._script(self._init_script())))
    
    def _form_name(self):
        return "exercise_%s" % id(self)
    
    def _form(self):
        return "document.forms['%s']" % self._form_name()
    
    def _header(self):
        return "<h3>%s %d &ndash; %s</h3>" % (_("Exercise"), self._number,
                                              self._NAME)
    
    def _instructions(self):
        return ""

    def _export_instructions(self):
        """Return the HTML formatted instructions for this type of exercise."""
        result = "<p>" + self._instructions() + "</p>"
        if self._recording is not None:
            url = self._recording.url()
            f = ('<form class="sound-control" action="">%s:' % _("Recording"),
                 self._button(_("Play"), "play_audio('%s')" % url),
                 self._button(_("Stop"), 'stop_audio()'),
                 '</form>')
            a = '<p>%s: [<a href="%s">Play</a>]</p>' % (_("Recording"), url)
            result += '\n\n'+ self._script_write('\n'.join(f), a)
        return result

    def _init_script(self):
        return ''
        
    def _export_task(self, task):
        raise "This Method must be overriden"


class Cloze(Exercise):
    """Filling in gaps in text by typing the correct word."""

    _TASK_TYPE = ClozeTask
    _NAME = _("Cloze")

    
    def __init__(self, parent, *args, **kwargs):
        super(Cloze, self).__init__(parent, *args, **kwargs),
        parent.media('all-correct-response.ogg', shared=True,
                     tts_input='everything correct!')
        parent.media('all-wrong-response.ogg', shared=True,
                     tts_input='all the answers are wrong!')
        parent.media('some-wrong-response.ogg', shared=True,
                     tts_input='some of the answers are wrong!')

    def _instructions(self):
        if self._recording is None:
            return """You will hear a short recording.  Listen carefully and
            then fill in the gaps in the text below using the same words.
            After filling all the gaps, check your results using the buttons
            below the text."""
        else:
            return """Fill in the gaps in the text below using the a suitable
            word.  After filling all the gaps, check your results using the
            buttons below the text.  Sometimes there might be more correct
            answers, but the evaluation only recognizes one.  Contact the tutor
            when in doubt."""

    def _init_script(self):
        answers = ",".join(map(lambda a: "'%s'" % a.replace("'", "\\'"),
                               reduce(lambda a, b: a + b,
                                      map(lambda t: t.answers(), self._tasks))))
        return "init_cloze_form(%s, [%s])" % (self._form(), answers)

    def _results(self):
        r = ('<p class="results">Results: ', 
             self._field('Use the Evaluate button to see the results.',
                         name='result', size=70, readonly=True), '<br/>',
             self._button('Evaluate', "eval_cloze(%s)" % self._form()),
             self._button('Fill', "fill_cloze(%s)" % self._form()),
             '<input type="reset" value="Reset">',
             '</p>')
        return self._script_write("\n".join(r))

    def _make_field(self, match):
        return self._field(cls='cloze', size=len(match.group(1))+1)
    
    def _export_task(self, task):
        return "\n".join(('<p>', task.text(self._make_field), '</p>'))
    

class _ChoiceBasedExercise(Exercise):

    _TASK_FORMAT = '<p>%s\n<div class="choices">\n%s\n</div></p>\n'

    def _answer_control(self, task, text, correct):
        self._parent.script('audio.js')
        if correct: 
            media = self._parent.media('correct-response.ogg', shared=True,
                                       tts_input=_('Correct'))
        else:
            media = self._parent.media('incorrect-response.ogg', shared=True,
                                       tts_input=_('You are wrong!'))
        handler = "eval_choice(%s, %d, %d, %d, '%s')" % \
                  (self._form(), self._tasks.index(task), len(self._tasks),
                   correct and 1 or 0, media.url())
        b = self._button(text, handler, cls='answer-control')
        a = '<a href="%s">%s</a>' % ('media.url()', text)
        return self._script_write(b, a)
    
    def _results(self):
        r = '<p class="results">Answered: %s<br/>\nCorrect: %s %s</p>' % \
            (self._field(name='answered', size=5, readonly=True),
             self._field(name='result', size=8, readonly=True),
             self._button('Reset', "reset_choices(%s, %d)" % \
                          (self._form(), len(self._tasks))))
        return self._script_write(r, '')

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
        return """A list of %d statements follows.  After each sentence,
        there are two links.  Select 'TRUE' if you think the sentence is true,
        or select 'FALSE' if you think it is false.""" % len(self._tasks)

    def _format_choice(self, task, choice):
        return self._answer_control(task, choice.answer(), choice.correct())
    
    
class MultipleChoiceQuestions(_ChoiceBasedExercise):
    """An Exercise with MultipleChoiceQuestion tasks."""
    
    _TASK_TYPE = MultipleChoiceQuestion
    _NAME = _("Multiple Choice Questions")
    
    def _instructions(self):
        return """Below is a list of %d questions.  For each question choose
        from the list of possible answers and check your choice by activating
        the link.""" % len(self._tasks)

    
class Selections(_ChoiceBasedExercise):
    """An Exercise with Selection tasks."""
    
    _TASK_TYPE = Selection
    _NAME = _("Select the Correct One")
    
    def _instructions(self):
        return """For each of the %d pairs of statements, decide which one is
        correct.  Activate the link to check the result.""" % len(self._tasks)

    
class GapFilling(_ChoiceBasedExercise):
    """An exercise composed of GapFillStatement tasks."""

    _TASK_TYPE = GapFillStatement
    _NAME = _("Gap Filling")

    def _instructions(self):
        return """Select a word from the list below each sentence to fill in
        the gap.  Activate the link made by the word to check the result."""

    
class VocabExercise(Cloze):
    _NAME = _("Vocabulary from English")

    def __init__(self, parent, items, *args, **kwargs):
        kwargs['tasks'] = [self._create_task(item) for item in items]
        super(Cloze, self).__init__(parent, *args, **kwargs),

    def _create_task(self, item):
        return ClozeTask("%s: [%s]" % (item.word(), item.translation()))

    def _instructions(self):
        return _("""Listen to the expression in English and repeat. You will
        hear a transltion into your language.""")
    
    def _export_task(self, task):
        return task.text(self._make_field)+'<br/>'

    
class VocabExercise2(VocabExercise):
    _NAME = _("Vocabulary to English")

    def _create_task(self, item):
        return ClozeTask("%s: [%s]" % (item.translation(), item.word()))

    def _instructions(self):
        return _("""You will hear each item in your language.  Say the word or
        expression in English and listen to the model pronunciation, then type
        the word into the box.""")

    
class SentenceCompletion(Cloze):
    """Filling in gaps in sentences by typing in the correct completion."""

    _NAME = _("Sentence Completion")

    def _instructions(self):
        return """You will hear a recording comprising %d sentences.  Below,
        you will find the same sentences unfinished.  Fill in the missing text
        and check your results using the buttons below all the sentences.""" % \
        len(self._tasks)

        
class Transformation(Cloze):
    """Transform a whole sentence and write it down."""

    _TASK_TYPE = TransformationTask
    _NAME = _("Transformation")

    def _instructions(self):
        return """Listen to the recording and transform each of the %d
        sentences below according to the instructions.  Check your results
        using the buttons below all the sentences.""" % len(self._tasks)

    def _export_task(self, task):
        return "\n".join(('<p>',
                          task.orig(), '<br/>',
                          task.text(self._make_field),
                          '</p>'))


class Dictation(Cloze):
    
    def _instructions(self):
        return """This exercise type is not yet implemented..."""
    
   
    
################################################################################

class Resource(object):
    """Representation of an external resource, the content depends on.

    Any 'ContentNode' (or more often a piece of 'Content' within it) can depend
    on several external resources.  They are maintained by parent 'ContentNode'
    so that the node is able to keep track of all the resources it depends on.
    
    This is a base class for particular resource types, such as `Media' or
    `Script'.

    """
    SUBDIR = 'resources'
    
    def __init__(self, parent, file, shared=True, check_file=True):
        """Initialize the instance.

        Arguments:

          parent -- parent 'ContentNode' instance; the actual output document
            this resource belongs to.
          file -- path to the actual resource file relative to its parent
            node's source/destination directory.
          shared -- a boolean flag indicating that the file may be shared by
            multiple nodes (is not located within the node-specific
            subdirectory, but rather in a course-wide resource directory).
          check_file -- if true, an exception will be risen when the source file
            can not be found.

        """
        assert isinstance(parent, ContentNode), \
               "Not a 'ContentNode' instance: %s" % parent
        self._parent = parent
        self._file = file
        self._shared = shared
        if shared:
            src_dirs = [os.path.join(d, self.SUBDIR)
                        for d in (self._parent.root_node().src_dir(),
                                  self._parent.default_resource_dir())]
            dst_subdir = self.SUBDIR
        else:
            src_dirs = (parent.src_dir(), )
            dst_subdir = os.path.join(self.SUBDIR, parent.subdir())
        self._src_path = self._find_source_file(src_dirs, file)
        self._dst_path = os.path.join(dst_subdir, file)
        if check_file:
            assert os.path.exists(self._src_path), \
                   "Resource file '%s' doesn't exist!" % self._src_path
        
    def _find_source_file(self, dirs, file):
        for d in dirs:
            path = os.path.join(d, file)
            if os.path.exists(path):
                return path
        return os.path.join(dirs[0], file)
                
    def _destination_file(self, dir):
        return os.path.join(dir, self._dst_path)

    def url(self):
        return '/'.join(self._dst_path.split(os.path.sep))

    def name(self):
        return "%s_%s" % (self.__class__.__name__.lower(), id(self))

    def export(self, dir):
        dst_path = self._destination_file(dir)
        if not os.path.exists(dst_path) or \
               os.path.exists(self._src_path) and \
               os.path.getmtime(dst_path) < os.path.getmtime(self._src_path):
            if not os.path.isdir(os.path.dirname(dst_path)):
                os.makedirs(os.path.dirname(dst_path))
            self._export(dir)
            
    def _export(self, dir):
        shutil.copy(self._src_path, self._destination_file(dir))
        print "%s: file copied." % self._destination_file(dir)


class Media(Resource):
    """Representation of a media object used within the content.

    'Media' instances should not be constructed directly.  Use the
    'ContentNode.media()' method instead.

    """
    SUBDIR = 'media'
    
    def __init__(self, parent, file, shared=False, tts_input=None):
        """Initialize the instance.

        Arguments:

          parent, file, shared -- See 'Resource.__init__()'.
          tts_input -- if defined and the source file does not exist, the
            destination file will be generated via TTS.  The given string will
            be synthesized.

        """
        ext = os.path.splitext(file)[1]
        assert ext in ('.ogg','.mp3','.wav'), "Unsupported media type: %s" %ext
        super(Media, self).__init__(parent, file, shared=shared,
                                    check_file=(tts_input is None))
        self._tts_input = tts_input   
        
    def _find_source_file(self, dirs, file):
        basename, extension = os.path.splitext(file)
        for ext in ('.ogg','.mp3','.wav','.tts.txt', '.txt'):
            path = super(Media, self)._find_source_file(dirs, basename + ext)
            if os.path.exists(path):
                return path
        return super(Media, self)._find_source_file(dirs, file)

    def _command(self, which, errmsg):
        var = 'LCG_%s_COMMAND' % which
        try:
            return os.environ[var]
        except KeyError:
            raise "Environment variable %s not set!\n" % var + errmsg

    def _open_stream_from_tts(self):
        if self._tts_input is not None:
            text = self._tts_input
        else:
            fh = codecs.open(self._src_path,
                             encoding=self._parent.input_encoding())
            text = ''.join(fh.readlines())
            fh.close()
        cmd = self._command('TTS', "Specify a TTS command synthesizing " + \
                            "the text on STDIN to a wave on STDOUT.")
        print "  - generating with TTS: %s" % cmd
        input, output = os.popen2(cmd, 'b')
        input.write(text.encode(self._parent.input_encoding()))
        input.close()
        return output
    
    def _open_stream_from_encoder(self, output_format, wave):
        # The tmp file is a hack.  It would be better to send the data into a
        # pipe, but popen2 gets stuck while reading it.  Why?
        tmp = os.tmpnam() + '.wav'
        self._tmp_files.append(tmp)
        f = open(tmp, 'wb')
        copy_stream(wave, f)
        f.close()
        cmd = self._command(output_format, "Specify a command encoding a " + \
                            "wave on STDIN to %s on STDOUT." % output_format)
        print "  - converting to %s: %s" % (output_format, cmd)
        output = os.popen('cat %s |' % tmp + cmd)
        #input, output = os.popen2(convert_cmd)
        #copy_stream(wave, input)
        #input.close()
        return output

    
    def _export(self, dir):
        # Either create the file with tts or copy from source directory.
        input_format = os.path.splitext(self._src_path)[1].upper()[1:]
        output_format = os.path.splitext(self._dst_path)[1].upper()[1:]
        if input_format == output_format and os.path.exists(self._src_path):
            return super(Media, self)._export(dir)
        dst_path = self._destination_file(dir)
        wave = None
        data = None
        self._tmp_files = []
        try:
            print dst_path + ':'
            # Open the input stream
            if input_format == 'WAV' and os.path.exists(self._src_path):
                wave = open(self._src_path)
            elif input_format in ('TXT', 'TTS.TXT') or \
                     self._tts_input is not None:
                wave = self._open_stream_from_tts() 
            else:
                raise "Unknown input format: %s" % input_format
            if output_format == 'WAV':
                data = wave
            else:
                data = self._open_stream_from_encoder(output_format, wave)
            # Write the output stream
            output_file = open(dst_path, 'wb')
            copy_stream(data, output_file)
            output_file.close()
        finally:
            if wave is not None:
                wave.close()                
            if data is not None:
                data.close()
            # This is just because of the hack in _open_output_stream().
            for f in self._tmp_files:
                os.remove(f)
        
        
class Script(Resource):
    """Representation of a script object used within the content.

    The 'Script' instances should not be constructed directly.  Use the
    'ContentNode.script()' method instead.

    """
    SUBDIR = 'scripts'

    
class Stylesheet(Resource):
    """Representation of a stylesheet used within the content.

    The 'Stylesheet' instances should not be constructed directly.  Use the
    'ContentNode.stylesheet()' method instead.

    """
    SUBDIR = 'css'

