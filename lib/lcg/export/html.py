# -*- coding: utf-8 -*-
#
# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2009 Brailcom, o.p.s.
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

_ = TranslatableTextFactory('lcg')

class HtmlGenerator(Generator):
    #DOCTYPE = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
    _DOCTYPE = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'

    def _attr(self, valid, **kwargs):
        result = ''
        #if kwargs.get('lang'):
        #    kwargs['style'] = 'color: red;' + (kwargs.get('style') or '')
        for name in valid + ('id', 'lang', 'tabindex', 'cls', 'style'):
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
                    value = '"%d"' % value
                elif isinstance(value, Localizable):
                    value = value.transform(saxutils.quoteattr)
                else:
                    value = saxutils.quoteattr(value)
                result += ' ' + name + '=' + value
        assert not kwargs, "Invalid attributes: %s" % kwargs
        return result

    def _tag(self, tag, content=None, _attr=(), _newlines=False, _paired=True, **kwargs):
        separator = _newlines and "\n" or ""
        start = '<' + tag + self._attr(_attr, **kwargs) + '>' + separator
        if not _paired:
            assert content is None
            return start
        else:
            assert content is not None
            end = '</' + tag + '>' + separator
            if isinstance(content, (tuple, list)):
                content = concat(content, separator=separator)
            if _newlines and not content.endswith('\n'):
                end = separator + end
            return concat(start, content, end)
     
    def _input(self, type, _attr=(), **kwargs):
        attr = ('type', 'name', 'value', 'title', 'size', 'maxlength', 'accesskey',
                'onclick', 'onmousedown', 'onmouseup', 'onkeydown', 'onkeypress', 'onchange',
                'readonly', 'disabled')
        return self._tag('input', _attr=attr+_attr, _paired=False, type=type, **kwargs)

    # Generic constructs
     
    def escape(self, text):
        return saxutils.escape(text)

    def heading(self, title, level, anchor=None, backref=None):
        if anchor or backref:
            if backref:
                backref = "#" + backref
            content = self.link(title, backref, name=anchor, cls='backref')
        else:
            content = title
        return self.h(content, level)
        
    def strong(self, text, **kwargs):
        return self._tag('strong', text, **kwargs)
     
    def pre(self, text, cls="lcg-preformatted-text", **kwargs):
        return self._tag('pre', text, _newlines=True, cls=cls, **kwargs)
     
    def sup(self, text, **kwargs):
        return self._tag('sup', text, **kwargs)
    
    def sub(self, text, **kwargs):
        return self._tag('sub', text, **kwargs)
    
    def p(self, *content, **kwargs):
        return self._tag('p', content, _newlines=True, **kwargs)
     
    def br(self, **kwargs):
        return self._tag('br', _paired=False, **kwargs)
     
    def hr(self, **kwargs):
        return self._tag('hr', _paired=False, **kwargs)
     
    def link(self, label, uri, title=None, target=None, hotkey=None, cls=None, **kwargs):
        if hotkey and title:
            title += ' (%s)' % hotkey
        if target:
            cls = (cls and cls+' ' or '') + 'external-link'
        attr = ('href', 'type', 'name', 'title', 'target', 'accesskey')
        return self._tag('a', label, attr, href=uri, title=title, target=target,
                         accesskey=hotkey, cls=cls, **kwargs)

    def anchor(self, label, name):
        return self.link(label, None, name=name)

    def li(self, content, **kwargs):
        return self._tag('li', content, **kwargs)
    
    def ol(self, *content, **kwargs):
        return self._tag('ol', content, **kwargs)
    
    def ul(self, *content, **kwargs):
        return self._tag('ul', content, **kwargs)
    
    def list(self, items, indent=0, ordered=False, style=None, **kwargs):
        spaces = ' ' * indent
        items = [concat(spaces, '  ', self.li(i), '\n') for i in items]
        tag = ordered and self.ol or self.ul
        style = style and 'list-style-type: %s' % style
        return spaces + tag(concat('\n', items, spaces), style=style, **kwargs)+'\n'

    def definitions(self, items, **kwargs):
        content = [self._tag('dt', dt) + self._tag('dd', dd) for dt, dd in items]
        return self._tag('dl', content, _newlines=True, **kwargs)

    def fset(self, items, **kwargs):
        return self.table([self.tr((self.th(name, valign="top", align="left"),
                                    self.td(value)))
                           for name, value in items],
                          cls='lcg-fieldset', **kwargs)
     
    def img(self, src, alt='', border=0, descr=None, **kwargs):
        attr = ('src', 'alt', 'longdesc', 'width', 'height', 'align', 'border')
        return self._tag('img', _attr=attr, _paired=False, src=src, alt=alt, border=border, **kwargs)

    def toc(self, context, item, indent=0, depth=1):
        pass

    def abbr(self, term, **kwargs):
        return self._tag('abbr', term, ('title',), **kwargs)

    def gtable(self, rows, title=None, cls='lcg-table', **kwargs):
        content = [self.tr([self.td(cell) for cell in row]) for row in rows]
        if title:
            content = ["<caption>"+ title +"</caption>"] + content
        return self.table(self.tbody(content), cls=cls, **kwargs)

    # HTML specific...

    def html(self, content, lang=None):
        return concat(self._DOCTYPE, '\n\n',
                      self._tag('html', concat(content), _newlines=True, lang=lang))
    
    def head(self, tags):
        content = concat('  ', concat(tags, separator='\n  ')),
        return self._tag('head', content, _newlines=True)
    
    def body(self, content, **kwargs):
        return self._tag('body', content, ('onkeydown', 'onload'), _newlines=True, **kwargs)
    
    def uri(self, base, *args, **kwargs):
        uri = urllib.quote(base.encode('utf-8'))
        query = ';'.join([k +'='+ urllib.quote(unicode(v).encode('utf-8'))
                          for k,v in args + tuple(kwargs.items()) if v is not None])
        if query:
            uri += '?' + query
        return uri
     
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
    
    def h(self, title, level, **kwargs):
        return self._tag('h%d' % level, title, **kwargs) + '\n'
    
    def span(self, text, **kwargs):
        return self._tag('span', text, ('title',), **kwargs)
     
    def div(self, content, **kwargs):
        return self._tag('div', content, ('title',), _newlines=True, **kwargs)
     
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
        return self._input('radio', _attr=('checked',), name=name, **kwargs)
     
    def hidden(self, name, value, id=None):
        return self._input('hidden', name=name, value=value, id=id)
     
    def button(self, content=None, label=None, cls=None, **kwargs):
        if content is None:
            cls = cls and 'button ' + cls or 'button'
            return self._input('button', value=label, cls=cls, **kwargs)
        else:
            attr = ('value', 'onclick', 'name', 'cls', 'disabled', 'title')
            return self._tag('button', content, attr, title=label, cls=cls, **kwargs)
     
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
     
    def iframe(self, src, **kwargs):
        attr = ('src', 'width', 'height', 'frameborder')
        return self._tag('iframe', self.link(src, src), attr, src=src, **kwargs)
     
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
    
class HtmlFormatter(MarkupFormatter):
    
    _FORMAT = {'emphasize': ('<em>', '</em>'),
               'strong': ('<strong>', '</strong>'),
               'fixed': ('<tt>', '</tt>'),
               'underline': ('<span class="underline">', '</span>'),
               'citation': ('<span class="citation">', '</span>'),
               'quotation': (u'“<span class="quotation">', u'</span>”'),
               'comment': '',
               'linebreak': '<br>',
               'dash': '&ndash;',
               'nbsp': '&nbsp;'}
    
    def _citation_formatter(self, context, close=False, **kwargs):
        if not close:
            lang = context.sec_lang()
            langattr = lang and ' lang="%s"' % lang or ''
            return '<span%s class="citation">' % langattr
        else:
            return '</span>'

    def _email_formatter(self, context, email, close=False, **kwargs):
        return self._link_formatter(context, href='mailto:'+email, label=email)

    
class HtmlExporter(Exporter):
    Generator = HtmlGenerator
    Formatter = HtmlFormatter

    class Context(Exporter.Context):
        def __init__(self, *args, **kwargs):
            super(HtmlExporter.Context, self).__init__(*args, **kwargs)
            self._shared_player_controls = []
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
    
    def _title(self, context):
        return context.node().title()

    def _meta(self, context):
        import lcg
        return (('generator', 'LCG %s (http://www.freebsoft.org/lcg)' % lcg.__version__),)
    
    def _head(self, context):
        node = context.node()
        return [concat('<title>', self._title(context), '</title>')] + \
               ['<meta http-equiv="%s" content="%s">' % pair
                for pair in (('Content-Type', 'text/html; charset=UTF-8'),
                             ('Content-Language', context.lang()),
                             ('Content-Script-Type', 'text/javascript'),
                             ('Content-Style-Type', 'text/css'))] + \
               ['<meta name="%s" content="%s">' % pair for pair in self._meta(context)] + \
               ['<link rel="alternate" lang="%s" href="%s">' % \
                (lang, self._uri_node(context, node, lang=lang))
                for lang in node.variants() if lang != context.lang()] + \
               ['<script language="Javascript" type="text/javascript"' + \
                ' src="%s"></script>' % context.uri(s) for s in node.resources(Script)]

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
            links.append(g.link(label, self._uri_node(context, node, lang=lang), cls=cls)+sign)
        return concat(g.link(self._LANGUAGE_SELECTION_LABEL, None,
                             id='language-selection-anchor', name='language-selection-anchor'),
                      "\n", concat(links, separator=" "+g.span('|', cls='sep')+"\n"))

    def _language_selection_image(self, context, lang):
        #return context.uri(context.resource('flags/%s.gif' % lang))
        return None
    
    def _content(self, context):
        return context.node().content().export(context)

    def export_swf_object(self, context, filename, element_id, width, height,
                          vars={}, min_flash_version=None, alternative_content=None):
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
          vars -- dictionary of variables to pass to the flash object (through SWFObject's
            'flashvars' parameter).
          min_flash_version -- minimal required Flash version as a string, such
            as '9' or '9.0.25'
          alternative_content -- HTML content (as a string or unicode) displayed inside the
            HTML element when Flash or JavaScript don't work on the client side
            (Flash not installed or its version doesn't match
            'min_flash_version', JS is disabled or not supoported, ...).  You
            may also pass a tuple of two strings in which case the first is
            used when flash doesn't work and the second when the problem is in
            JavaScript.  You may think of using 'self._flash_warnings()' to get
            decent warning messages for this argument.
        
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
        g = context.generator()
        flashvars = '&'.join(['='.join((name, escape(value)))
                              for name, value in vars.items()])
        if isinstance(alternative_content, tuple):
            no_flash_content, no_js_content = alternative_content
            no_flash_content = context.translate(no_flash_content)
        else:
            no_flash_content = None
            no_js_content = alternative_content
        # Here we first create a DIV containing error text about js not
        # working, then a javascript code that replaces this error message with
        # the flash object when page is loaded into browser and js is working.
        return (g.div(no_js_content or '', id=element_id) + 
                g.script(g.js_call('embed_swf_object', context.uri(flash_object), element_id,
                                   width, height, flashvars, min_flash_version, no_flash_content)))

    def _flash_warnings(self, context, warning, min_flash_version=None):
        # Translators: '%(plugin)s' is automatically replaced by a hypertext
        # link to Adobe Flash plugin download page.  '%(version)s' is replaced
        # by the required version number or an empty string if no version was
        # required.
        g = context.generator()
        flash_msg = _("Get %(plugin)s %(version)s or later.",
                      version=min_flash_version or '',
                      # Translators: Title of the link to Adobe website used in the Flash warning.
                      plugin=g.link(_("Adobe Flash plugin"),
                                    'http://www.adobe.com/products/flash/about/'))
        return (g.strong(_("Warning:")) +' '+ warning +' '+ flash_msg,
                g.strong(_("Warning:")) +' '+ warning +' '+ _("Use a JavaScript enabled browser."))
    
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
        g = context.generator()
        min_flash_version = '9.0.115'
        warnings = self._flash_warnings(context, _("Media Player unavailable."), min_flash_version)
        result = self.export_swf_object(context, 'mediaplayer.swf', player_id, width, height,
                                        min_flash_version=min_flash_version,
                                        alternative_content=warnings)
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
            g = context.generator()
            player_id = 'shared-audio-player'
            # export_media_player() returns None if one of the dependencies is not found...
            content = self.export_media_player(context, player_id, 300, 20, shared=True)
            if content:
                for args in controls:
                    content += "\n"+ g.script(g.js_call('init_player_controls', player_id, *args))
            return content
        else:
            return None

    def export_inline_audio(self, context, audio, title=None, descr=None, image=None, shared=True):
        """Export emedded audio player for given audio file.

        Inline audio can be rendered as a simple link which controls a shared
        Flash audio player (usually located in the bottom right corner of a
        webpage) or using a standalone Flash audio player located directly
        inside page content in place of the link.  In both cases, if Flash or
        Javascript is not available, a simple link without a player is rendered
        allowing just downloading the audio file.

        Arguments are described in parent class method.
        
        """
        if shared:
            g = context.generator()
            uri = context.uri(audio)
            link_id = '%x' % positive_id(audio)
            context.connect_shared_player(uri, link_id)
            if image:
                label = g.img(context.uri(image), alt=title)
                descr = descr or title
            else:
                label = title or audio.title()
            return g.link(label, uri, id=link_id, title=descr, cls='media-control-link')
        else:
            raise NotImplementedError
        
    def export_inline_video(self, context, video, title=None, descr=None, image=None, size=None):
        """Export emedded video player for given video file.

        The 'Video' resource instance is rendered as a standalone Flash video
        player preloaded with given video.  If Flash or Javascript is not
        available, only a link to the video file is rendered.

        Arguments are described in parent class method.
        
        """
        g = context.generator()
        if size is None:
            width, height = (200, 200)
        else:
            width, height = size
        uri = context.uri(video)
        title = title or video.title()
        descr = descr or video.descr()
        link = g.link(title, uri, title=descr)
        player = self.export_swf_object(context, 'mediaplayer.swf', '%x' % positive_id(video),
                                        width, height, min_flash_version='9.0.115',
                                        vars=dict(file=uri, title=title, description=descr,
                                                  image=(image and context.uri(image))),
                                        alternative_content=link)
        return g.div(player or link, cls='video-player')
        
    def _initialize(self, context):
        return ''

    def _body_attr(self, context, **kwargs):
        return kwargs
    
    def _body_content(self, context):
        return self._parts(context, self._BODY_PARTS)
    
    def export(self, context):
        g = context.generator()
        # Export body first to allocate all resources before generating the head.
        body = self._body_content(context)
        attr = self._body_attr(context)
        parts = (g.head(self._head(context)),
                 g.body(body, **attr))
        return g.html(parts, lang=context.lang())


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

    def _head(self, context):
        for style in self._styles:
            context.resource(style)
        styles = context.node().resources(Stylesheet)
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
                            hidden = g.link('', self.uri(context, target),
                                            hotkey=self._hotkey['up'], cls='hidden')
                    elif target == parent:
                        key = 'up'
                return g.link(label, self.uri(context, target), title=target.title(),
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
        
