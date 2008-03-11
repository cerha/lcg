# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2008 Brailcom, o.p.s.
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

_ = TranslatableTextFactory('lcg')

class HtmlGenerator(Generator):

    def _attr(self, valid, **kwargs):
        result = ''
        #if kwargs.get('lang'):
        #    kwargs['style'] = 'color: red;' + (kwargs.get('style') or '')
        for name in valid + ('id', 'lang', 'cls', 'style'):
            if not kwargs:
                break
            value = kwargs.pop(name, None)
            if name == 'cls':
                name = 'class'
            if value is None or value is False:
                continue
            elif value is True:
                result += ' ' + name
            else:
                if isinstance(value, int):
                    value = str(value)
                result += ' ' + name + '="' + value + '"'
        assert not kwargs, "Invalid attributes: %s" % kwargs
        return result

    def _tag(self, tag, content, _attributes=(), _newlines=False, **kwargs):
        separator = _newlines and "\n" or ""
        start = '<' + tag + self._attr(_attributes, **kwargs) + '>' + separator
        end = '</' + tag + '>' + separator
        if isinstance(content, (tuple, list)):
            content = concat(content, separator=separator)
        if _newlines and not content.endswith('\n'):
            end = separator + end
        return concat(start, content, end)
     
    def _input(self, type, _attr=(), **kwargs):
        attr = ('type', 'name', 'value', 'title', 'tabindex', 'size', 'maxlength', 'onclick',
                'readonly', 'disabled')
        return concat('<input', self._attr(attr + _attr, type=type, **kwargs), ' />')

    # Generic constructs
     
    def h(self, title, level, **kwargs):
        return self._tag('h%d' % level, title, **kwargs) + '\n'
        
    def strong(self, text, **kwargs):
        return self._tag('strong', text, **kwargs)
     
    def pre(self, text, **kwargs):
        return self._tag('pre', text, _newlines=True, **kwargs)
     
    def sup(self, text, **kwargs):
        return self._tag('sup', text, **kwargs)
    
    def sub(self, text, **kwargs):
        return self._tag('sub', text, **kwargs)
    
    def p(self, *content, **kwargs):
        return self._tag('p', content, _newlines=True, **kwargs)
     
    def br(self, **kwargs):
        return concat('<br', self._attr((), **kwargs), '/>')
     
    def hr(self, **kwargs):
        return concat('<hr', self._attr((), **kwargs), '/>')
     
    def link(self, label, uri, title=None, target=None, hotkey=None, cls=None, **kwargs):
        if hotkey and title:
            title += ' (%s)' % hotkey
        if target:
            cls = (cls and cls+' ' or '') + 'external-link'
        attr = ('href', 'type', 'name', 'title', 'target', 'accesskey')
        return self._tag('a', label, attr, href=uri, title=title, target=target,
                         accesskey=hotkey, cls=cls, **kwargs)

    def list(self, items, indent=0, ordered=False, style=None, **kwargs):
        tag = ordered and 'ol' or 'ul'
        attr = self._attr((), style=(style and 'list-style-type: %s' % style), **kwargs)
        spaces = ' ' * indent
        items = [concat(spaces+'  <li>', i, '</li>\n') for i in items]
        return concat(spaces +'<'+ tag, attr, '>\n', items, spaces +'</'+ tag +'>\n')
     
    def img(self, src, alt='', border=0, descr=None, **kwargs):
        attr = ('src', 'alt', 'longdesc', 'width', 'height', 'align', 'border')
        return '<img'+ self._attr(attr, src=src, alt=alt, longdesc=descr, border=border,
                                  **kwargs) +' />'

    def abbr(self, term, **kwargs):
        return self._tag('abbr', term, ('title',), **kwargs)

    def th(self, content, **kwargs):
        return self._tag('th', content, ('colspan', 'width', 'align', 'valign', 'scope'), **kwargs)
    
    def td(self, content, **kwargs):
        return self._tag('td', content, ('colspan', 'width', 'align', 'valign', 'scope'), **kwargs)
    
    def tr(self, content, **kwargs):
        return self._tag('tr', content, **kwargs)

    def table(self, content, **kwargs):
        attr = ('title', 'summary', 'border', 'cellspacing', 'cellpadding', 'width')
        return self._tag('table', content, attr, _newlines=True, **kwargs)

    def thead(self, content):
        return self._tag('thead', content)
    
    def tfoot(self, content):
        return self._tag('tfoot', content)
    
    def tbody(self, content):
        return self._tag('tbody', content, _newlines=True)
    
    # HTML specific...
    
    def escape(self, text):
        return saxutils.escape(text)

    def uri(self, base, *args, **kwargs):
        uri = urllib.quote(base.encode('utf-8'))
        query = ';'.join([k +'='+ urllib.quote(unicode(v).encode('utf-8'))
                          for k,v in args + tuple(kwargs.items()) if v is not None])
        if query:
            uri += '?' + query
        return uri
     
    def span(self, text, **kwargs):
        return self._tag('span', text, **kwargs)
     
    def div(self, content, **kwargs):
        return self._tag('div', content, _newlines=True, **kwargs)
     
    def map(self, content, **kwargs):
        return self._tag('map', content, ('name', 'title'), _newlines=True, **kwargs)

    # Form controls
     
    def form(self, content, action="#", **kwargs):
        attr = ('name', 'action', 'method', 'enctype')
        return self._tag('form', content, attr, _newlines=True, action=action, **kwargs)
     
    def fieldset(self, legend, content, **kwargs):
        content = (self._tag('legend', legend or '', cls=(not legend and 'empty' or None)),) +\
                   tuple(content)
        return self._tag('fieldset', content, _newlines=True, **kwargs)
     
    def label(self, text, id, **kwargs):
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
        return self._input('radio', ('checked',), name=name, **kwargs)
     
    def hidden(self, name, value):
        return self._input('hidden', name=name, value=value)
     
    def button(self, label, handler, cls=None, **kwargs):
        cls = cls and 'button ' + cls or 'button'
        return self._input('button', value=label, onclick=handler, cls=cls, **kwargs)
     
    def reset(self, label, onclick=None, cls=None, title=None):
        return self._input('reset', title=title, onclick=onclick, value=label, cls=cls)
     
    def submit(self, label, value=None, **kwargs):
        if value is None:
            return self._input('submit', value=label, **kwargs)
        else:
            attr = ('value', 'onclick' 'name', 'cls', 'disabled', 'title')
            return self._tag('button', label, attr, value=value, **kwargs)
            
    def select(self, name, options, selected=None, **kwargs):
        assert selected is None or selected in [x[1] for x in options], (selected, options)
        def opt(label, value, enabled=True, cls=None):
            if isinstance(value, (list, tuple)):
                return self._tag('optgroup', [opt(*x) for x in value], ('label',), label=label,
                                 _newlines=True)
            else:
                return self._tag('option', label, ('value', 'selected', 'disabled'),
                                 value=value, selected=(value == selected), disabled=not enabled,
                                 cls=not enabled and (cls and cls+' ' or '')+'disabled' or cls)
        opts = [opt(*x) for x in options]
        attr = ('name', 'title', 'onchange', 'disabled', 'readonly')
        return self._tag('select', opts, attr, _newlines=True, name=name, **kwargs)
     
    def checkbox(self, name, **kwargs):
        return self._input('checkbox', ('checked',), name=name, **kwargs)
     
    def textarea(self, name, value='', **kwargs):
        attr = ('name', 'rows', 'cols', 'readonly')
        return self._tag('textarea', value, attr, name=name, **kwargs)
     
    # Special controls
     
    def speaking_text(self, text, media):
        id_ = 'text_%s' % id(media)
        a1 = self.button(text, "play_audio('%s');" % media.uri(), cls='speaking-text')
        a2 = self.link(text, media.uri(), cls='speaking-text')
        return self.script_write(a1, a2)

    # JavaScript code generation.
     
    def script(self, code, noscript=None):
        return '<script type="text/javascript" language="Javascript">'+ \
               (code and '<!--\n' + code + ' //-->\n' or '') + \
               '</script>' + \
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
            return "'" + var.replace("'", "\\'") + "'"
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
        assert is_sequence_of(dict(items).keys(), types.StringType)
        pairs = [concat("'%s': " % k, self.js_value(v)) for k,v in items]
        return concat('{', concat(pairs, separator=", "), '}')
     
    def js_args(self, *args):
        return concat([self.js_value(arg) for arg in args], separator=", ")
     

class HtmlFormatter(MarkupFormatter):
    
    _FORMAT = {'emphasize': ('<em>', '</em>'),
               'strong': ('<strong>', '</strong>'),
               'fixed': ('<tt>', '</tt>'),
               'underline': ('<span class="underline">', '</span>'),
               'citation': ('<span class="citation">', '</span>'),
               'quotation': (u'“<span class="quotation">', u'</span>”'),
               'comment': '',
               'linebreak': '<br/>',
               'dash': '&ndash;',
               'nbsp': '&nbsp;',
               'lt':   '&lt;',
               'gt':   '&gt;',
               'amp':  '&amp;',
               }
    
    _BLANK_MATCHER = re.compile('\s+')
    _IMAGE_URI_MATCHER = re.compile(r'^(?P<align>[<>])?(?P<name>'
                                    '(?P<basename>[\w\d_.,/-]+)\.'
                                    '(jpe?g|png|gif))$', re.IGNORECASE)
    _IMAGE_ALIGN_MAPPING = {'>': InlineImage.RIGHT, '<': InlineImage.LEFT}

    def _citation_formatter(self, context, close=False, **kwargs):
        if not close:
            lang = context.sec_lang()
            langattr = lang and ' lang="%s"' % lang or ''
            return '<span%s class="citation">' % langattr
        else:
            return '</span>'

    def _match_image(self, uri):
        match = self._IMAGE_URI_MATCHER.match(uri)
        if match:
            uri = match.group('name')
            name = match.group('basename').split('/')[-1].replace('.','-')
            align = self._IMAGE_ALIGN_MAPPING.get(match.group('align'))
            return True, uri, dict(name=name, align=align)
        return False, uri, {}
        
    def _find_resource(self, node, cls, filename, label, descr, fallback=False, **imgargs):
        result = node.resource(cls, filename, fallback=False)
        if not result and fallback:
            if issubclass(cls, XResource):
                result = resource(node, cls, filename, fallback=True, title=label)
            else:
                log("%s: Unknown resource: %s: %s" % (node.id(), cls.__name__, filename))
                result = cls(filename, title=label)
        if result:
            title = label or result.title()
            if isinstance(result, Image):
                return InlineImage(result, title=title, **imgargs)
            else:
                return Link(result, label=title)
        return None

    def _link_formatter(self, context, label=None, href=None, anchor=None, descr=None, **kwargs):
        node = None
        result = None
        parent = context.node()
        if href and not anchor:
            is_image, href, imgargs = self._match_image(href)
            cls = is_image and Image or Resource
            result = self._find_resource(parent, cls, href, label, descr, fallback=is_image,
                                         **imgargs)
        if not result:
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
            if not target:
                if anchor is not None:
                    href += '#'+anchor
                target = Link.ExternalTarget(href, label or href)
            if label:
                parts = self._BLANK_MATCHER.split(label, maxsplit=1)
                is_image, uri, imgargs = self._match_image(parts[0])
                if is_image:
                    title = len(parts) == 2 and parts[1] or None
                    label = self._find_resource(parent, Image, uri, title, descr, fallback=True,
                                                **imgargs)
                    if isinstance(target, Link.ExternalTarget):
                        target = Link.ExternalTarget(href, title, descr=title)
            result = Link(target, label=label, descr=descr)
        result.set_parent(parent)
        return result.export(context)
    
    def _uri_formatter(self, context, uri, close=False, **kwargs):
        return self._link_formatter(context, href=uri, label=None)

    def _email_formatter(self, context, email, close=False, **kwargs):
        return self._link_formatter(context, href='mailto:'+email, label=email)

    
class HtmlExporter(Exporter):
    #DOCTYPE = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'

    Generator = HtmlGenerator
    Formatter = HtmlFormatter
    
    _BODY_PARTS = ('heading',
                   'language_selection',
                   'content',
                   )
    _LANGUAGE_SELECTION_LABEL = _("Choose your language:")
    _LANGUAGE_SELECTION_COMBINED = False
    
    def __init__(self, stylesheet=None, inlinestyles=False, **kwargs):
        """Initialize the exporter."""
        super(HtmlExporter, self).__init__(**kwargs)
        self._stylesheet = stylesheet
        self._inlinestyles = inlinestyles
    
    def _output_file(self, context, node, lang=None):
        """Return the pathname of node's output file relative to export dir."""
        name = node.id().replace(':', '-')
        if lang is None:
            lang = context.lang()
        if lang is not None and len(node.variants()) > 1:
            name += '.'+lang
        return name + '.html'

    def _node_uri(self, context, node, lang=None):
        return self._output_file(context, node, lang=lang)

    def uri(self, context, target, relative_to=None):
        """Return the URI of the target as string."""
        if isinstance(target, ContentNode):
            return self._node_uri(context, target)
        elif isinstance(target, Section):
            if relative_to is not None and relative_to is target.parent():
                base = ''
            else:
                base = self.uri(context, target.parent())
            return base + "#" + target.anchor()
        elif isinstance(target, (Link.ExternalTarget, Resource)):
            return target.uri()
        else:
            raise Exception("Invalid URI target:", target)
    
    def _styles(self, context):
        if self._inlinestyles:
            return ['<style type="text/css">\n%s</style>' % s.get()
                    for s in context.node().resources(Stylesheet)]
        else:
            return ['<link rel="stylesheet" type="text/css" href="%s">' % \
                    s.uri() for s in context.node().resources(Stylesheet)]
            
    def _title(self, context):
        return context.node().title()

    def _meta(self, context):
        import lcg
        return (('generator', 'LCG %s (http://www.freebsoft.org/lcg)' % lcg.__version__),)
    
    def _head(self, context):
        node = context.node()
        if self._stylesheet is not None:
            node.resource(XStylesheet, self._stylesheet)
        tags = [concat('<title>', self._title(context), '</title>')] + \
               ['<meta http-equiv="%s" content="%s">' % pair
                for pair in (('Content-Type', 'text/html; charset=UTF-8'),
                             ('Content-Language', context.lang()),
                             ('Content-Script-Type', 'text/javascript'),
                             ('Content-Style-Type', 'text/css'))] + \
               ['<meta name="%s" content="%s">' % pair for pair in self._meta(context)] + \
               ['<link rel="alternate" lang="%s" href="%s">' % \
                (lang, self._node_uri(context, node, lang=lang))
                for lang in node.variants() if lang != context.lang()] + \
               ['<script language="Javascript" type="text/javascript"' + \
                ' src="%s"></script>' % s.uri()
                for s in node.resources(Script)]
        return concat('  ', concat(tags + self._styles(context), separator='\n  '))

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
        g = context.generator()
        node = context.node()
        variants = list(node.variants())
        if len(variants) <= 1:
            return None
        variants.sort()
        links = []
        for lang in variants:
            label = language_name(lang)
            if lang == context.lang():
                sign = g.span(' *', cls='hidden')
                cls = 'current'
            else:
                sign = ''
                cls = None
            image = self._language_selection_image(context, lang)
            if image:
                if self._LANGUAGE_SELECTION_COMBINED:
                    label += g.img(image, border=None)
                else:
                    label = g.img(image, alt=label, border=None)
            links.append(g.link(label, self._node_uri(context, node, lang=lang), cls=cls)+sign)
        return concat(g.link(self._LANGUAGE_SELECTION_LABEL, None,
                             name='language-selection-anchor'),
                      "\n", concat(links, separator=" "+g.span('|', cls='sep')+"\n"))

    def _language_selection_image(self, context, lang):
        #return context.node().resource(Image, 'flags/%s.gif' % lang).uri()
        return None
    
    def _content(self, context):
        return context.node().content().export(context)
    
    def export(self, context):
        lines = (self.DOCTYPE, '',
                 '<html lang="%s">' % context.lang(),
                 '<head>',
                 self._head(context),
                 '</head>',
                 '<body>',
                 self._parts(context, self._BODY_PARTS),
                 '</body>',
                 '</html>')
        return concat(lines, separator="\n")


class FileExporter(object):
    """Mix-in class exporting content into files."""

    class Context(Exporter.Context):
        def _init_kwargs(self, directory=None, **kwargs):
            assert isinstance(directory, str)
            self._directory = directory
            super(FileExporter.Context, self)._init_kwargs(**kwargs)
            
        def directory(self):
            return self._directory

    def _write_file(self, filename, content):
        file = open(filename, 'w')
        file.write(content.encode('utf-8'))
        file.close()
    
    def dump(self, node, directory, sec_lang=None):
        """Save the node's content and resources into files recursively."""
        if not os.path.isdir(directory):
            os.makedirs(directory)
        for lang in node.variants() or (None,):
            context = self.context(node, lang, directory=directory, sec_lang=sec_lang)
            filename = os.path.join(directory, self._output_file(context, node))
            self._write_file(filename, context.translate(self.export(context)))
        for r in node.resources():
            r.export(directory)
        for n in node.children():
            self.dump(n, directory, sec_lang=sec_lang)


class HtmlStaticExporter(FileExporter, HtmlExporter):
    """Export the content as a set of static web pages."""

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
        nav = self._navigation(context)
        if nav:
            return g.div(nav, cls='navigation') + '<hr class="hidden">\n'
        else:
            return None

    def _bottom_navigation(self, context):
        nav = self._navigation(context)
        if nav:
            return '<hr class="hidden">\n' + g.div(nav, cls='navigation')
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
                            hidden = g.link('', self.uri(context, target),
                                            hotkey=self._hotkey['up'], cls='hidden')
                    elif target == parent:
                        key = 'up'
                return g.link(label, self.uri(context, target), title=target.title(),
                              hotkey=key and self._hotkey[key]) + hidden
            else:
                return _("None")
        breadcrumbs = g.div(_("You are here:") +' '+ \
                            concat([link(n) for n in node.path()], separator=' / '))
        nav = [g.span(_('Next') + ': ' + link(node.next(), key='next'), cls='next'),
               g.span(_('Previous') + ': ' + link(node.prev(), key='prev'), cls='prev')]
        return breadcrumbs + concat(nav, separator=g.span(' |\n', cls='separator'))

            
