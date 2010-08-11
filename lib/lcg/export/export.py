# -*- coding: utf-8 -*-
#
# Copyright (C) 2004-2010 Brailcom, o.p.s.
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

"""Framework for exporting LCG content into various output formats.

The module contains the following important classes:

  'Exporter' :: Generic exporter class defining the common interface that must
    be supported by derived exporters for particular output formats.

  'MarkupFormatter' :: 

See documentation of the individual classes for more details.

"""

from lcg import *
import shutil


class MarkupFormatter(object):
    """Simple inline ASCII markup formatter.

    This simple formatter can only format the markup within one block (ie. a
    single paragraph or other non-structured piece of text).  Parsing the
    higher level document structure (headings, paragraphs, bullet lists etc.)
    is done on the LCG input.  Formatting the inline markup, on the other hand,
    is done on LCG output (export).

    """
    _IMG_EXT = r'\.(?:jpe?g|png|gif)'
    _MARKUP = (('linebreak', '//'),
               ('emphasize', ('/',  '/')),
               ('strong',    ('\*', '\*')),
               ('fixed',     ('=',  '=')),
               ('underline', ('_',  '_')),
               ('citation',  ('>>', '<<')),
               ('quotation', ('``', "''")),
               # Link to an inside or outside (http) source via [ ], see _link_formatter()
               ('link', (r'\['
                         r'(?P<align>[<>])?'                                # Left/right Image aligment e.g. [<imagefile], [>imagefile]
                         r'(?P<href>[^\[\]\|\#\s]*?'                        # The link target e.g. [src]
                         r'(?:(?P<imgname>[^\[\]\|\#\s/]+)'+_IMG_EXT+')?)'  # If the target is an image, imgname is its file name without extension.  It is used for CSS class to allow individual image styling.
                         r'(?:#(?P<anchor>[^\[\]\|\s]*))?'                  # Anchor ex. [#topic11]
                         r'(?::(?P<size>\d+x\d+))?'                         # Optional explicit image (or video) size e.g. [image.jpg:30x40])
                         r'(?:(?:\s*\|\s*|\s+)'                             # Separator (pipe is enabled for backwards compatibility, but space is the official separator)
                         r'(?:(?P<label_img>[^\[\]\|\s]+'+_IMG_EXT+'))?'    # Link label image (a link displayed as a clickable image)
                         r'(?P<label>[^\[\]\|]*))?'                         # Label text
                         r'(?:(?:\s*\|\s*)(?P<descr>[^\[\]]*))?'            # Description after | [src Label | Description] 
                         r'\]')),
               # Link directly in the text starting with http(s)/ftp://, see _uri_formatter()
               ('uri', (r'(?:https?|ftp)://\S+?(?:(?P<imgname_>[^\#\s/]+)'+ _IMG_EXT +\
                        r')?(?=[\),.:;]*(\s|$))')),   # ?!? SOS!
               ('email', r'\w[\w\-\.]*@\w[\w\-\.]*\w'),
               ('substitution', (r"(?!\\)\$(?P<subst>[a-zA-Z][a-zA-Z_]*(\.[a-zA-Z][a-zA-Z_]*)?" + \
                                 "|\{[^\}]+\})")),
               ('comment', r'^#.*'),
               ('dash', r'(^|(?<=\s))--($|(?=\s))'),
               ('nbsp', '~'))
    
    _HELPER_PATTERNS = ('align', 'href', 'imgname', 'imgname_', 'anchor', 'label', 'label_img',
                        'descr', 'subst', 'size')

    _FORMAT = {'linebreak': '\n',
               'comment': '',
               'dash': u'—',
               'nbsp': u' '}

    _BLANK_MATCHER = re.compile('\s+')
    _IMAGE_ALIGN_MAPPING = {'>': InlineImage.RIGHT, '<': InlineImage.LEFT}
    _VIMEO_VIDEO_MATCHER = re.compile(r"http://(www.)?vimeo.com/(?P<video_id>[0-9]*)")
    _YOUTUBE_VIDEO_MATCHER = re.compile(
        r"http://(www.)?youtube.com/watch\?v=(?P<video_id>[a-zA-z0-9_-]*)")

    def __init__(self):
        regexp = r"(?P<%s>\\*%s)"
        pair_regexp = '|'.join((regexp % ("%s_end",   r"(?<=\S)%s(?!\w)"),
                                regexp % ("%s_start", r"(?<!\w)%s(?=\S)")))
        regexps = [isinstance(markup, str) and regexp % (type, markup)
                   or pair_regexp % (type, markup[1], type, markup[0])
                   for type, markup in self._MARKUP]
        self._rules = re.compile('(?:' +'|'.join(regexps)+ ')',
                                 re.MULTILINE|re.UNICODE|re.IGNORECASE)
        self._paired_on_output = [type for type, format in self._FORMAT.items()
                                  if isinstance(format, tuple)]
    
    def _markup_handler(self, context, match):
        exporter = context.exporter()
        type = [key for key, m in match.groupdict().items()
                if m and not key in self._HELPER_PATTERNS][0]
        markup = match.group(type)
        backslashes = markup.count('\\')
        markup = exporter.escape(markup[backslashes:])
        prefix = exporter.escape(backslashes / 2 * '\\')
        if backslashes % 2:
            return exporter.concat(prefix, markup)
        # We need two variables (start and end), because both can be False for
        # unpaired markup.
        start = False
        end = False
        if type.endswith('_start'):
            type = type[:-6]
            start = True
        elif type.endswith('_end'):
            type = type[:-4]
            end = True
        if not start and self._open and type == self._open[-1]:
            # Closing an open markup.
            self._open.pop()
            result = self._formatter(context, type, match.groupdict(), close=True)
        elif not end and not (start and type in self._open):
            # Start markup or an unpaired markup.
            if start:
                self._open.append(type)
            result = self._formatter(context, type, match.groupdict())
        else:
            # Markup in an invalid context is just printed as is.
            # This can be end markup, which was not opened or start markup,
            # which was already opened.
            result = markup
        return exporter.concat(prefix, result)

    def _substitution_formatter(self, context, subst, **kwargs):
        exporter = context.exporter()
        # get the substitution value for _SUBSTITUTION_REGEX match
        if subst.startswith('{') and subst.endswith('}'):
            text = subst[1:-1]
        else:
            text = subst
        if not text:
            return exporter.escape('$' + subst)
        result = context.node().globals()
        for name in text.split('.'):
            try:
                result = result[str(name)]
            except KeyError:
                return exporter.escape('$' + subst)
        if isinstance(result, Content):
            result = result.export(context)
        else:
            if not isinstance(result, Localizable):
                result = str(result)
            result = exporter.escape(result)
        return result
    
    def _link_formatter(self, context, href=None, imgname=None, anchor=None, size=None,
                        label_img=None, label=None, descr=None, align=None, **kwargs):
        parent = context.node()
        target = None
        # Prepare the link data like name, description, target
        # TODO: This fails to prepare an Audio() object if the file
        # is link to audio file via http://
        if label:
            label=label.strip()
        if href and not anchor:
            target = parent.resource(href, warn=False)
            if not target and imgname:
                target = Image(href, uri=href)
        if target is None:
            node = None
            if not href:
                node = parent
            elif href.find('@') == href.find('/') == -1:
                node = parent.root().find_node(href)
                if not node:
                    log("%s: Unknown node: %s" % (parent.id(), href))
            target = node
            if node and anchor:
                target = node.find_section(anchor, context)
                if target is None:
                    log("%s: Unknown section: %s:%s" %
                        (parent.id(), node.id(), anchor))
        if target is None:
            if anchor is not None:
                href += '#'+anchor
            target = Link.ExternalTarget(href, label or href)
        if size:
            size = tuple(map(int, size.split('x')))
        if label_img:
            label_image = parent.resource(label_img, warn=False)
            if label_image is None or not isinstance(label_image, Image):
                label_image = Image(label_img, uri=label_img)
        else:
            label_image = None
        # Create the resulting content element and return its exported string.
        if not label_image and isinstance(target, Image):
            result = InlineImage(target, title=label, descr=descr, name=imgname,
                                 align=self._IMAGE_ALIGN_MAPPING.get(align), size=size)
        elif isinstance(target, Audio):
            result = InlineAudio(target, title=label, descr=descr, image=label_image, shared=True)
        elif isinstance(target, Video):
            result = InlineVideo(target, title=label, descr=descr, image=label_image, size=size)
        else:
            youtube_match = self._YOUTUBE_VIDEO_MATCHER.match(href)
            vimeo_match = self._VIMEO_VIDEO_MATCHER.match(href)
            if youtube_match:
                video_id = youtube_match.group("video_id")
                result = InlineExternalVideo('youtube', video_id, size=size)
            elif vimeo_match:
                video_id = vimeo_match.group("video_id")
                result = InlineExternalVideo('vimeo', video_id, size=size)
            else:
                if label_image:
                    name = os.path.splitext(os.path.basename(label_img))[0]
                    label = InlineImage(label_image, title=label, name=name,
                                    align=self._IMAGE_ALIGN_MAPPING.get(align))
                #if isinstance(target, Link.ExternalTarget):
                #    target = Link.ExternalTarget(href, label or href)
                result = Link(target, label=label, descr=descr)
        result.set_parent(parent)
        return result.export(context)

    
    def _uri_formatter(self, context, uri, imgname_, close=False, **kwargs):
        return self._link_formatter(context, href=uri, label=None, imgname=imgname_)

    def _formatter(self, context, type, groups, close=False):
        try:
            formatter = getattr(self, '_'+type+'_formatter')
        except AttributeError:
            formatter = None
        if formatter is not None:
            result = formatter(context, close=close, **groups)
        else:
            f = self._FORMAT.get(type, '')
            if type in self._paired_on_output and f:
                if close:
                    result = f[1]
                else:
                    result = f[0]
            else:
                result = f
        return result
        
    def format(self, context, text):
        exporter = context.exporter()
        self._open = []
        result = []
        pos = 0
        for match in self._rules.finditer(text):
            starting_text = exporter.escape(text[pos:match.start()])
            markup = self._markup_handler(context, match)
            result.extend((starting_text, markup))
            pos = match.end()
        final_text = exporter.escape(text[pos:])
        result.append(final_text)
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result.append(self._formatter(context, type, {}, close=True))
        return exporter.concat(*result)


class Exporter(object):
    """Transforming structured content objects to various output formats.

    This class is a base class of all exporters.  It provides basic exporting
    framework to be extended and customized for particular kinds of outputs.
    When defining a real exporter you should define the nested class
    'Formatter' and override the necessary export methods.  You may also wish
    to extend the 'Context' which is passed throughout the export process (see
    below).

    The exporting process itself is run by subsequent calls to the 'export()'
    method, passing it a context created by the 'context()' method.
    
    """

    Formatter = MarkupFormatter
    
    class Context(object):
        """Storage class containing complete data necessary for export.

        An instance of this class is passed to export methods of content
        classes.  It is possible to access all information about the current
        context (exported node, target language, etc) and also all the
        components involved in the export process (the exporter, formatter,
        generator and translator instances).

        The class is designed to be extensible.  The derived classes may accept
        additional constructor arguments to expose additional context
        information to the export process (for example the current request may
        be passed through the context in the on-line web environment).  The
        method '_init_kwargs()' may be overriden to process these specific
        arguments without the need to override the default constructor.
        
        To use an extended context class, just define it as the 'Context'
        attribute of the derived 'Exporter' class (it is a nested class).

        """
        def __init__(self, exporter, formatter, node, lang, **kwargs):
            """Initialize the export context.

            Arguments:
            
              exporter -- 'Exporter' instance to which this context belongs.
              formatter -- The exporter's 'Formatter' instance.
              node -- 'ContentNode' instance to be exported.
              lang -- Target language as an ISO 639-1 Alpha-2 lowercase
                language code or None.  If None, the export will be language
                neutral (no information about the content language will be
                present in the output and no translation will be performed).

            The constructor should not be called directly.  Use the method
            'context()' instead.
            
            """
            self._exporter = exporter
            self._formatter = formatter
            self._node = node
            self._lang = lang
            self._translator = exporter.translator(lang)
            self._init_kwargs(**kwargs)

        def _init_kwargs(self, sec_lang=None):
            self._sec_lang = sec_lang
            
        def exporter(self):
            return self._exporter
        
        def formatter(self):
            return self._formatter
        
        def lang(self):
            return self._lang

        def sec_lang(self):
            return self._sec_lang
    
        def node(self):
            return self._node
            
        def locale_data(self):
            return self._translator.locale_data()

        def translate(self, text):
            return self._translator.translate(text)

        def resource(self, filename, **kwargs):
            return self._node.resource(filename, **kwargs)
        
        def uri(self, target, **kwargs):
            return self._exporter.uri(self, target, **kwargs)
            
    def __init__(self, translations=()):
        self._formatter = self.Formatter()
        self._translations = translations
        self._translators = {}
        self._export_method = self._define_export_methods()

    def _translator(self, lang):
        return GettextTranslator(lang, path=self._translations, fallback=True)

    def _uri_node(self, context, node, lang=None):
        return node.id()

    def _uri_section(self, context, section, local=False):
        result = "#" + section.anchor()
        if not local:
            result = self._uri_node(context, section.parent()) + result
        return result

    def _resource_uri_prefix(self, context, resource):
        return None

    def _uri_resource(self, context, resource):
        if resource.uri() is not None:
            result = resource.uri()
        else:
            prefix = self._resource_uri_prefix(context, resource)
            if prefix is not None:
                path = [prefix]
            else:
                path = []
            if resource.SUBDIR:
                path.append(resource.SUBDIR)
            path.append(resource.filename())
            result = '/'.join(path)
        return result
    
    def _uri_external(self, context, target):
        return target.uri()
    
    def _define_export_methods(self):
        return {Content: self._export_content,
                HorizontalSeparator: self._export_horizontal_separator,
                NewPage: self._export_new_page,
                PageNumber: self._export_page_number,
                Title: self._export_title,
                HSpace: self._export_hspace,
                VSpace: self._export_vspace,
                TextContent: self._export_text_content,
                FormattedText: self._export_formatted_text,
                PreformattedText: self._export_preformatted_text,
                Anchor: self._export_anchor,
                Container: self._export_container,
                Paragraph: self._export_paragraph,
                Link: self._export_link,
                Section: self._export_section, 
                ContentVariants: self._export_content_variants,
                TableOfContents: self._export_table_of_contents,
                ItemizedList: self._export_itemized_list,
                DefinitionList: self._export_definition_list,
                FieldSet: self._export_field_set,
                Table: self._export_table,
                TableRow: self._export_table_row,
                TableCell: self._export_table_cell,
                TableHeading: self._export_table_heading,
                InlineImage: self._export_inline_image,
                InlineAudio: self._export_inline_audio,
                InlineVideo: self._export_inline_video,
                InlineExternalVideo: self._export_inline_external_video,
                }
    
    def _export(self, node, context):
        return node.content().export(context)

    def uri(self, context, target, **kwargs):
        """Return the URI of the target as string.

        Arguments:

          context -- exporting object created in the 'context' method and
            propagated from the 'export' method
          target -- URI target that can be one of: 'ContentNode', 'Section',
            'Link.ExternalTarget' or 'Resource' instance

        """
        if isinstance(target, ContentNode):
            method = self._uri_node
        elif isinstance(target, Section):
            method = self._uri_section
        elif isinstance(target, Resource):
            method = self._uri_resource
        elif isinstance(target, Link.ExternalTarget):
            method = self._uri_external
        else:
            raise Exception("Invalid URI target:", target)
        return method(context, target, **kwargs)

    def translator(self, lang):
        """Return a translator instance for given language.

        Translator instances are reused, so you may get the same instance for
        two subsequent calls with the same language.
        
        """
        if lang is None:
            translator = NullTranslator()
        else:
            try:
                translator = self._translators[lang]
            except KeyError:
                translator = self._translators[lang] = self._translator(lang)
        return translator

    def context(self, node, lang, **kwargs):
        """Return the export context instance to be used as an argument to the 'export' method.

        All arguments are passed to the 'Context' constructor.  See its
        documentation for more details.

        Returns an instance of 'self.Context' class, thus if the derived
        exporter class overrides the definition of its 'Context' class, the
        instance of this overriden class is returned.  This is also the
        recommended approach for extending the exporter context with specific
        context information (see 'Exporter.Context' documentation for more
        information).

        """
        return self.Context(self, self._formatter, node, lang, **kwargs)

    def export_element(self, context, element_type, element):
        """Export the given content element and return its output representation.

        Arguments:

          context -- export context object created by the 'context()' method and
            propagated from the 'export()' method.  Instance of 'self.Context'.
          element_type -- content element class (derived from 'Content')
            determining how the content element will be treated.  Most often
            this is the class of the 'element' instance, but a different class
            may be passed (usually one of 'element's superclasses) to force
            specific behavior.  In any case, the class must be compatible with
            the 'element' instance's class (have the same public methods) and
            must be supported by the exporter.  If the exporter doesn't
            recognize the class, 'UnsupportedElementType' exception is raised.
          element -- 'Content' instance to be exported.

        The supported element types are defined by the method
        '_define_export_methods()'.

        """
        try:
            method = self._export_method[element_type]
        except KeyError:
            raise UnsupportedElementType(element_type)
        return method(context, element)

    def export(self, context):
        """Export the node represented by 'context' and return the corresponding output string.

        'context' is the exporter 'Context' instance as returned by the
        'context()' method.  The context holds the actual 'ContentNode'
        instance to be exported.

        """
        return self._export(context.node(), context)

    # Basic utilitites

    def escape(self, text):
        """Escape 'text' for the output format and return the resulting string.

        In this class the method returns value of 'text'.
        
        """
        return text

    def concat(self, *items):
        """Return elements of 'exported' objects sequence as a general block.

        In this class the method performs simply text concatenation of
        'exported' objects.

        """
        return concat(*items)

    # Inline constructs (text styles).

    def emphasize(self, context, text):
        """Return exported 'text' emphasized.

        In this class the method returns value of 'text'.
        
        """
        return text

    def strong(self, context, text):
        """Return exported 'text' in a bold face.

        In this class the method returns value of 'text'.
        
        """
        return text

    def fixed(self, context, text):
        """Return exported 'text' in a fixed width font.

        In this class the method returns value of 'text'.
        
        """
        return text
     
    def underline(self, context, text):
        """Return exported 'text' underlined.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def superscript(self, context, text):
        """Return exported 'text' as a superscript.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def subscript(self, context, text):
        """Return exported 'text' as a subscript.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def citation(self, context, text):
        """Return exported 'text' as ???.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def quotation(self, context, text):
        """Return exported 'text' as ???.

        In this class the method returns value of 'text'.
        
        """
        return text

    # Content element export methods (defined by _define_export_methods).

    def _export_content(self, context, element):
        """Export the base 'Content' element.

        This element actually doesn't hold any content, so the method just
        returns escaped empty string.  It should not be necessary to override
        this method in derived classes.

        """
        return self.escape('')

    def _export_horizontal_separator(self, context, element):
        """Export the given 'HorizontalSeparator' element.

        In this class the method just returns a form feed characted.
        
        """
        return '\f'

    def _export_text_content(self, context, element):
        """Export the given 'TextContent' element.

        In this class the method just returns the escaped element text.  It
        should not be necessary to override this method in derived classes.
        
        """
        return self.escape(element.text())

    def _export_formatted_text(self, context, element):
        """Export the given 'FormattedText' element.

        This method uses the 'Exporter.Formatter' instance to export the
        element's text.  If a derived class implements the Formatter correctly,
        there should be no need to override this method.
        
        """
        text = element.text()
        if text:
            # Since formatting will destroy the translatable instances,
            # translate them before formatting.
            result = self._formatter.format(context, context.translate(text))
        else:
            result = self.escape('')
        return result
        
    def _export_anchor(self, context, element):
        """Export the given 'Anchor' element.

        In this class the method just returns the escaped anchor text.
        
        """
        return self._export_text_content(context, element)
    
    def _export_new_page(self, context):
        """Export the given 'NewPage' element.

        In this class the method just returns the page break character.
        
        """
        return '\n'

    def _export_horizontal_separator(self, context):
        """Export the given 'HorizontalSeparator' element.

        In this class the method just returns a form feed character.

        """
        return '\f'

    def _export_page_number(self, context, element):
        """Export the given 'PageNumber' element.

        In this class this method returns an escaped empty text.

        """
        return self.escape('')

    def _export_hspace(self, context, element):
        """Export the given 'HSpace' element.

        In this class this method returns an escaped empty text.
          
        """
        return self.escape('')

    def _export_vspace(self, context, element):
        """Export the given 'VSpace' element.

        In this class this method returns an escaped empty text.
          
        """
        return self.escape('')

    def _export_title(self, context, element):
        """Export the given 'Title' element.

        This method returns the escaped title of the requested content node.  There should be no
        need to override this method in derived classes.

        """
        id = element.id()
        parent = element.parent()
        if id is None:
            item = parent
        else:
            item = parent.find_section(id, context)
            if not item:
                item = parent.root().find_node(id)
        if item:
            title = item.title()
        else:
            title = id
        return self.escape(title)

    def _export_preformatted_text(self, context, element):
        """Export verbatim text of given 'PreformattedText' element.

        In this class the method returns just the escaped element text.
        
        """
        return self.escape(element.text())

    # Container elements
    
    def _export_container(self, context, element):
        """Export given 'Container' element.

        In this class the method exports the contained content elements and concatenates them.
        
        """
        return self.concat(*[content.export(context) for content in element.content()])

    def _export_link(self, context, element):
        """Export given 'Link' element.

        In this class the method just returns the exported inner content (link label).
        
        """
        return self._export_container(context, element)

    def _export_section(self, context, element):
        """Export given 'Section' element.

        In this class the method returns section title and contents separated by empty
        lines.
        
        """
        return '\n' + element.title() + '\n\n' + self._export_container(context, element) + '\n'

    def _export_content_variants(self, context, element):
        """Export the proper language variant of 'ContentVariants' element.

        Returns the exported content for language determined by
        'context.lang()'.  There should be no need to override this method in
        derived classes.

        """
        return element.variant(context.lang()).export(context)
 
    def _export_itemized_list(self, context, element):
        """Export given 'ItemizedList' element.

        In this class the method returns just a concatenation of list items.

        """
        return self._export_container(context, element)

    def _export_definition_list(self, context, element):
        """Export given 'DefinitionList' element.

        In this class the method returns just a simple concatenation of
        definition terms and their descriptions.

        """
        return self.concat(*[self.concat(dt.export(context), dd.export(context), '\n')
                             for dt, dd in element.content()])

    def _export_field_set(self, context, element):
        """Export given 'FieldSet' element.

        In this class the method returns a simple concatenation of fieldset's
        name/value pairs.
        
        """
        return self._export_definition_list(context, element)
            
    def _export_paragraph(self, context, element):
        """Export given 'Paragraph' element.

        In this class the method returns the exported paragraph content with an
        empty line appended (two new line characters).
        
        """
        return self.concat(self._export_container(context, element), '\n\n')

    def _export_table_of_contents(self, context, element):
        """Generate a Table of Contents for given 'TableOfContents' element.

        In this class the method just returns an empty content.

        """
        return self.escape('')

    # Tables

    def _export_table(self, context, element):
        """Export given 'Table' element.

        In this class the method returns just the exported table content.

        """
        return content

    def _export_table_row(self, context, element):
        """Export given 'TableRow' element.
        
        In this class the method returns just the exported row content.

        """
        return self._export_container(context, element)
        
    def _export_table_cell(self, context, element):
        """Export given 'TableCell' element.
        
        In this class the method returns just the exported cell content.

        """
        return self._export_container(context, element)

    def _export_table_heading(self, context, element):
        """Export given 'TableHeading' element.
        
        In this class the method returns the result of '_export_table_cell()'.

        """
        return self._export_table_cell(context, element)

    # Media (represented by resources wrapped in inline content elements)

    def _export_inline_image(self, context, element):
        """Export embedded image for given 'InlineImage' element.
        
        In this class the method returns just the escaped image title.
        
        """
        return self.escape(element.title() or element.image().title() or element.image().filename())

    def _export_inline_audio(self, context, element):
        """Export embedded audio player for given 'InlineAudio' element.

        In this class the method returns just the escaped audio title.

        """
        return self.escape(element.title() or element.audio().title() or element.audio().filename())

    def _export_inline_video(self, context, element):
        """Export embedded video player for given 'InlineVideo' element.

        In this class the method returns just the escaped video title.

        """
        return self.escape(element.title() or element.video().title() or element.video().filename())

    def _export_inline_external_video(self, context, element):
        """Export embedded video player for given 'InlineExternalVideo' element.

        In this class the method returns just the escaped video title.
        
        """
        return self.escape(element.title() or "Embedded Video %s id=%s" % (element.service(), element.id()))
    
        
class FileExporter(object):
    """Mix-in class exporting content into files.

    This class defines the 'dump()' method for writing the result of the export
    into filesystem.  See its documentation for more information.

    """

    _OUTPUT_FILE_EXT = None

    def __init__(self, force_lang_ext=False, **kwargs):
        super(FileExporter, self).__init__(**kwargs)
        self._force_lang_ext = force_lang_ext

    def _write_file(self, filename, content):
        directory = os.path.split(filename)[0]
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        if isinstance(content, unicode):
            content = content.encode('utf-8')
        file = open(filename, 'w')
        try:
            file.write(content)
        finally:
            file.close()

    def _filename(self, node, context, lang=None):
        """Return the pathname of node's output file relative to the output directory."""
        name = node.id().replace(':', '-')
        if lang is None:
            lang = context.lang()
        if lang is not None and ((len(node.variants()) > 1) or (self._force_lang_ext)):
            name += '.'+ lang
        return name +'.'+ self._OUTPUT_FILE_EXT
    
    def _export_resource(self, resource, dir):
        infile = resource.src_file()
        outfile = os.path.join(dir, resource.SUBDIR, resource.filename())
        if infile is None:
            data = resource.get()
            if data is not None:
                created = not os.path.exists(outfile)
                self._write_file(outfile, data)
                if created:
                    log("%s: file created.", outfile)
        elif not os.path.exists(outfile) or \
                 os.path.exists(infile) and os.path.getmtime(outfile) < os.path.getmtime(infile):
            if not os.path.isdir(os.path.dirname(outfile)):
                os.makedirs(os.path.dirname(outfile))
            input_format = os.path.splitext(infile)[1].lower()[1:]
            output_format = os.path.splitext(outfile)[1].lower()[1:]
            if input_format == output_format:
                shutil.copyfile(infile, outfile)
                log("%s: file copied.", outfile)
            else:
                if input_format != 'wav':
                    raise Exception("Unsupported conversion: %s -> %s" % (input_format, output_format))
                var = 'LCG_%s_COMMAND' % output_format.upper()
                def cmd_err(msg):
                    info = "Specify a command encoding %s file '%%infile' to %s file '%%outfile'."
                    raise Exception(msg % var +"\n"+ info % (input_format, output_format))
                try:
                    cmd = os.environ[var]
                except KeyError:
                    cmd_err("Environment variable %s not set.")
                if cmd.find("%infile") == -1 or cmd.find("%outfile") == -1:
                    cmd_err("Environment variable %s must refer to '%%infile' and '%%outfile'.")
                log("%s: converting to %s: %s", outfile, output_format, cmd)
                command = cmd.replace('%infile', infile).replace('%outfile', outfile)
                if os.system(command):
                    raise IOError("Subprocess returned a non-zero exit status.")
        
    
    def dump(self, node, directory, filename=None, variant=None, **kwargs):
        """Write node's content into the output file.

        Arguments:

           node -- the 'ContentNode' instance to dump.
           directory -- name of the destination directory as a string.
           filename -- the name of the output file as a string.  If None, the
             name will be determined automatically based on the node id and
             corresponding language and file type suffix.
           variant -- the language variant to write.  The value must be the ISO
             language code corresponding to one of the node's available
             language variants.  If None, all available variants will be
             written.

        All other keyword arguments will be passed to the exporter context
        constructor (See the .

        """
        variants = variant and (variant,) or node.variants() or (None,)
        for lang in variants:
            context = self.context(node, lang, **kwargs)
            data = context.translate(self.export(context))
            if filename:
                fn = filename
            else:
                fn = self._filename(node, context)
            self._write_file(os.path.join(directory, fn), data)


class UnsupportedElementType(Exception):
    def __init__(self, element_type):
        msg = "Element type not supported by the exporter: %s" % element_type
        return super(UnsupportedElementType, self).__init__(msg)
