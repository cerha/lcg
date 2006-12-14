# -*- coding: utf-8 -*-
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

from lcg import *
from lcg.export import *
from lcg.export import _html

_ = TranslatableTextFactory('lcg')


class HtmlMarkupFormatter(MarkupFormatter):
    
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
    
    _IMAGE_URI_MATCHER = re.compile(r'\.(jpe?g|png|gif)$', re.IGNORECASE)
    
    def _citation_formatter(self, parent, close=False, **kwargs):
        if not close:
            lang = parent.secondary_language()
            langattr = lang and ' lang="%s"' % lang or ''
            return '<span%s class="citation">' % langattr
        else:
            return '</span>'
    
    def _link_formatter(self, parent, title=None, href=None, anchor=None,
                        resource_cls=None, close=False, **kwargs):
        node = None
        if resource_cls:
            cls = globals()[resource_cls]
            resource = parent.resource(cls, href, fallback=False)
            if resource:
                return '<a href="%s">%s</a>' % (resource.uri(), title or href)
            else:
                log("%s: Unknown resource: %s" % (parent.id(), href))
        elif not href:
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
            if self._IMAGE_URI_MATCHER.search(href):
                return _html.img(href, alt=title or '')
            else:
                target = Link.ExternalTarget(href, title or href)
        if title:
            maybeimg = title.split(' ')[0]
            if self._IMAGE_URI_MATCHER.search(maybeimg):
                title = _html.img(maybeimg, alt=title[len(maybeimg)+1:] or '')
        l = Link(target, label=title)
        l.set_parent(parent)
        return l.export(self._exporter)
    
    def _uri_formatter(self, parent, uri, close=False, **kwargs):
        return self._link_formatter(parent, href=uri, title=None)

    def _email_formatter(self, parent, email, close=False, **kwargs):
        return self._link_formatter(parent, href='mailto:'+email, title=email)

    
class HtmlExporter(Exporter):
    DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'
    _BODY_PARTS = ('heading',
                   'language_selection',
                   'content',
                   )
    _LANGUAGE_SELECTION_LABEL = _("Choose your language:")
    
    def __init__(self, stylesheet=None, inlinestyles=False, **kwargs):
        """Initialize the exporter for a given 'ContentNode' instance."""
        self._stylesheet = stylesheet
        self._inlinestyles = inlinestyles
        self._formatter = HtmlMarkupFormatter(self)
        super(HtmlExporter, self).__init__(**kwargs)
    
    def _backref(self, node, target):
        # We can allow just one backref target on the page.  Links on other
        # pages are not backreferenced.
        return None
        
        if node is target.parent() and not self._backref_used.has_key(target):
            self._backref_used[target] = True
            return "backref-" + target.anchor()
        else:
            return None
    
    def _output_file(self, node, lang=None):
        """Return full pathname of node's output file relative to export dir."""
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
    
    def _section_header(self):
        if self._backref_used[target]:
            href = "#"+self._backref()
        else:
            href = None
        return _html.h(_html.link(self.title(), href, cls='backref',
                                  name=self.anchor()),
                           len(self._section_path())+1)+'\n'
               
    def _export_section(self):
        return "\n".join((self._section_header(),
                          super(Section, self).export(self)))

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
            r = node.resource(Stylesheet, self._stylesheet)
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
        x = [(getattr(self, '_'+part)(node), part.replace('_', '-'))
             for part in parts]
        return concat([self._part(part, name)
                       for part, name in x if part is not None],
                      separator="\n")
    
    def _part(self, part, name):
        return _html.div(part, cls=name)
        
    def _heading(self, node):
        return concat('<h1>', node.title(), '</h1>')

    def _language_selection(self, node):
        #handler = "location.href = this.form.language.options[this.form.language.selectedIndex].value"
        #select = _html.form((_html.label(self._label, 'language-selection'),
        #                     _html.select('language',
        #                                  [(t.title(), t.url())
        #                                   for t in self._targets],
        #                                  id='language-selection',
        #                                  selected=self._current.url()),
        #                     _html.button(_('Switch'), handler)),
        #                    cls='language-selection')
        #radio = _html.fieldset([_html.radio('language', value=t.url(), id=tid,
        #                                    onclick="location.href = this.value",
        #                                    checked=(self._current.url()==t.url())
        #                                    ) + \
        #                        _html.label(flag.export(exporter) + t.title(), tid)
        #                        for t, tid, flag in
        #                        [(t, t.url().replace('.','-'), f)
        #                         for t, f in zip(self._targets, self._flags)]],
        #                       legend=self._label, cls='language-selection')
        if node is not node.root() or len(node.language_variants()) <= 1:
            return None
        current = node.current_language_variant()
        languages = list(node.language_variants()[:])
        languages.sort()
        links = []
        for lang in languages:
            name = language_name(lang)
            cls = None
            if lang == current:
                name = concat(name, _html.span(' *', cls='hidden'))
                cls = 'current'
            uri = self._node_uri(node, lang=lang)
            links.append(_html.link(name, uri, cls=cls))
            #flag = InlineImage(node.resource(Image, 'flags/%s.gif' % lang))
        return concat(self._LANGUAGE_SELECTION_LABEL, "\n",
                      concat(links, separator=" |\n"))

    def _content(self, node):
        return node.content().export(self)
    
    def format_wiki_text(self, parent, text):
        """Format text with wiki markup and return HTML."""
        if text:
            return self._formatter.format(parent, text)
        else:
            return ''
    
    def page(self, node):
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
    
    def export(self, node, directory):
        if not os.path.isdir(directory):
            os.makedirs(directory)
        filename = os.path.join(directory, self._output_file(node))
        file = open(filename, 'w')
        file.write(self.translate(self.page(node)).encode('utf-8'))
        file.close()
        for r in node.resources():
            r.export(directory)
        for n in node.children():
            self.export(n, directory)


class HtmlStaticExporter(HtmlExporter):
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

    def _rule(self, node):
        return '<hr class="hidden">'
    
    def _navigation(self, node):
        def link(node, label=None, key=None):
            if node:
                if label is None:
                    label = node.title(brief=True)
                return  _html.link(label, self.uri(node), title=node.title(),
                                   hotkey=not key or self._hotkey[key])
            else:
                return _("None")
        if len(node.root().linear()) <= 1:
            return None
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
