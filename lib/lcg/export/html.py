# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2012 Brailcom, o.p.s.
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

from lcg import *
from lcg.export import *

from xml.sax import saxutils
import random

_ = TranslatableTextFactory('lcg')

class HtmlGenerator(object):

    _DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
    #_DOCTYPE = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'

    def _attribute(self, name, value):
        if value is True:
            return name
        else:
            if isinstance(value, int):
                value = '"%d"' % value
            elif isinstance(value, Localizable):
                value = value.transform(saxutils.quoteattr)
            else:
                value = saxutils.quoteattr(value)
            return name + '=' + value
    
    def _attributes(self, valid, **kwargs):
        result = ''
        for name in valid + ('id', 'lang', 'tabindex', 'cls', 'style'):
            if kwargs:
                value = kwargs.pop(name, None)
                if not (value is None or value is False):
                    if name == 'cls':
                        name = 'class'
                    result += ' ' + self._attribute(name, value)
            else:
                break
        assert not kwargs, "Invalid attributes: %s" % kwargs
        return result

    def _tag(self, tag, content=None, _attr=(), _newlines=False, _paired=True, **kwargs):
        separator = _newlines and "\n" or ""
        attributes = self._attributes(_attr, **kwargs)
        if not _paired:
            assert content is None
            return '<' + tag + attributes + '/>' + separator
        else:
            assert content is not None
            if isinstance(content, (tuple, list)):
                content = concat(content, separator=separator)
            if _newlines and not content.endswith(separator):
                content += separator
            return concat('<', tag, attributes, '>', separator, content, '</', tag, '>', separator)
     
    def _input(self, type, _attr=(), **kwargs):
        attr = ('type', 'name', 'value', 'title', 'size', 'maxlength', 'accesskey',
                'onclick', 'onmousedown', 'onmouseup', 'onkeydown', 'onkeypress', 'onchange',
                'readonly', 'disabled')
        return self._tag('input', _attr=attr+_attr, _paired=False, type=type, **kwargs)
    
    def uri(self, base, *args, **kwargs):
        uri = urllib.quote(base.encode('utf-8'))
        query = ';'.join([k +'='+ urllib.quote(unicode(v).encode('utf-8'))
                          for k,v in args + tuple(kwargs.items()) if v is not None])
        if query:
            uri += '?' + query
        return uri

    def escape(self, text):
        return saxutils.escape(text)

    def concat(self, *items):
        return concat(*items)

    # HTML tags

    def html(self, content, **kwargs):
        return self._tag('html', content, ('xmlns',), _newlines=True, **kwargs)
    
    def head(self, content):
        content = concat('  ', concat(content, separator='\n  ')),
        return self._tag('head', content, _newlines=True)
    
    def body(self, content, **kwargs):
        return self._tag('body', content, ('onkeydown', 'onload'), _newlines=True, **kwargs)
    
    def div(self, content, **kwargs):
        return self._tag('div', content, ('title',), _newlines=True, **kwargs)
     
    def span(self, text, **kwargs):
        return self._tag('span', text, ('title',), **kwargs)
     
    def h(self, title, level, **kwargs):
        return self._tag('h%d' % level, title, **kwargs)
    
    def map(self, content, **kwargs):
        return self._tag('map', content, ('name', 'title'), _newlines=True, **kwargs)

    def strong(self, text, **kwargs):
        return self._tag('strong', text, **kwargs)
     
    def em(self, text, **kwargs):
        return self._tag('em', text, **kwargs)
    
    def u(self, text, **kwargs):
        return self._tag('u', text, **kwargs)
    
    def code(self, text, **kwargs):
        return self._tag('code', text, **kwargs)
    
    def pre(self, text, cls="lcg-preformatted-text", **kwargs):
        return self._tag('pre', text, _newlines=True, cls=cls, **kwargs)
     
    def sup(self, text, **kwargs):
        return self._tag('sup', text, **kwargs)
    
    def sub(self, text, **kwargs):
        return self._tag('sub', text, **kwargs)
    
    def p(self, *content, **kwargs):
        if content[0].find('object') != -1:
            # This is a nasty hack to suppress <p>...</p> around a video player.  In any case,
            # wrapping a block-level element in another block level element is invalid HTML, so
            # this should never be wrong to omit the paragraph.
            if content and content[0].strip().startswith('<div') \
                   and content[-1].strip().endswith('</div>'):
                return concat(content, separator='\n')
        return self._tag('p', content, **kwargs)
     
    def blockquote(self, content, **kwargs):
        return self._tag('blockquote', content, **kwargs)
    
    def footer(self, content, **kwargs):
        return self._tag('footer', content, **kwargs)
    
    def br(self, **kwargs):
        return self._tag('br', _paired=False, **kwargs)
     
    def hr(self, **kwargs):
        return self._tag('hr', _paired=False, **kwargs)

    def a(self, label, **kwargs):
        attr = ('href', 'type', 'name', 'title', 'target', 'accesskey', 'rel', 'onclick')
        return self._tag('a', label, attr, **kwargs)

    def link(self, label, uri, title=None, target=None, hotkey=None, cls=None, **kwargs):
        """Deprecated!  Just for backwards compatibility."""
        if hotkey and title:
            title += ' (%s)' % hotkey
        if target:
            cls = (cls and cls+' ' or '') + 'external-link'
        return self.a(label, href=uri, title=title, target=target, accesskey=hotkey, cls=cls,
                      **kwargs)

    def ol(self, *content, **kwargs):
        return self._tag('ol', content, **kwargs)
    
    def ul(self, *content, **kwargs):
        return self._tag('ul', content, **kwargs)
    
    def li(self, content, **kwargs):
        return self._tag('li', content, **kwargs)
    
    def list(self, items, indent=0, ordered=False, style=None, **kwargs):
        """Deprecated!  Just for backwards compatibility."""
        spaces = ' ' * indent
        items = [concat(spaces, '  ', self.li(i), '\n') for i in items]
        tag = ordered and self.ol or self.ul
        style = style and 'list-style-type: %s' % style
        return spaces + tag(concat('\n', items, spaces), style=style, **kwargs)+'\n'
    
    def dl(self, *content, **kwargs):
        return self._tag('dl', content, _newlines=True, **kwargs)

    def dt(self, content, **kwargs):
        return self._tag('dt', content)

    def dd(self, content, **kwargs):
        return self._tag('dd', content)
    
    def img(self, src, alt='', border=0, **kwargs):
        attr = ('src', 'alt', 'longdesc', 'width', 'height', 'align', 'border')
        return self._tag('img', _attr=attr, _paired=False, src=src, alt=alt, border=border, **kwargs)

    def abbr(self, term, **kwargs):
        return self._tag('abbr', term, ('title',), **kwargs)

    def table(self, content, **kwargs):
        attr = ('title', 'summary', 'border', 'cellspacing', 'cellpadding', 'width')
        return self._tag('table', content, attr, _newlines=True, **kwargs)
    
    def tr(self, content, **kwargs):
        return self._tag('tr', content, **kwargs)

    def th(self, content, **kwargs):
        return self._tag('th', content, ('colspan', 'width', 'align', 'valign', 'scope'), **kwargs)
    
    def td(self, content, **kwargs):
        return self._tag('td', content, ('colspan', 'width', 'align', 'valign', 'scope'), **kwargs)
    
    def thead(self, content):
        return self._tag('thead', content)
    
    def tfoot(self, content):
        return self._tag('tfoot', content)
    
    def tbody(self, content):
        return self._tag('tbody', content, _newlines=True)
    
    def iframe(self, src, **kwargs):
        attr = ('src', 'width', 'height', 'frameborder')
        return self._tag('iframe', self.a(src, href=src), attr, src=src, **kwargs)
     
    def object(self, content, **kwargs):
        return self._tag('object', content, (
                'align', 'archive', 'border', 'classid', 'codebase', 'codetype',
                'data', 'declare', 'height', 'hspace', 'name', 'standby', 'type',
                'usemap', 'vspace', 'width', 'dir', 'title'), 
                         _newlines=True, **kwargs)

    def param(self, **kwargs):
        return self._tag('param', _attr=('name', 'value', 'valuetype', 'type'),
                         _paired=False, **kwargs)
 
    # Form controls (special methods for various HTML INPUT fields are defined, so the `input'
    # method itself is not needed).
     
    def form(self, content, action="#", **kwargs):
        attr = ('name', 'action', 'method', 'enctype', 'onsubmit')
        return self._tag('form', content, attr, _newlines=True, action=action, **kwargs)
     
    def fieldset(self, legend, content, **kwargs):
        content = (self._tag('legend', legend or '', cls=(not legend and 'empty' or None)),) +\
                   tuple(content)
        return self._tag('fieldset', content, _newlines=True, **kwargs)
     
    def label(self, text, id, **kwargs):
        # We don't respect the HTML attribute name since 'for' is a Python keyword.
        # Additionally we also intentionally force this atributte to be mandatory.
        kwargs['for'] = id
        return self._tag('label', text, ('for',), **kwargs)

    def field(self, value='', name='', size=20, password=False, cls=None, **kwargs):
        type = password and 'password' or 'text'
        cls = type + (cls and ' '+cls or '')
        return self._input(type, name=name, value=value, size=size, cls=cls, **kwargs)
     
    def upload(self, name, size=50, cls=None, **kwargs):
        cls = 'upload' + (cls and ' '+cls or '')
        return self._input('file', name=name, size=size, cls=cls, **kwargs)
     
    def radio(self, name, **kwargs):
        return self._input('radio', _attr=('checked',), name=name, **kwargs)
     
    def hidden(self, name, value, id=None):
        return self._input('hidden', name=name, value=value, id=id)
     
    def button(self, content, type='submit', **kwargs):
        attr = ('name', 'value', 'type', 'onclick', 'cls', 'disabled', 'title')
        return self._tag('button', content, attr, type=type, **kwargs)
     
    def reset(self, label, onclick=None, cls=None, title=None):
        return self._input('reset', title=title, onclick=onclick, value=label, cls=cls)
     
    def submit(self, label, value=None, **kwargs):
        if value is None:
            return self._input('submit', value=label, **kwargs)
        else:
            attr = ('value', 'onclick', 'name', 'cls', 'disabled', 'title')
            return self._tag('button', label, attr, value=value, **kwargs)
            
    def select(self, name, options, selected=None, **kwargs):
        found = []
        def opt(label, value, enabled=True, cls=None):
            if isinstance(value, (list, tuple)):
                return self._tag('optgroup', [opt(*x) for x in value], ('label',), label=label,
                                 _newlines=True)
            else:
                if __debug__:
                    if selected == value:
                        found.append(value)
                return self._tag('option', label, ('value', 'selected', 'disabled'),
                                 value=value, selected=(value == selected), disabled=not enabled,
                                 cls=not enabled and (cls and cls+' ' or '')+'disabled' or cls)
        opts = [opt(*x) for x in options]
        assert selected is None or found, "Value %r not found in options: %r" % (selected, options)
        # TODO: check also for duplicate `selected' values?
        attr = ('name', 'title', 'onchange', 'disabled', 'readonly')
        return self._tag('select', opts, attr, _newlines=True, name=name, **kwargs)
     
    def checkbox(self, name, **kwargs):
        return self._input('checkbox', _attr=('checked',), name=name, **kwargs)
     
    def textarea(self, name, value='', **kwargs):
        attr = ('name', 'rows', 'cols', 'disabled', 'readonly')
        return self._tag('textarea', value, attr, name=name, **kwargs)

    # HTML 5 Media tags
     
    def audio(self, src, content=None, controls=True, **kwargs):
        return self._tag('audio', content,
                         _attr=('autoplay', 'controls', 'loop', 'preload', 'title', 'src'),
                         _paired=content is not None, src=src, controls=controls, **kwargs)

    def video(self, src, content=None, controls=True, **kwargs):
        return self._tag('video', content,
                         _attr=('autoplay', 'controls', 'height', 'loop', 'muted', 'poster',
                                'preload', 'src', 'title', 'width'),
                         _paired=content is not None, src=src, controls=controls, **kwargs)

    def source(self, src, **kwargs):
        return self._tag('source', _attr=('src', 'type'), _paired=False, src=src, **kwargs)

    # JavaScript code generation.
     
    def script(self, code, noscript=None):
        return '<script type="text/javascript" language="Javascript">\n' + \
            (code and code.strip() + '\n' or '') + '</script>' + \
            (noscript and self.noscript(noscript) or '')
    
    def noscript(self, content):
        return self._tag('noscript', content)
     
    def script_write(self, content, noscript=None, condition=None):
        #return content
        #return noscript
        if content:
            c = content.replace('"','\\"').replace("'","\\'")
            c = c.replace('</', '<\\/').replace('\n','\\n')
            content = 'document.write("' + c + '");'
            if condition:
                content = 'if (' + condition + ') ' + content
        return self.script(content, noscript)
     
    def js_value(self, var):
        if var is None:
            return 'null'
        elif isinstance(var, (str, unicode)):
            return "'" + var.replace("'", "\\'").replace('</', '<\\/').replace('\n','\\n') + "'"
        elif isinstance(var, bool):
            return (var and 'true' or 'false')
        elif isinstance(var, int):
            return str(var)
        elif isinstance(var, (tuple, list)):
            return self.js_array(var)
        elif isinstance(var, dict):
            return self.js_dict(var)
        else:
            raise Exception("Invalid type for JavaScript conversion:", var)
        
    def js_array(self, items):
        assert isinstance(items, (tuple, list))
        values = [self.js_value(i) for i in items]
        return concat('[', concat(values, separator=", "), ']')
     
    def js_dict(self, items):
        if isinstance(items, dict):
            items = items.items()
        else:
            assert isinstance(items, (tuple, list))
        assert is_sequence_of(dict(items).keys(), str)
        pairs = [concat("'%s': " % k, self.js_value(v)) for k,v in items]
        return concat('{', concat(pairs, separator=", "), '}')
     
    def js_args(self, *args):
        return concat([self.js_value(arg) for arg in args], separator=", ")
     
    def js_call(self, fname, *args):
        fargs = concat([self.js_value(arg) for arg in args], separator=", ")
        return '%s(%s)' % (fname, fargs)


class XhtmlGenerator(HtmlGenerator):

    def _attribute(self, name, value):
        if value is True:
            value = 'yes'
        return super(Xhtmlgenerator, self)._attribute(name, value)

    
class HtmlExporter(Exporter):
    Generator = HtmlGenerator

    class Context(Exporter.Context):
        
        def __init__(self, *args, **kwargs):
            self._generator = kwargs['generator']
            self._shared_player_controls = []
            # We generate a random string prefix for all unique identifiers.
            # This makes the identifiers unique even if we compose a page from
            # pieces exported in different contexts, which is typical when
            # using AJAX.
            self._unique_id_prefix = (random.choice(string.ascii_lowercase) +
                                      ''.join(random.sample(string.digits + string.ascii_lowercase + '-', 11)))
            self._unique_id_index = 0
            del kwargs['generator']
            super(HtmlExporter.Context, self).__init__(*args, **kwargs)
            
        def generator(self):
            return self._generator

        def unique_id(self):
            """Return a unique id string in the curent context.
            
            The returned string may typically be used as a unique HTML element
            id.
            
            """
            self._unique_id_index += 1
            return '%s%x' % (self._unique_id_prefix, self._unique_id_index)
    
        def connect_shared_player(self, *args):
            """Connect given player controls to the shared player.

            Arguments correspond to the arguments of the JavaScript function
            'init_player_controls()' defined in 'media.js' starting with 'uri'.  At least two
            arguments ('uri' and 'button_id') should be passed.  The remaining arguments are
            optional.

            If this method is called at least once during document export, a shared media player is
            exported at the bottom of the page and passed player controls are connected to the
            player.

            """
            self._shared_player_controls.append(args)
            
        def shared_player_controls(self):
            return self._shared_player_controls
        
    _BODY_PARTS = ('heading',
                   'language_selection',
                   'content',
                   'media_player',
                   )
    _LANGUAGE_SELECTION_LABEL = _("Choose your language:")
    _LANGUAGE_SELECTION_COMBINED = False

    def __init__(self, *args, **kwargs):
        self._generator = self.Generator()
        super(HtmlExporter, self).__init__(*args, **kwargs)
    
    def _title(self, context):
        return context.node().title()

    def _meta(self, context):
        """Return the list of pairs (NAME, CONTENT) for meta tags of given context/node."""
        import lcg
        return (('generator', 'LCG %s (http://www.freebsoft.org/lcg)' % lcg.__version__),)

    def _scripts(self, context):
        """Return the list of 'Script' instances for given context/node."""
        return context.node().resources(Script)
    
    def _head(self, context):
        node = context.node()
        return [concat('<title>', self._title(context), '</title>')] + \
               ['<meta http-equiv="%s" content="%s">' % pair
                for pair in (('Content-Language', context.lang()),
                             ('Content-Script-Type', 'text/javascript'),
                             ('Content-Style-Type', 'text/css'),
                             ('X-UA-Compatible', 'edge'))] + \
               ['<meta name="%s" content="%s">' % pair for pair in self._meta(context)] + \
               ['<link rel="alternate" lang="%s" href="%s">' % \
                (lang, self._uri_node(context, node, lang=lang))
                for lang in node.variants() if lang != context.lang()] + \
               ['<link rel="gettext" type="application/x-po" href="%s"</style>' % context.uri(t)
                for t in context.node().resources(Translations)] + \
               ['<script language="Javascript" type="text/javascript"' + \
                ' src="%s"></script>' % context.uri(s) for s in self._scripts(context)]

    def _parts(self, context, parts):
        result = []
        for name in parts:
            content = self._part(name, context)
            if content is not None:
                result.append(content)
        return concat(result)
    
    def _part(self, name, context):
        content = getattr(self, '_'+name)(context)
        if content is not None:
            return self._generator.div(content, id=name.replace('_', '-'))
        else:
            return None
        
    def _heading(self, context):
        return self._generator.h(context.node().title(), level=1)

    def _language_selection(self, context):
        g = context._generator
        node = context.node()
        variants = list(node.variants())
        if len(variants) <= 1:
            return None
        variants.sort()
        links = []
        for lang in variants:
            localizer = self.localizer(lang)
            label = localizer.localize(language_name(lang) or lang)
            cls = 'lang-'+lang
            if lang == context.lang():
                cls += ' current'
                sign = g.span(' *', cls='hidden')
            else:
                sign = ''
            image = self._language_selection_image(context, lang)
            if image:
                if self._LANGUAGE_SELECTION_COMBINED:
                    label += g.img(image, border=None)
                else:
                    label = g.img(image, alt=label, border=None)
            links.append(g.a(label, href=self._uri_node(context, node, lang=lang),
                             lang=lang, cls=cls)+sign)
        return concat(g.a(self._LANGUAGE_SELECTION_LABEL,
                          id='language-selection-anchor', name='language-selection-anchor'),
                      "\n", concat(links, separator=" "+g.span('|', cls='sep')+"\n"))

    def _language_selection_image(self, context, lang):
        #return context.uri(context.resource('flags/%s.gif' % lang))
        return None
    
    def _content(self, context):
        return context.node().content().export(context)

    def _body_attr(self, context, **kwargs):
        return kwargs
    
    def _body_content(self, context):
        return self._parts(context, self._BODY_PARTS)
    
    def context(self, *args, **kwargs):
        kwargs['generator'] = self._generator
        return super(HtmlExporter, self).context(*args, **kwargs)

    # Specific methods for exporting content elements.
    
    def _export_horizontal_separator(self, context, element):
        return self._generator.hr()

    def _export_new_line(self, context, element):
        return self._generator.br()

    def _export_new_page(self, context, element):
        return self._generator.hr(cls='new-page')

    def _export_strong(self, context, element):
        return self._export_container(context, element, wrap=self._generator.strong)
    
    def _export_emphasized(self, context, element):
        return self._export_container(context, element, wrap=self._generator.em)
    
    def _export_underlined(self, context, element):
        return self._export_container(context, element, wrap=self._generator.u)
    
    def _export_code(self, context, element):
        return self._export_container(context, element, wrap=self._generator.code)

    def _export_citation(self, context, element):
        return self._export_container(context, element, wrap=self._generator.span,
                                      lang=element.lang(inherited=False) or context.sec_lang(),
                                      cls='lcg-citation')
    
    def _export_quotation(self, context, element):
        g = self._generator
        def wrap(content, cls='lcg-quotation', **kwargs):
            uri = element.uri()
            if uri:
                source = g.a(element.source(), href=uri)
            else:
                source = element.source()
            if source or uri:
                content += g.footer(u'— ' + source)
            return g.blockquote(content, cls=cls, **kwargs)
        return self._export_container(context, element, wrap=wrap)

    def _export_footer(self, context, element):
        return self._export_container(context, element, wrap=self._generator.footer)

    def _export_superscript(self, context, element):
        return self._export_container(context, element, wrap=self._generator.sup)

    def _export_subscript(self, context, element):
        return self._export_container(context, element, wrap=self._generator.sub)

    
    def _export_anchor(self, context, element):
        return self._generator.a(self._export_text_content(context, element),
                                 name=element.anchor())
    
    def _export_link(self, context, element):
        target = element.target(context)
        label = self.concat(self._exported_container_content(context, element))
        descr = element.descr()
        if not label:
            if isinstance(target, (ContentNode, Section)):
                label = target.heading().export(context)
            elif isinstance(target, Resource):
                label = target.title() or target.filename()
            elif isinstance(target, element.ExternalTarget):
                label = target.title() or target.uri()
        if descr is None:
            if isinstance(target, (ContentNode, element.ExternalTarget, Resource)):
                descr = target.descr()
            elif isinstance(target, Section) and target.parent() is not element.parent():
                descr = target.title() + ' ('+ target.parent().title() +')'
        return self._generator.a(label, href=context.uri(target), title=descr, type=element.type())

    def _container_attr(self, element, cls=None, lang=None, **kwargs):
        style = {}
        if element.halign():
            style['text-align'] = {HorizontalAlignment.RIGHT: 'right',
                                   HorizontalAlignment.LEFT: 'left',
                                   HorizontalAlignment.CENTER: 'center',
                                   HorizontalAlignment.JUSTIFY: 'justify',
                                   }[element.halign()]
        presentation = element.presentation()
        if presentation and presentation.indent_left:
            style['margin-left'] = '%dem' % element.presentation().indent_left.size()
        attr = dict(cls=' '.join([x for x in (element.name(), cls) if x is not None]) or None,
                    lang=lang or element.lang(inherited=False),
                    style=style and ' '.join(['%s: %s;' % x for x in style.items()]) or None,
                    **kwargs)
        return dict([(key, value) for key, value in attr.items() if value is not None])
    
    def _exported_container_content(self, context, element):
        return [subcontent.export(context) for subcontent in element.content()]
    
    def _export_container(self, context, element, wrap=None, **kwargs):
        result = self.concat(self._exported_container_content(context, element))
        attr = self._container_attr(element, **kwargs)
        if wrap or attr:
            if wrap is None:
                wrap = self._generator.div
            result = wrap(result, **attr)
        return result
    
    def _export_paragraph(self, context, element):
        return self._export_container(context, element, wrap=self._generator.p)

    def _export_heading(self, context, element):
        return self._export_container(context, element)

    def _export_section(self, context, element):
        g = self._generator
        level = len(element.section_path()) + 1
        anchor = element.anchor()
        backref = element.backref()
        if backref:
            href = "#" + backref
        else:
            href = None
        # Get rid of the outer Heading instance and only consider the contained content.
        heading = element.heading()
        lang = None
        if len(heading.content()) == 1 and isinstance(heading.content()[0], lcg.Container):
            # In this case, we want replace the Container created in
            # HTMLProcessor._section() and may have the lang attribute set by a
            # container with no lang (to avoid <div> tag when calling
            # heading.export()) and use the lang for the <h> tag.
            lang = heading.content()[0].lang()
            heading = lcg.Container(heading.content()[0].content())
        return g.div((g.h(g.a(heading.export(context), href=href, name=anchor, cls='backref'),
                          level, lang=lang),
                      self.concat(self._exported_container_content(context, element))),
                     id='section-' + anchor,
                     **self._container_attr(element))
    
    def _export_preformatted_text(self, context, element):
        return self._generator.pre(self.escape(element.text()))

    def _itemized_list(self, items, order=None, _indent=0):
        g = self._generator
        spaces = ' ' * _indent
        items = [concat(spaces, '  ', g.li(item, cls="i%d" % (i+1)), '\n')
                 for i, item in enumerate(items)]
        style = None
        if order is None:
            method = g.ul
        else:
            method = g.ol
            if order == 'lower-alpha':
                style = 'list-style-type: lower-alpha'
            elif order == 'upper-alpha':
                style = 'list-style-type: upper-alpha'
        return spaces + method(concat('\n', items, spaces), style=style)+'\n'
        
    def _export_itemized_list(self, context, element):
        return self._itemized_list([item.export(context) for item in element.content()],
                                   order=element.order())

    def _export_definition_list(self, context, element):
        g = self._generator
        content = [g.dt(dt.export(context)) + g.dd(dd.export(context))
                   for dt, dd in element.content()]
        return g.dl(*content)

    def _export_field_set(self, context, element):
        g = self._generator
        return g.table([g.tr((g.th(name.export(context), valign="top", align="left"),
                              g.td(value.export(context))))
                        for name, value in element.content()],
                       cls='lcg-fieldset')

    def _export_table_of_contents(self, context, element):
        g = self._generator
        parent = element.parent()
        def make_toc(items, _indent=0):
            if len(items) == 0:
                return g.escape('')
            links = []
            for item, subitems in items:
                if isinstance(item, ContentNode):
                    descr = item.descr()
                    name = None
                    uri_kwargs = {}
                else:
                    assert isinstance(item, Section)
                    descr = None
                    name = item.create_backref(parent)
                    uri_kwargs = dict(local=(parent is item.parent()))
                uri = context.uri(item, **uri_kwargs)
                link = g.a(item.heading().export(context), href=uri, name=name, title=descr)
                subtoc = make_toc(subitems, _indent=_indent+4)
                links.append(g.concat(link, subtoc))
            return concat("\n", self._itemized_list(links, _indent=_indent), ' '*(_indent-2))
        result = make_toc(element.items(context), _indent=0)
        title = element.title()
        if title is not None:
            g = self._generator
            #TODO: add a "skip" link?
            result = g.div(g.concat(g.div(g.strong(title), cls='title'), result),
                           cls='table-of-contents')
        return result
    
    def _export_table(self, context, element):
        return self._export_container(context, element, wrap=self._generator.table,
                                      cls='lcg-table', title=element.title())

    def _export_table_row(self, context, element):
        return self._export_container(context, element, wrap=self._generator.tr)

    def _export_table_cell(self, context, element):
        return self._export_container(context, element, wrap=self._generator.td,
                                      align=element.align())
    
    def _export_table_heading(self, context, element):
        return self._export_container(context, element, wrap=self._generator.th,
                                      align=element.align())

    def _export_inline_image(self, context, element):
        g = self._generator
        image = element.image(context)
        thumbnail = image.thumbnail()
        link = None
        if thumbnail:
            if True not in [isinstance(c, lcg.Link) for c in element.container_path()]:
                link = context.uri(image)
            image = thumbnail
        title = element.title()
        descr = element.descr()
        size = element.size()
        uri = context.uri(image)
        if size is None:
            size = image.size()
        if title is None:
            title = image.title()
        if descr is None:
            descr = image.descr()
        if size is not None:
            width, height = size
        else:
            width, height = None, None
        if descr:
            if title:
                title = self.concat(title, ': ', descr)
            else:
                title = descr
        if title and not link:
            alt = title
        else:
            alt = ''
        cls = ['lcg-image']
        if element.align():
            cls.append(element.align() + '-aligned')
        if element.name():
            cls.append('image-'+element.name())
        img = g.img(uri, alt=alt, align=element.align(), cls=' '.join(cls),
                    width=width, height=height)
        if link:
            # The rel='lightbox[gallery]' attribute is actually a quick hack.
            # Lightbox is integrated within Wiking CMS, so LCG doesn't know
            # about it.  But CMS page content is generated by LCG and we want
            # to have images with thumbnails handled by lightbox.  This helps
            # and should not harm anything else (It has no effect when lightbox
            # is not loaded).
            img = g.a(img, href=link, title=title, rel='lightbox[gallery]')
        return img


    def _export_inline_audio(self, context, element):
        """Export emedded audio player for given audio file.

        Inline audio can be rendered as a simple link which controls a shared
        Flash audio player (usually located at the bottom right corner of a
        webpage) or using a standalone Flash audio player located directly
        inside page content in place of the link.  In both cases, if Flash or
        Javascript is not available, a simple link without a player is rendered
        allowing just downloading the audio file.

        """
        if element.shared():
            g = self._generator
            audio = element.audio(context)
            image = element.image(context)
            title = element.title()
            descr = element.descr()
            uri = context.uri(audio)
            link_id = context.unique_id()
            context.connect_shared_player(uri, link_id)
            if image:
                label = g.img(context.uri(image), alt=title)
                descr = descr or title
            else:
                label = title or audio.title() or audio.filename()
            return g.a(label, href=uri, id=link_id, title=descr, cls='media-control-link')
        else:
            raise NotImplementedError
        
    def _export_inline_video(self, context, element):
        """Export emedded video player for given video file.

        The 'Video' resource instance is rendered as a standalone Flash video
        player preloaded with given video.  If Flash or Javascript is not
        available, only a link to the video file is rendered.

        """
        g = self._generator
        if element.size() is None:
            width, height = (200, 200)
        else:
            width, height = element.size()
        video = element.video(context)
        image = element.image(context)
        uri = context.uri(video)
        title = element.title() or video.title() or video.filename()
        descr = element.descr() or video.descr()
        link = g.a(title, href=uri, title=descr)
        player = self.export_swf_object(context, 'mediaplayer.swf', context.unique_id(),
                                        width, height, min_flash_version='9.0.115',
                                        flashvars=dict(file=uri, title=title, description=descr,
                                                       image=(image and context.uri(image))),
                                        alternative_content=link)
        return g.div(player or link, cls='video-player')

    def _export_inline_external_video(self, context, element):
        """Export emedded video player for external services such as YouTube or Vimeo.
        
        A remote player from the video service is embedded into the page.
       
        """
        g = context.generator()
        service = element.service()
        if service == 'youtube':
            # rel=0 means do not load related videos
            video_uri = "http://www.youtube.com/v/%s?rel=0" % element.video_id()
        elif service == 'vimeo':
            video_uri = "http://vimeo.com/moogaloop.swf?clip_id=%s&server=vimeo.com" % element.video_id()
        else:
            Exception("Unsupported video service %s" % service)
        width, height = element.size() or (500,300)
        return g.object(
            (g.param(name="movie", value=video_uri),
             g.param(name="wmode", value="opaque")),
            type="application/x-shockwave-flash",
            title=element.title() or _("Flash movie object"),
            data=video_uri, width=width, height=height)

    def export_swf_object(self, context, filename, element_id, width, height, flashvars={},
                          min_flash_version=None, alternative_content=None, warning=None):
        """Export an arbitrary SWF object.
        
        This method tries to export a Flash object into HTML.  The object is
        not included directly, but using a mechanism with a Javascript library
        that ensures that if Javascript or Flash is not available on client
        side, alternative content (error message or a gracefull degradation)
        may be displayed.

        Arguments:
          filename -- name of the .swf file of the Flash object to embed (must
            be available through resources)
          element_id -- HTML id to use for the flash object HTML element  
            (necessary for communication via Javascript)
          width, height -- size of the HTML element in pixels
          flashvars -- dictionary of variables to pass to the flash object (through
            SWFObject's 'flashvars' parameter).
          min_flash_version -- minimal required Flash version as a string, such
            as '9' or '9.0.25'
          alternative_content -- HTML content (as a string or unicode) displayed
            inside the HTML element when Flash or JavaScript don't work on the
            client side (Flash not installed or its version doesn't match
            'min_flash_version', JS is disabled or not supoported, ...).  You
            may also pass a tuple of two strings in which case the first is
            used when Flash doesn't work and the second when the problem is in
            JavaScript.  If you wish to display simple warning messages, you
            may think of using the argument 'warning' instead of this one.
          warning -- Warning message displayed as alternative content.  This
            message will become a part of automatically created alternative
            content, so it cannot be used in combination with the
            'alternative_content' argument.  Individual warnings are generated
            to cover both situations (no JS and no Flash).  They will look like:
            ``Warning: <warning> Get Adobe Flash plugin 9.0.10 or later.'' and 
            ``Warning: <warning> Use a JavaScript enabled browser.'', where
            ``<warning>'' is replaced by the value of this argument.
        
        """
        def warn_swfobject(msg):
            log(msg)
            log("Get SWFObject v2.1 from http://code.google.com/p/swfobject/ "
                "and put swfobject.js to your resource path.")
        def escape(value):
            return str(value).replace('?', '%3F').replace('=', '%3D').replace('&', '%26')
        flash_object = context.resource(filename)
        if flash_object is None:
            return None
        swfobject_js = context.resource('swfobject.js', warn=warn_swfobject)
        if swfobject_js is None:
            return None
        flash_js = context.resource('flash.js')
        if flash_js is None:
            return None
        g = self._generator
        if isinstance(alternative_content, tuple):
            no_flash_content, no_js_content = alternative_content
            no_flash_content = context.localize(no_flash_content)
        elif warning and alternative_content is None:
            # Translators: Warning message displayed if Flash plugin is not installed or doesn't
            # have the required version.  '%(plugin)s' is automatically replaced by a hypertext
            # link to Adobe Flash plugin download page.  '%(version)s' is replaced by the required
            # version number.
            msg1 = _("Get %(plugin)s %(version)s or later.",
                     version=min_flash_version or '9',
                     # Translators: Title of the link to Adobe website used in
                     # the Flash warning.
                     plugin=g.a(_("Adobe Flash plugin"),
                                href='http://www.adobe.com/products/flash/about/'))
            msg2 = _("Use a JavaScript enabled browser.")
            no_flash_content = context.localize(g.strong(_("Warning:")) +' '+ warning +' '+ msg1)
            no_js_content = g.strong(_("Warning:")) +' '+ warning +' '+ msg2
        else:
            no_flash_content = None
            no_js_content = alternative_content
        # Here we first create a DIV containing error text about js not
        # working, then a javascript code that replaces this error message with
        # the flash object when page is loaded into browser and js is working.
        return (g.div(no_js_content or '', id=element_id) + 
                g.script(g.js_call('embed_swf_object', context.uri(flash_object), element_id,
                                   width, height, flashvars, min_flash_version, no_flash_content)))

    def export_media_player(self, context, player_id, width, height, shared=False):
        """Export Flash media player
        
        The player can be controlled from other parts of the webpage through
        Javascript functions defined in 'media.js'.
        
        Caution: The media player works only if the webpage is served through a
        webserver. If it is displayed locally, Flash and Javascript
        communication is not possible due to security restrictions. The player
        displays but there is no way to controll it.
        
        Arguments:
          context, player_id, width, height -- see 'export_swf_object()' arguments
          shared -- whether to use a shared media player (e.g. in bottom right corner
            of a webpage to serve many different media playback requests)
        
        """
        g = self._generator
        result = self.export_swf_object(context, 'mediaplayer.swf', player_id, width, height,
                                        min_flash_version='9.0.115',
                                        warning=_("Media Player unavailable."))
        if result:
            context.resource('media.js')
            result += g.script(g.js_call('init_media_player', player_id, shared))
        return result

    def _media_player(self, context):
        """Export shared media player if in use, otherwise do nothing.

        See export_media_player() for more details.
        
        """
        controls = context.shared_player_controls()
        if controls:
            # Shared player controls exist, so create the player and connect the controls to it.
            g = self._generator
            player_id = 'shared-audio-player'
            # export_media_player() returns None if one of the dependencies is not found...
            content = self.export_media_player(context, player_id, 300, 20, shared=True)
            if content:
                for args in controls:
                    content += "\n"+ g.script(g.js_call('init_player_controls', player_id, *args))
            return content
        else:
            return None

    def escape(self, text):
        return self._generator.escape(text)
    
    def concat(self, *items):
        return self._generator.concat(*items)
    
    def _reformat_text(self, text):
        return text

    def _html_conetnt(self, context):
        g = self._generator
        # Export body first to allocate all resources before generating the head.
        body = g.body(self._body_content(context), **self._body_attr(context))
        head = g.head(self._head(context))
        return concat(head, body)
    
    def export(self, context):
        g = self._generator
        return concat('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">',
                      #'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">',
                      '\n\n',
                      g.html(self._html_conetnt(context), lang=context.lang()))


class Html5Exporter(HtmlExporter):
    Generator = XhtmlGenerator

    def _export_inline_audio(self, context, element):
        """Override with HTML5 audio element."""
        # TODO: shared not supported
        g = self._generator
        audio = element.audio(context)
        image = element.image(context)
        title = element.title()
        descr = element.descr()
        uri = context.uri(audio)
        if image:
            # TODO: image not supported in AUDIO tag capable browsers (only in
            # compatibility content).
            label = g.img(context.uri(image), alt=title)
            descr = descr or title
        else:
            label = title or audio.title() or audio.filename()
        return g.audio(src=uri, title=descr or title or audio.title() or audio.filename(),
                       # 'content' is displayed only in browsers not supporting the audio tag.
                       content=g.a(label, href=uri, title=descr))

    def _export_inline_video(self, context, element):
        """Export emedded video player for given video file.

        The 'Video' resource instance is rendered as a standalone Flash video
        player preloaded with given video.  If Flash or Javascript is not
        available, only a link to the video file is rendered.

        """
        video = element.video(context)
        if video.filename().lower().endswith('.flv'):
            return super(Html5Exporter, self)._export_inline_video(context, element)
        g = self._generator
        size = element.size()
        if size is None:
            width, height = (None, None)
        else:
            width, height = size
        image = element.image(context)
        uri = context.uri(video)
        title = element.title() or video.title() or video.filename()
        descr = element.descr() or video.descr()
        return g.video(src=uri, title=descr or title, poster=image and context.uri(image),
                       width=width, height=height,
                       # 'content' is displayed only in browsers not supporting the audio tag.
                       content=g.a(title, href=uri, title=descr))
    
    def export(self, context):
        g = self._generator
        return concat('<?xml version="1.0" encoding="UTF-8"?>', '\n',
                      '<!DOCTYPE html>', '\n',
                      g.html(self._html_conetnt(context), lang=context.lang(),
                             xmlns='http://www.w3.org/1999/xhtml'))
                      

class HtmlFileExporter(FileExporter, HtmlExporter):
    """Export the content as a set of html files."""
    
    _OUTPUT_FILE_EXT = 'html'
    
    def _uri_node(self, context, node, lang=None):
        return self._filename(node, context, lang=lang)

    def dump(self, node, directory, filename=None, **kwargs):
        super(HtmlFileExporter, self).dump(node, directory, filename=filename, **kwargs)
        for n in node.children():
            self.dump(n, directory, **kwargs)
        for r in node.resources():
            self._export_resource(r, directory)


class StyledHtmlExporter(object):
    """Mix-in class for HTML exporter with a CSS support."""
    
    def __init__(self, styles=(), inlinestyles=False, **kwargs):
        """Initialize the exporter."""
        super(StyledHtmlExporter, self).__init__(**kwargs)
        self._styles = styles
        self._inlinestyles = inlinestyles

    def _stylesheets(self, context):
        """Return the list of 'Stylesheet' instances for given context/node."""
        return context.node().resources(Stylesheet)
        
    def _head(self, context):
        for style in self._styles:
            context.resource(style)
        styles = self._stylesheets(context)
        if self._inlinestyles:
            tags = ['<style type="text/css" media="%s">\n%s</style>' % (media, content)
                    for media, content in [(s.media(), s.get()) for s in styles]
                    if content is not None]
        else:
            tags = ['<link rel="stylesheet" type="text/css" href="%s" media="%s">' % \
                    (context.uri(s), s.media()) for s in styles]
        return super(StyledHtmlExporter, self)._head(context) + tags
    
    def _export_resource(self, resource, dir):
        if self._inlinestyles and isinstance(resource, Stylesheet):
            pass
        else:
            super(StyledHtmlExporter, self)._export_resource(resource, dir)


class HtmlStaticExporter(StyledHtmlExporter, HtmlFileExporter):
    """Export the content as a set of static web pages with navigation."""

    _hotkey = {
        'prev': '1',
        'next': '3',
        'up': '2',
        'index': '4',
        }

    _BODY_PARTS = ('top_navigation',
                   'heading',
                   'language_selection',
                   'content',
                   'bottom_navigation',
                   'media_player',
                   )

    def _head(self, context):
        base = super(HtmlStaticExporter, self)._head(context)
        node = context.node()
        additional = [concat('<link rel="%s" href="%s" title="' % (kind, self.uri(context, n)),
                             n.title() ,'">')
                      for kind, n in (('top', node.root()), 
                                      ('prev', node.prev()),
                                      ('next', node.next()),
                                      ('parent', node.parent()))
                      if n is not None and n is not node]
        return concat(base, additional, separator='\n  ')

    def _language_selection(self, context):
        if context.node() is not context.node().root():
            return None
        else:
            return super(HtmlStaticExporter, self)._language_selection(context)
        
    def _top_navigation(self, context):
        navigation = self._navigation(context)
        if navigation:
            return navigation + '<hr>\n'
        else:
            return None

    def _bottom_navigation(self, context):
        navigation = self._navigation(context)
        if navigation:
            return '<hr>\n' + navigation
        else:
            return None
        
    def _navigation(self, context):
        node = context.node()
        root = node.root()
        if len(root.linear()) <= 1:
            return None
        g = self._generator
        parent = node.parent()
        def link(target, label=None, key=None):
            if target:
                hidden = ''
                if label is None:
                    label = target.title(brief=True)
                if not key:
                    if target == root:
                        key = 'index'
                        if target == parent:
                            hidden = g.a('', href=self.uri(context, target),
                                         hotkey=self._hotkey['up'], cls='hidden')
                    elif target == parent:
                        key = 'up'
                return g.a(label, href=self.uri(context, target), title=target.title(),
                           hotkey=key and self._hotkey[key]) + hidden
            else:
                # Translators: Label used instead of a link when the target does not exist.  For
                # example sequential navigation may contain: "Previous: Introduction, Next: None".
                return _("None")
        breadcrumbs = g.div(_("You are here:") +' '+ \
                            concat([link(n) for n in node.path()], separator=' / '))
        nav = [
            # Translators: Label of a link to the next page in sequential navigation.
            g.span(_('Next') + ': ' + link(node.next(), key='next'), cls='next'),
            # Translators: Label of a link to the next page in sequential navigation.
            g.span(_('Previous') + ': ' + link(node.prev(), key='prev'), cls='prev')]
        return breadcrumbs + concat(nav, separator=g.span(' |\n', cls='separator'))
        
