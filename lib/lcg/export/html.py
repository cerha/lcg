# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007 Brailcom, o.p.s.
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

    def _attr(self, *pairs):
        attributes = []
        for attr, value in pairs:
            if value is None:
                continue
            elif isinstance(value, types.BooleanType):
                if not value:
                    continue
                string = attr
            else:
                if isinstance(value, int):
                    value = str(value)
                string = concat(attr+'="', value, '"')
            attributes.append(concat(' ', string))
        return concat(*attributes)
     
    def _tag(self, tag, attr, content, newlines=False):
        start = concat('<'+tag, self._attr(*attr), '>')
        end = '</%s>' % tag
        if isinstance(content, (types.ListType, types.TupleType)):
            result = (start,) + tuple(content) + (end,)
        else:
            result = (start, content, end)
        return concat(result, separator=(newlines and "\n" or ""))
     
    def _input(self, type, name=None, value=None, title=None, id=None,
               tabindex=None, onclick=None, size=None, maxlength=None,
               cls=None, readonly=False, checked=False, disabled=False):
        assert isinstance(type, str)
        assert isinstance(checked, bool)
        assert isinstance(readonly, bool)
        assert isinstance(disabled, bool)
        assert not checked or type in ('radio', 'checkbox')
        assert tabindex is None or isinstance(tabindex, int)
        attr = self._attr(('type', type),
                          ('name', name),
                          ('value', value),
                          ('title', title),
                          ('id', id),
                          ('tabindex', tabindex),
                          ('size', size),
                          ('maxlength', maxlength),
                          ('onclick', onclick),
                          ('class', cls),
                          ('checked', checked),
                          ('readonly', readonly),
                          ('disabled', disabled))
        return concat('<input', attr, ' />')

    # Generic constructs
     
    def h(self, title, level=2):
        return concat('<h%d>' % level, title, '</h%d>' % level)
        
    def strong(self, text, cls=None, id=None, lang=None):
        attr = (('class', cls),
                ('lang', lang),
                ('id', id))
        return self._tag('strong', attr, text)
     
    def pre(self, text, cls=None):
        return self._tag('pre', (('class', cls),), text)
     
    def p(self, *content, **kwargs):
        return self._tag('p', (('class', kwargs.get('cls')),), content,
                         newlines=True)
     
    def br(self, cls=None):
        return concat('<br', self._attr(('class', cls),), '/>')
     
    def hr(self, cls=None):
        return concat('<hr', self._attr(('class', cls),), '/>')
     
    def sup(self, text, cls=None):
        return self._tag('sup', (('class', cls),), text)
    
    def sub(self, text, cls=None):
        return self._tag('sub', (('class', cls),), text)
    
    def link(self, label, uri, name=None, title=None, target=None, cls=None,
             hotkey=None, type=None):
        if hotkey and title:
            title += ' (%s)' % hotkey
        if target:
            cls = (cls and cls+' ' or '') + 'external-link'
        attr = (('type', type), ('href', uri), ('name', name),
                ('title', title), ('target', target), ('class', cls),
                ('accesskey', hotkey))
        return self._tag('a', attr, label)
     
    def list(self, items, indent=0, ordered=False, style=None, cls=None,
             lang=None):
        tag = ordered and 'ol' or 'ul'
        attr = self._attr(('style', style and 'list-style-type: %s' % style),
                          ('lang', lang),
                          ('class', cls))
        spaces = ' ' * indent
        items = [concat(spaces+"  <li>", i, "</li>\n") for i in items]
        return concat(spaces+"<"+tag, attr,">\n", items, spaces+"</"+tag+">")
     
    def img(self, src, alt='', width=None, height=None, align=None,
            descr=None, cls=None):
        attr = (('src', src),
                ('alt', alt),
                ('longdesc', descr),
                ('width', width),
                ('height', height),
                ('align', align),
                ('border', 0),
                ('class', cls),
                )
        return concat('<img', self._attr(*attr), ' />')

    def escape(self, text):
        from xml.sax import saxutils
        return saxutils.escape(text)

    # HTML specific...
    
    def span(self, text, cls=None, id=None, lang=None, style=None):
        attr = (('id', id),
                ('lang', lang),
                ('class', cls),
                ('style', style))
        return self._tag('span', attr, text)
     
    def div(self, content, id=None, cls=None, lang=None):
        args = (('class', cls), ('id', id), ('lang', lang))
        return self._tag('div', args, content, newlines=True)
     
    def map(self, content, name=None, title=None, lang=None, id=None, cls=None):
        args = (('name', name), ('title', title), ('lang', lang), ('id', id), ('class', cls))
        return self._tag('map', args, content, newlines=True)

    def uri(self, base, *args, **kwargs):
        args += tuple(kwargs.items())
        if args:
            return base + '?' + ';'.join(["%s=%s" % item for item in args])
        else:
            return base
     
    # Form controls
     
    def form(self, content, name=None, cls=None, action="#", method=None,
             enctype=None):
        attr = (('name', name), ('action', action), ('method', method),
                ('enctype', enctype), ('class', cls))
        return self._tag('form', attr, content, newlines=True)
     
    def fieldset(self, content, legend=None, cls=None):
        if legend:
            content = (self._tag('legend', (), legend),) + tuple(content)
        return self._tag('fieldset', (('class', cls),), content, newlines=True)
     
    def label(self, text, id, lang=None, cls=None):
        attr = (('for', id), ('lang', lang), ('class', cls))
        return self._tag('label', attr, text)
     
    def field(self, value='', name='', size=20, password=False, cls=None,
              **kwargs):
        type = password and 'password' or 'text'
        kwargs['cls'] = type + (cls and ' '+cls or '')
        return self._input(type, name=name, value=value, size=size, **kwargs)
     
    def upload(self, name, size=50, cls=None, **kwargs):
        cls = 'upload' + (cls and ' '+cls or '')
        return self._input('file', name=name, size=size, cls=cls, **kwargs)
     
    def radio(self, name, **kwargs):
        return self._input('radio', name=name, **kwargs)
     
    def hidden(self, name, value):
        return self._input('hidden', name=name, value=value)
     
    def button(self, label, handler, cls=None, title=None):
        cls = cls and 'button ' + cls or 'button'
        return self._input('button', value=label, onclick=handler, cls=cls,
                           title=title)
     
    def reset(self, label, onclick=None, cls=None):
        return self._input('reset', onclick=onclick, value=label, cls=cls)
     
    def submit(self, label, onclick=None, cls=None):
        return self._input('submit', onclick=onclick, value=label, cls=cls)
     
    def select(self, name, options, onchange=None, selected=None, id=None,
               disabled=False, readonly=False):
        assert selected is None or \
               selected in [value for text, value in options], \
               (selected, options)
        opts = [self._tag('option',
                          (('value', value),
                           ('selected', (value == selected))),
                          text)
                for text, value in options]
        attr = (('name', name), ('id', id), ('onchange', onchange),
                ('disabled', disabled), ('readonly', readonly))
        return self._tag('select', attr, opts, newlines=True)
     
    def checkbox(self, name, value=None, id=None, checked=False,
                 disabled=False, readonly=False, cls=None):
        return self._input('checkbox', name=name, value=value, id=id,
                           checked=checked, disabled=disabled,
                           readonly=readonly, cls=cls)
     
    def textarea(self, name, value='', id=None, rows=None, cols=None,
                 readonly=False, cls=None):
        attr = (('name', name),
                ('id', id),
                ('rows', rows),
                ('cols', cols),
                ('readonly', readonly),
                ('class', cls))
        return self._tag('textarea', attr, value)
     
    # Special controls
     
    def speaking_text(self, text, media):
        id_ = 'text_%s' % id(media)
        a1 = self.button(text, "play_audio('%s');" % media.uri(),
                         cls='speaking-text')
        a2 = self.link(text, media.uri(), cls='speaking-text')
        return self.script_write(a1, a2)
     
    # JavaScript code generation.
     
    def script(self, code, noscript=None):
        noscript = noscript and \
                   concat('<noscript>', noscript, '</noscript>') or ''
        if code:
            code = concat('<!--\n', code, ' //-->\n')
        return concat('<script type="text/javascript" language="Javascript">',
                            code, '</script>', noscript)
     
    def script_write(self, content, noscript=None, condition=None):
        #return content
        #return noscript
        if content:
            c = content.replace('"','\\"').replace("'","\\'")
            c = c.replace('</', '<\\/').replace('\n','\\n')
            content = concat('document.write("', c, '");')
            if condition:
                content = concat('if (', condition, ') ', content)
        return self.script(content, noscript)
     
    def js_value(self, var):
        if isinstance(var, types.StringTypes):
            return "'" + var.replace("'", "\\'") + "'"
        elif isinstance(var, (TranslatableText, Concatenation)):
            return concat("'", var.replace("'", "\\'"), "'")
        elif isinstance(var, types.IntType):
            return str(var)
        elif isinstance(var, (types.ListType, types.TupleType)):
            return self.js_array(var)
        else:
            raise Exception("Invalid type for JavaScript conversion:", var)
        
    def js_array(self, items):
        assert isinstance(items, (types.ListType, types.TupleType))
        values = [self.js_value(i) for i in items]
        return concat('[', concat(values, separator=", "), ']')
     
    def js_dict(self, items):
        assert isinstance(items, (types.ListType, types.TupleType, types.DictType))
        if isinstance(items, types.DictType):
            items = items.items()
        assert is_sequence_of(dict(items).keys(), types.StringType)
        pairs = [concat("'%s': " % k, self.js_value(v)) for k,v in items]
        return concat('{', concat(pairs, separator=", "), '}')
     

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
                                    '(?P<basename>[\w\d_./-]+)\.'
                                    '(jpe?g|png|gif))$', re.IGNORECASE)
    _IMAGE_ALIGN_MAPPING = {'>': InlineImage.RIGHT, '<': InlineImage.LEFT}

    def _citation_formatter(self, parent, close=False, **kwargs):
        if not close:
            lang = parent.secondary_language()
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
        
    def _find_resource(self, parent, cls, filename, label, fallback=False, **imgargs):
        result = parent.resource(cls, filename, fallback=False)
        if not result and fallback:
            if issubclass(cls, XResource):
                result = resource(parent, cls, filename, fallback=True,
                                  title=label)
            else:
                log("%s: Unknown resource: %s: %s" % (parent.id(), cls.__name__, filename))
                result = cls(filename, title=label)
        if result:
            title = label or result.title()
            if isinstance(result, Image):
                return InlineImage(result, title=title, **imgargs)
            else:
                return Link(result, label=title)
        return None

    def _link_formatter(self, parent, label=None, href=None, anchor=None,
                        close=False, xresource=None, **kwargs):
        node = None
        result = None
        if href and not anchor:
            is_image, href, imgargs = self._match_image(href)
            cls = is_image and Image or xresource and XResource or Resource
            fallback = bool(is_image or xresource)
            result = self._find_resource(parent, cls, href, label, fallback=fallback, **imgargs)
        if not result:
            if not href:
                node = parent
            elif href.find('@') == href.find('/') == -1:
                node = parent.root().find_node(href)
                if not node:
                    log("%s: Unknown node: %s" % (parent.id(), href))
            target = node
            if node and anchor:
                target = node.find_section(anchor)
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
                    label = self._find_resource(parent, Image, uri, title, fallback=True, **imgargs)
                    if isinstance(target, Link.ExternalTarget):
                        target = Link.ExternalTarget(href, title, descr=title)
            result = Link(target, label=label)
        result.set_parent(parent)
        return result.export(self._exporter)
    
    def _uri_formatter(self, parent, uri, close=False, **kwargs):
        return self._link_formatter(parent, href=uri, label=None)

    def _email_formatter(self, parent, email, close=False, **kwargs):
        return self._link_formatter(parent, href='mailto:'+email, label=email)

    
class HtmlExporter(Exporter):
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'

    _GENERATOR = HtmlGenerator
    _FORMATTER = HtmlFormatter
    
    _BODY_PARTS = ('heading',
                   'language_selection',
                   'content',
                   )
    _LANGUAGE_SELECTION_LABEL = _("Choose your language:")
    
    def __init__(self, stylesheet=None, inlinestyles=False, **kwargs):
        """Initialize the exporter."""
        super(HtmlExporter, self).__init__(**kwargs)
        self._stylesheet = stylesheet
        self._inlinestyles = inlinestyles
    
    def _output_file(self, node, lang=None):
        """Return the pathname of node's output file relative to export dir."""
        assert isinstance(node, ContentNode)
        name = node.id().replace(':', '-')
        if lang is None:
            lang = node.current_language_variant()
        if lang is not None and len(node.language_variants()) > 1:
            name += '.'+lang
        return name + '.html'

    def _node_uri(self, node, lang=None):
        return self._output_file(node, lang=lang)

    def uri(self, target, relative_to=None):
        """Return the URI of the target as string."""
        if isinstance(target, ContentNode):
            return self._node_uri(target)
        elif isinstance(target, Section):
            if relative_to is not None and relative_to is target.parent():
                base = ''
            else:
                base = self.uri(target.parent())
            return base + "#" + target.anchor()
        elif isinstance(target, (Link.ExternalTarget, Resource)):
            return target.uri()
        else:
            raise Exception("Invalid URI target:", target)
    
    def _styles(self, node):
        if self._inlinestyles:
            return ['<style type="text/css">\n%s</style>' % s.get()
                    for s in node.resources(Stylesheet)]
        else:
            return ['<link rel="stylesheet" type="text/css" href="%s">' % \
                    s.uri() for s in node.resources(Stylesheet)]
            
    def _title(self, node):
        return node.title()
    
    def _head(self, node):
        if self._stylesheet is not None:
            node.resource(XStylesheet, self._stylesheet)
        import lcg
        meta = node.meta() + \
               (('generator',
                 'LCG %s (http://www.freebsoft.org/lcg)' % lcg.__version__),)
        tags = [concat('<title>', self._title(node), '</title>')] + \
               ['<meta http-equiv="%s" content="%s">' % pair
                for pair in (('Content-Type', 'text/html; charset=UTF-8'),
                             ('Content-Language', node.language()),
                             ('Content-Script-Type', 'text/javascript'),
                             ('Content-Style-Type', 'text/css'))] + \
               ['<meta name="%s" content="%s">' % pair for pair in meta] + \
               ['<script language="Javascript" type="text/javascript"' + \
                ' src="%s"></script>' % s.uri()
                for s in node.resources(Script)]
        return concat('  ', concat(tags + self._styles(node), separator='\n  '))

    def _parts(self, node, parts):
        result = []
        for name in parts:
            content = self._part(name, node)
            if content is not None:
                result.append(content)
        return concat(result, separator="\n")
    
    def _part(self, name, node):
        content = getattr(self, '_'+name)(node)
        if content is not None:
            return self._generator.div(content, cls=name.replace('_', '-'))
        else:
            return None
        
    def _heading(self, node):
        return self._generator.h(node.title(), level=1)

    def _language_selection(self, node):
        g = self._generator
        #handler = ("location.href = this.form.language.options"
        #           "[this.form.language.selectedIndex].value")
        #select = g.form((g.label(self._label, 'language-selection'),
        #                 g.select('language',
        #                          [(t.title(), t.url())
        #                           for t in self._targets],
        #                          id='language-selection',
        #                          selected=self._current.url()),
        #                 g.button(_('Switch'), handler)),
        #                cls='language-selection')
        #radio = g.fieldset([g.radio('language', value=t.url(), id=tid,
        #                            onclick="location.href = this.value",
        #                            checked=(self._current.url()==t.url())
        #                            ) + \
        #                    g.label(flag.export(exporter) + t.title(), tid)
        #                    for t, tid, flag in
        #                    [(t, t.url().replace('.','-'), f)
        #                     for t, f in zip(self._targets, self._flags)]],
        #                   legend=self._label, cls='language-selection')
        if len(node.language_variants()) <= 1:
            return None
        current = node.current_language_variant()
        languages = list(node.language_variants()[:])
        languages.sort()
        links = []
        for lang in languages:
            name = language_name(lang)
            cls = None
            sign = ''
            if lang == current:
                sign = g.span(' *', cls='hidden')
                cls = 'current'
            links.append(g.link(name, self._node_uri(node, lang=lang), cls=cls)+sign)
            #flag = InlineImage(node.resource(Image, 'flags/%s.gif' % lang))
        return concat(g.link(self._LANGUAGE_SELECTION_LABEL, None, name='language-selection'),
                      "\n", concat(links, separator=" |\n"))

    def _content(self, node):
        return node.content().export(self)
    
    def export(self, node):
        if 'audio.js' in [r.uri().split('/')[-1]
                          for r in node.resources(Script)]:
            hack = ('\n<object id="media_player" height="0" width="0"'
		    ' classid="CLSID:6BF52A52-394A-11d3-B153-00C04F79FAA6">'
                    '</object>')
        else:
            hack = ''
        lines = (self.DOCTYPE, '',
                 '<html>',
                 '<head>',
                 self._head(node),
                 '</head>',
                 '<body lang="%s">' % node.language(),
                 self._parts(node, self._BODY_PARTS) + hack,
                 '</body>',
                 '</html>')
        return concat(lines, separator="\n")


class FileExporter(object):
    """Mix-in class exporting content into files."""
    
    def dump(self, node, directory):
        """Save the node's content and resources into files recursively."""
        if not os.path.isdir(directory):
            os.makedirs(directory)
        filename = os.path.join(directory, self._output_file(node))
        file = open(filename, 'w')
        file.write(self.translate(self.export(node)).encode('utf-8'))
        file.close()
        for r in node.resources():
            r.export(directory)
        for n in node.children():
            self.dump(n, directory)


class HtmlStaticExporter(HtmlExporter, FileExporter):
    """Export the content as a set of static web pages."""

    _hotkey = {
        'prev': '1',
        'next': '3',
        'up': '2',
        'index': '4',
        }

    _INDEX_LABEL = None

    _BODY_PARTS = ('navigation',
                   'rule',
                   'heading',
                   'language_selection',
                   'content',
                   'rule',
                   'navigation',
                   )
    
    def _head(self, node):
        base = super(HtmlStaticExporter, self)._head(node)
        additional = [format('<link rel="%s" href="%s" title="%s">',
                             kind, self.uri(n), n.title())
                      for kind, n in (('start', node.root()), 
                                      ('prev', node.prev()),
                                      ('next', node.next()))
                      if n is not None and n is not node]
        return concat(base, additional, separator='\n  ')

    def _language_selection(self, node):
        if node is not node.root():
            return None
        else:
            return super(HtmlStaticExporter, self)._language_selection(node)
        
    def _rule(self, node):
        if len(node.root().linear()) <= 1:
            return None
        return '<hr class="hidden">'
    
    def _navigation(self, node):
        if len(node.root().linear()) <= 1:
            return None
        g = self._generator
        def link(node, label=None, key=None):
            if node:
                if label is None:
                    label = node.title(brief=True)
                return g.link(label, self.uri(node), title=node.title(),
                              hotkey=not key or self._hotkey[key])
            else:
                return _("None")
        nav = [_('Next') + ': ' + link(node.next(), key='next'),
               _('Previous') + ': ' + link(node.prev(), key='prev')]
        hidden = ''
        if node is not node.root():
            p = node.parent()
            if p is not node.root():
                nav.append(_("Up") + ': ' + link(p, key='up'))
            else:
                hidden = concat("\n", link(p, key='up', label=''))
            nav.append(_("Top") + ': ' + link(node.root(), key='index',
                                              label=self._INDEX_LABEL))
        return concat(nav, separator=' |\n') + hidden


            
