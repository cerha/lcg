# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2015 Brailcom, o.p.s.
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

__version__ = '0.6.1'

"""Learning Content Genarator."""

from . import config
from .locales import LocaleData, LocaleData_cs, LocaleData_de, \
    LocaleData_en, LocaleData_es, LocaleData_no, LocaleData_pl, \
    LocaleData_sk

from .i18n import TranslatableTextFactory, TranslatedTextFactory, \
    Localizable, TranslatableText, SelfTranslatableText, \
    TranslatablePluralForms, LocalizableDateTime, LocalizableTime, \
    Decimal, Monetary, Concatenation, Translator, NullTranslator, \
    GettextTranslator, Localizer, \
    concat, format, source_files_by_domain

from .util import is_sequence_of, camel_case_to_lower, text_to_id, \
    unindent_docstring, positive_id, log, caller, \
    language_name, country_name, week_day_name, month_name, \
    attribute_value, ParseError

from .nodes import ContentNode, Variant, Metadata

from .resources import Resource, Image, Stylesheet, Script, Translations, \
    Media, Audio, Video, Flash, ResourceProvider

from .units import Unit, UAny, UFont, UMm, UPoint, USpace, FontFamily, \
    HorizontalAlignment, VerticalAlignment, Orientation

from .content import Content, Container, Strong, Emphasized, \
    Underlined, Code, Citation, Quotation, Superscript, Subscript, \
    TextContent, Link, Abbreviation, Anchor, InlineImage, InlineAudio, \
    InlineVideo, InlineExternalVideo, Title, HorizontalSeparator, \
    NewPage, NewLine, PageNumber, PageHeading, HSpace, VSpace, \
    HtmlContent, Heading, PreformattedText, Paragraph, ItemizedList, \
    DefinitionList, FieldSet, TableCell, TableHeading, TableRow, \
    Table, Section, TableOfContents, NodeIndex, RootIndex, NoneContent, \
    SetVariable, Substitution, Figure, MathML, \
    coerce, join, link, dl, ul, ol, fieldset, p, strong, em, u, \
    code, cite, container, br, hr, pre, abbr 

from .widgets import Widget, FoldableTree, Notebook, PopupMenuCtrl, \
    PopupMenuItem, CollapsiblePane

from .presentation import Presentation, ContentMatcher, \
    TopLevelMatcher, LanguageMatcher, LCGClassMatcher, \
    LCGHeadingMatcher, LCGContainerMatcher, PresentationSet, \
    StyleFile

from .exercises import Task, TextTask, ContentTask, Choice, \
    ChoiceTask, TrueFalseTask, ExerciseParser, Exercise, \
    MultipleChoiceQuestions, Selections, TrueFalseStatements, \
    GapFilling, HiddenAnswers, FillInExercise, VocabExercise, \
    WrittenAnswers, NumberedCloze, Cloze, ModelCloze

from .export.export import Exporter, FileExporter, TextExporter, \
    UnsupportedElementType, SubstitutionIterator

from .export.html import HtmlEscapedUnicode, HtmlGenerator, \
    XhtmlGenerator, HtmlExporter, Html5Exporter, HtmlFileExporter, \
    StyledHtmlExporter, HtmlStaticExporter, format_text

from .export.epub import EpubHtml5Exporter
from .export.ims import IMSExporter
from .export.hhp import HhpExporter

from .export.exercises_html import ExerciseExporter, \
    MultipleChoiceQuestionsExporter, SelectionsExporter, \
    TrueFalseStatementsExporter, GapFillingExporter, \
    HiddenAnswersExporter, VocabExerciseExporter, \
    WrittenAnswersExporter, NumberedClozeExporter, \
    ClozeExporter, ModelClozeExporter

try:
    from .export.braille import BrailleError, BrailleExporter, \
        braille_presentation, xml2braille
except ImportError:
    pass

try:
    from .export import pdf # For backwards compatibility
    from .export.pdf import PDFExporter
except ImportError:
    pass

from .parse import ProcessingError, Parser, MacroParser, HTMLProcessor, \
    html2lcg, add_processing_info

from .read import Reader, FileReader, StructuredTextReader, DocFileReader, \
    DocDirReader, reader

from .transform import data2content, data2html, html2data, \
    HTML2XML, XML2HTML, XML2Content

