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

"""Framework for exporting structured content into output formats.

The framework consists of the following parts:

  'Generator' :: 

  'MarkupFormatter' :: 

  'Exporter' :: This is the top exporting class that exports structured text
    into the output format.

See documentation of the particular classes for more details.

"""

from lcg import *
import shutil

        
class Generator(object):

    # Basic utilitites

    def escape(self, text):
        """Escape 'text' for the output format and return the resulting string.

        In this class the method returns value of 'text'.
        
        """
        return text

    def concat(self, *exported):
        """Return elements of 'exported' objects sequence as a general block.

        In this class the method performs simply text concatenation of
        'exported' objects.

        """
        return concat(*exported)
    
    # Text styles

    def pre(self, text):
        """Return 'text' in a verbatim form.

        In this class the method returns value of 'text'.
        
        """
        return text

    def emphasize(self, text):
        """Return exported 'text' emphasized.

        In this class the method returns value of 'text'.
        
        """
        return text

    def strong(self, text):
        """Return exported 'text' in a bold face.

        In this class the method returns value of 'text'.
        
        """
        return text

    def fixed(self, text):
        """Return exported 'text' in a fixed width font.

        In this class the method returns value of 'text'.
        
        """
        return text
     
    def sup(self, text):
        """Return exported 'text' as a superscript.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def sub(self, text):
        """Return exported 'text' as a subscript.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def underline(self, text):
        """Return exported 'text' underlined.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def citation(self, text):
        """Return exported 'text' as ???.

        In this class the method returns value of 'text'.
        
        """
        return text
    
    def quotation(self, text):
        """Return exported 'text' as ???.

        In this class the method returns value of 'text'.
        
        """
        return text

    # Sectioning

    def heading(self, title, level, anchor=None, backref=None):
        """Return heading.

        Arguments:

          title -- exported title of the heading
          level -- level of the heading as a positive integer; the highest
            level is 1
          anchor -- link target identifier of the heading (allows links to
            point to this heading as to an anchor).
            
          backref -- anchor name of the nearest item in a table of contents
            pointing to this heading.  This heading should become a link
            pointing to this anchor to support section title back-references
            within the document.  May be ignored in output formats where
            back-referencing is not desirable.

        In this class the method returns value of 'title' separated by empty
        lines.
        
        """
        return '\n' + title + '\n\n'
    
    def list(self, items, ordered=False, style=None, lang=None):
        """Return list of 'items'.

        Arguments:

          items -- sequence of previously exported objects
          ordered, style -- list item markup style; if 'ordered' is true,
            markup for ordered list should be chosen, then 'style' can further
            specify the style, its valid values are 'None' and the string
            'lower-alpha'
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code
        
        In this class method returns concatenation of 'items' elements
        surrounded by new lines.

        """
        items_nl = []
        for i in items:
            items_nl += [i, '\n']
        return self.concat(items_nl)

    def definitions(self, items, lang=None):
        """Return a list of definitions.

        Arguments:

          items -- sequence of '(TERM, DESCRIPTION)' pairs as tuples of
            previously exported objects
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method calls 'fset' on 'items'.
        
        """
        return self.fset(items, lang=lang)

    def fset(self, items, lang=None):
        """Return a list of label/value pairs.

        Arguments:

          items -- sequence of (LABEL, VALUE) pairs as tuples of previously exported
            objects
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns a concatenation of 'items' elements.
        
        """
        exported_items = [self.concat(dt, dd, '\n') for dt, dd in items]
        return self.concat(*exported_items)
            
    def p(self, content, lang=None):
        """Return a single paragraph of exported 'content'.

        Arguments:

          content -- already exported content
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns 'content' surrounded by new line
        characters.
        
        """
        return self.concat(content, '\n\n')

    def div(self, content, lang=None, **kwargs):
        """Return exported 'content' as a general block.

        Arguments:

          content -- already exported content
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns 'content' surrounded by new lines.

        """
        return content + '\n'

    def br(self):
        """Return a newline separator.

        In this class the method returns a new line character.
        
        """
        return '\n'

    def hr(self):
        """Return a horizontal separator.

        In this class the method returns a form feed character.

        """
        return '\f'

    # Links and images
    
    def link(self, label, uri, **kwargs):
        """Return link with 'label' and pointing to 'uri'.

        Arguments:

          label -- exported content of the link
          uri -- the target URI as a string

        In this class the method returns a text created from 'label' and 'uri'.
        
        """
        if label:
            result = self.concat(label, self.escape('(%s)' % (uri,)))
        else:
            result = uri
        return result

    def anchor(self, label, name, **kwargs):
        """Return an anchor (link target) named 'name' and containing 'label' text.

        Arguments:

          label -- exported content to be put into the place of the link target
          name -- name of the link target as a string

        In this class the method returns a text created from 'label' and
        'name'.
          
        """
        return self.escape('%s#%s' % (label, name,))

    def img(self, src, alt=None, descr=None, align=None, width=None, height=None, **kwargs):
        """Return image stored at 'src' URI.

        Arguments:

          src -- URI (as a string) where the image is stored
          alt -- title of the image as a string or unicode or 'None'
          descr -- ???
          align -- requested alignment of the image, 'None' or one of the
            strings 'left' or 'right'
          width -- ???
          height -- ???

        In this class the method returns text of 'src'.

        """
        return self.escape(src)

    def toc(self, item, depth=1):
        """Generate a Table of Contents for given content 'item' limited to given 'depth'.

        Arguments:
           item -- An instance of 'ContentNode'

        """
        #TODO: Generalize the implementation from content.py.

    # Tables

    def th(self, content, lang=None):
        """A table heading container wrapping previously exported heading content.
        
        Arguments:

          content -- previously exported heading content
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns the 'content' unchanged.

        """
        return content

    def td(self, content, align=None, lang=None):
        """A table cell container wrapping previously exported cell content.
        
        Arguments:

          content -- previously exported cell content
          align -- requested cell content alignment, 'None' or one of the
            strings 'left', 'right', 'center'.
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns the 'content' unchanged.

        """
        return content

    def tr(self, content, lang=None):
        """A table row container wrapping previously exported table cells.
        
        Arguments:

          content -- previously exported row content
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns the 'content' unchanged.

        """
        return content
        
    def table(self, content, title=None, cls=None, lang=None):
        """A table container wrapping previously exported table rows.

        Arguments:

          content -- previously exported table content
          title -- 'None' or table caption as a string or unicode
          cls -- table presentation class identifier as a string
          lang -- 'None' or content language as an ISO 639-1 Alpha-2 lowercase
            language code

        In this class the method returns the 'content' unchanged.

        """
        return content


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
        g = context.generator()
        type = [key for key, m in match.groupdict().items()
                if m and not key in self._HELPER_PATTERNS][0]
        markup = match.group(type)
        backslashes = markup.count('\\')
        markup = g.escape(markup[backslashes:])
        prefix = g.escape(backslashes / 2 * '\\')
        if backslashes % 2:
            return g.concat(prefix, markup)
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
        return g.concat(prefix, result)

    def _substitution_formatter(self, context, subst, **kwargs):
        g = context.generator()
        # get the substitution value for _SUBSTITUTION_REGEX match
        if subst.startswith('{') and subst.endswith('}'):
            text = subst[1:-1]
        else:
            text = subst
        if not text:
            return g.escape('$' + subst)
        result = context.node().globals()
        for name in text.split('.'):
            try:
                result = result[str(name)]
            except KeyError:
                return g.escape('$' + subst)
        if not isinstance(result, Localizable):
            result = str(result)
        return g.escape(result)
    
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
        g = context.generator()
        self._open = []
        result = []
        pos = 0
        for match in self._rules.finditer(text):
            starting_text = g.escape(text[pos:match.start()])
            markup = self._markup_handler(context, match)
            result.extend((starting_text, markup))
            pos = match.end()
        final_text = g.escape(text[pos:])
        result.append(final_text)
        self._open.reverse()
        x = self._open[:]
        for type in x:
            result.append(self._formatter(context, type, {}, close=True))
        return g.concat(*result)


class Exporter(object):
    """Transforming structured content objects to various output formats.

    This class is a base class of all transformers.  It provides basic exporting framework to be
    extended and customized for particular kinds of outputs.  When defining a real exporter you
    should assign the 'Generator' and 'Formatter' attributes to corresponding utility classes.  The
    exporter instantiates and uses them as needed.  You may also wish to extend the 'Context' which
    is passed throughout the export process (see below).

    The exporting process itself is run by subsequent calls of the 'export()' method, passing it a
    context created by the 'context()' method.
    
    """

    Generator = Generator
    Formatter = MarkupFormatter
    
    class Context(object):
        """Storage class containing complete data necessary for export.

        An instance of this class is passed to export methods of content classes.  It is possible
        to access all information about the current context (exported node, target language, etc)
        and also all the components involved in the export process (the exporter, formatter,
        generator and translator instances).

        The class is designed to be extensible.  The derived classes may accept additional
        constructor arguments to expose additional context information to the export process (for
        example the current request may be passed through the context in the on-line web
        environment).  The method '_init_kwargs()' may be overriden to process these specific
        arguments without the need to override the default constructor.
        
        To use an extended context class, just define it as the 'Context' attribute of the derived
        'Exporter' class.

        """
        def __init__(self, exporter, generator, formatter, node, lang, **kwargs):
            """Initialize the export context.

            Arguments:
            
              exporter -- 'Exporter' instance to which this context belongs.
              generator --  The exporter's 'Generator' instance.
              formatter -- The exporter's 'Formatter' instance.
              node -- 'ContentNode' instance to be exported.
              lang -- Target language as an ISO 639-1 Alpha-2 lowercase language code or None.  If
                None, the export will be language neutral (no information about the content
                language will be present in the output and no translation will be performed).

            

            The constructor should not be called directly.  Use the metohd 'context()' instead.
            
            """
            self._exporter = exporter
            self._generator = generator
            self._formatter = formatter
            self._node = node
            self._lang = lang
            self._translator = exporter.translator(lang)
            self._init_kwargs(**kwargs)

        def _init_kwargs(self, sec_lang=None):
            self._sec_lang = sec_lang
            
        def exporter(self):
            return self._exporter
        
        def generator(self):
            return self._generator
        
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
        self._generator = self.Generator()
        self._formatter = self.Formatter()
        self._translations = translations
        self._translators = {}

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
    
    def uri(self, context, target, **kwargs):
        """Return the URI of the target as string.

        Arguments:

          context -- exporting object created in the 'context' method and
            propagated from the 'export' method
          target -- URI target that can be one of: 'ContentNode', 'Section', 'Link.ExternalTarget'
            or 'Resource' instance

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

    def _translator(self, lang):
        return GettextTranslator(lang, path=self._translations, fallback=True)

    def translator(self, lang):
        """Return a translator instance for given language.

        Translator instances are reused, so you may get the same instance for two subsequent calls
        with the same language.
        
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

        All arguments are passed to the 'Context' constructor.  See its documentation for more
        details.

        Returns an instance of 'self.Context' class, thus if the derived exporter class overrides
        the definition of its 'Context' class, the instance of this overriden class is returned.
        This is also the recommended approach for extending the exporter context with specific
        context information (see 'Exporter.Context' documentation for more information).

        """
        return self.Context(self, self._generator, self._formatter, node, lang, **kwargs)

    def _initialize(self, context):
        generator = context.generator()
        title = generator.escape(context.node().title())
        content = generator.heading(title, 1)
        return content

    def _finalize(self, context):
        return ''

    def _export(self, node, context):
        return node.content().export(context)
        
    def export(self, context):
        """Export the node represented by 'context' and return the corresponding output string.

        'context' is the exporter 'Context' instance as returned by the 'context()' method.  The
        context holds the actual 'ContentNode' instance to be exported.

        """
        node = context.node()
        initial_export = self._initialize(context)
        export = self._export(node, context)
        final_export = self._finalize(context)
        generator = context.generator()
        result = export
        if initial_export is not None:
            result = generator.concat(initial_export, result)
        if final_export is not None:
            result = generator.concat(result, final_export)
        return result

    def export_inline_audio(self, context, audio, title=None, descr=None, image=None, shared=True):
        """Export embedded audio player for given 'Audio' resource instance.

        Arguments:

          context -- current exporter context as 'Exporter.Context' instance
          audio -- 'Audio' resource instance or an absolute URI (as a string)
          title -- audio file title as a string.
          descr -- audio file description as a string.
          image -- visual presentation image as an 'Image' resource instance or None.
          shared -- True if using a shared audio player is desired, False otherwise

        In this class the method returns the audio title as a string.
        Derived classes implement a more appropriate behavior relevant for
        given output media.

        """
        return self.escape(title or audio.title() or audio.filename())

    def export_inline_video(self, context, video, title=None, descr=None, image=None, size=None):
        """Export embedded video player for given 'Video' resource instance.

        Arguments:

          context -- current exporter context as 'Exporter.Context' instance
          video -- 'Video' resource instance or an absolute URI (as a string)
          title -- video file title as a string.
          descr -- video file description as a string.
          image -- video thumbnail image as an 'Image' resource instance or None.
          size -- video size in pixels as a sequence of two integers (WIDTH, HEIGHT)

        In this class the method returns the video file title as a string.
        Derived classes implement a more appropriate behavior relevant for
        given output media.

        """
        return self.escape(title or video.title() or video.filename())


class FileExporter(object):
    """Mix-in class exporting content into files.

    This class defines the 'dump()' method for writing the result of the export into filesystem.
    See its documentation for more information.

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
           filename -- the name of the output file as a string.  If None, the name will be
             determined automatically based on the node id and corresponding language and file type
             suffix.
           variant -- the language variant to write.  The value must be the ISO language code
             corresponding to one of the node's available language variants.  If None, all
             available variants will be written.

        All other keyword arguments will be passed to the exporter context constructor (See the .

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

