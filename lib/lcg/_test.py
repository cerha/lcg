#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2004-2017 BRAILCOM, o.p.s.
# Copyright (C) 2019 Tomáš Cerha <t.cerha@gmail.com>
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

from __future__ import unicode_literals
from __future__ import division
from __future__ import print_function
from future import standard_library
from builtins import zip
from builtins import range

import datetime
import io
import os
import re
import string
import sys
import unittest
import zipfile
import pytest

import lcg

_ = lcg.TranslatableTextFactory('test')
standard_library.install_aliases()
unistr = type(u'')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


lcg_dir = os.path.normpath(os.path.join(__file__, '..', '..', '..'))
os.environ['LCGDIR'] = lcg_dir
translation_path = [os.path.join(lcg_dir, 'translations')]


class TranslatableText(unittest.TestCase):

    def test_interpolation(self):
        a = lcg.TranslatableText("Hi %s, say hello to %s.", "Joe", "Bob")
        b = lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.",
                                 person1="Joe", person2="Bob")
        c0 = lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.")
        c = c0.interpolate(lambda key: '-' + key + '-')
        a1 = a.localize(lcg.Localizer())
        b1 = b.localize(lcg.Localizer())
        c1 = c.localize(lcg.Localizer())
        assert a1, "Hi Joe, say hello to Bob."
        assert b1, "Hi Joe, say hello to Bob."
        assert c1, "Hi -person1-, say hello to -person2-."

    def test_addition(self):
        a = lcg.TranslatableText("Version %s", "1.0")
        b = "xxx"
        c = a + b
        assert isinstance(c, lcg.Concatenation)
        assert c == "Version 1.0xxx"
        d = c + b
        assert isinstance(d, lcg.Concatenation)
        e = b + a
        assert isinstance(e, lcg.Concatenation)
        assert e == "xxxVersion 1.0"
        f = b + c
        assert isinstance(f, lcg.Concatenation)
        assert f == "xxxVersion 1.0xxx"
        try:
            e = a + 1
        except TypeError as e:
            pass
        assert isinstance(e, TypeError)

    def test_concat(self):
        a = lcg.concat(lcg.TranslatableText("Version %s", "1.0") + 'xx', 'yy', separator="\n")
        assert isinstance(a, lcg.Concatenation)
        items = a.items()
        assert len(items) == 2
        assert items[1] == ('xx\nyy')
        b = lcg.concat('a', ('b', 'c', 'd'), 'e', 'f', separator='-')
        assert isinstance(b, unistr)
        assert b == 'a-b-c-d-e-f'
        c = lcg.concat('a', (u'b', 'c', 'd'), 'e', 'f', separator='-')
        assert isinstance(c, unistr)
        assert c == 'a-b-c-d-e-f'

    def test_replace(self):
        t = lcg.TranslatableText("Version %s", "xox")
        a = t + '-yoy'
        b = t.replace('o', '-')
        c = a.replace('o', '-')
        d = c.replace('V', 'v')
        assert isinstance(a, lcg.Concatenation)
        assert isinstance(b, lcg.TranslatableText)
        assert isinstance(c, lcg.Concatenation)
        assert isinstance(d, lcg.Concatenation)
        ax = a.localize(lcg.Localizer())
        bx = b.localize(lcg.Localizer())
        cx = c.localize(lcg.Localizer())
        dx = d.localize(lcg.Localizer())
        assert unistr(a) == ax == 'Version xox-yoy', (a, ax)
        assert unistr(b) == bx == 'Versi-n x-x', (b, bx)
        assert unistr(c) == cx == 'Versi-n x-x-y-y', (c, cx)
        assert unistr(d) == dx == 'versi-n x-x-y-y', (d, dx)

    def test_translate(self):
        cs = lcg.Localizer('cs', translation_path=translation_path)
        a = _('His name is "%s"', _("Bob"))
        assert a.localize(cs) == 'Jmenuje se "Bobik"'
        assert str(a) == 'His name is "Bob"'
        b = _("Bob") + ' + ' + _("Joe")
        assert str(b) == 'Bob + Joe'
        assert b.localize(cs) == 'Bobik + Pepa'

    def test_transform(self):
        from xml.sax import saxutils
        cs = lcg.Localizer('cs', translation_path=translation_path)
        a = _('His name is "%s"', _("Bob")).transform(saxutils.quoteattr)
        assert isinstance(a, lcg.TranslatableText)
        assert str(a) == '\'His name is "Bob"\''
        assert a.localize(cs) == '\'Jmenuje se "Bobik"\''
        b = _("Bob") + ' + ' + _("Joe")
        c = b.transform(saxutils.quoteattr)
        assert isinstance(c, lcg.Concatenation)
        assert str(c) == '"Bob + Joe"'
        assert c.localize(cs) == '"Bobik + Pepa"'
        attr = "attr=" + c  # Test transformed Concatenation nesting!
        assert str(attr) == 'attr="Bob + Joe"'
        assert attr.localize(cs) == 'attr="Bobik + Pepa"'
        tag = lcg.concat('<tag ' + attr + '>')
        assert str(tag) == '<tag attr="Bob + Joe">'
        assert tag.localize(cs) == '<tag attr="Bobik + Pepa">'

    def test_pgettext(self):
        cs = lcg.Localizer('cs', translation_path=translation_path)
        assert _.pgettext('dont translete this msg', 'untranslated').localize(cs) == 'untranslated'
        assert _.pgettext('verb', 'force').localize(cs) == 'donutit'
        assert _.pgettext('noun', 'force').localize(cs) == u'síla'

    def test_string_context(self):
        a = lcg.TranslatableText("Version %s", "1.0")
        assert a == "Version 1.0"
        b = lcg.TranslatableText("Info: %s", a)
        assert b == "Info: Version 1.0"
        c = lcg.concat("Info:", lcg.concat(a, '2006-08-14', separator=', '),
                       ('Mon', '10:32'), separator=' ')
        assert c == "Info: Version 1.0, 2006-08-14 Mon 10:32"

    def test_html_escaping(self):
        def test(src, expected_result, escaped=True):
            result = src.localize(lcg.Localizer())
            assert result == expected_result
            if escaped:
                assert isinstance(result, lcg.HtmlEscapedUnicode)
            else:
                assert not isinstance(result, lcg.HtmlEscapedUnicode)

        g = lcg.HtmlExporter.Generator()
        a = lcg.TranslatableText("Hi %s, say hello to %s.", g.strong("Joe"), g.strong("Bob"))
        test(a,
             'Hi <strong>Joe</strong>, say hello to <strong>Bob</strong>.')
        test(lcg.format('<a href=%s>%s</a>', 'http://www.freebsoft.org', a, escape_html=False),
             '<a href=http://www.freebsoft.org>Hi <strong>Joe</strong>, '
             'say hello to <strong>Bob</strong>.</a>')
        test(lcg.format('<%s>', a),
             '&lt;Hi <strong>Joe</strong>, say hello to <strong>Bob</strong>.&gt;')
        test(g.div(lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.")
                   .interpolate(lambda x: g.span(x.upper()))),
             '<div>Hi <span>PERSON1</span>, say hello to <span>PERSON2</span>.</div>')
        test(lcg.format('%s -> %s', 'x', 'y', escape_html=True),
             'x -&gt; y')
        test(lcg.format('%s', 'x'), 'x', escaped=False)
        link = lcg.format('<a href="%s">%d</a>', 'x', 1, escape_html=False)
        test(link, '<a href="x">1</a>')
        post = _("post #%s", link)
        test(post, 'post #<a href="x">1</a>')
        test(lcg.format('<span>%s</span>', post, escape_html=False),
             '<span>post #<a href="x">1</a></span>')
        # Test a specific case of pytis.web.ItemizedView export
        template = lcg.TranslatableText("%(a)s [%(b)s]")
        fields = dict(a=g.a(lcg.TranslatableText("a"), href='a'), b='b')
        interpolated = template.interpolate(lambda f: fields[f])
        test(interpolated, '<a href="a">a</a> [b]')


class TranslatablePluralForms(unittest.TestCase):

    def test_translation(self):
        loc = lcg.Localizer('cs', translation_path=translation_path)
        for n, translated in ((1, u"Mám 1 problém."),
                              (2, u"Mám 2 problémy."),
                              (5, u"Mám 5 problémů.")):
            a = _.ngettext("I have %d problem.", "I have %d problems.", n)
            b = a.localize(loc)
            assert b == translated

    def test_interpolation(self):
        t = lcg.Localizer('cs', translation_path=translation_path)
        for n, translated in ((1, u"1 záznam nalezen v tabulce xy."),
                              (2, u"2 záznamy nalezeny v tabulce xy."),
                              (5, u"5 záznamů nalezeno v tabulce xy.")):
            a = _.ngettext("%(n)d record found in table %(name)s.",
                           "%(n)d records found in table %(name)s.", n=n, name='xy')
            b = a.localize(t)
            assert b == translated

    def test_replace(self):
        loc = lcg.Localizer('cs', translation_path=translation_path)
        for n, ta, tb in ((1, u"Mám 1 problém.", u"1 záznam nalezen v tabulce xy."),
                          (2, u"Mám 2 problémy.", u"2 záznamy nalezeny v tabulce xy."),
                          (5, u"Mám 5 problémů.", u"5 záznamů nalezeno v tabulce xy.")):
            a = _.ngettext("I have %d problem.", "I have %d problems.", n)
            a1 = a.replace('5', '123')
            a2 = a1.localize(loc)
            ta1 = ta.replace('5', '123')
            assert a2 == ta1
            b = _.ngettext("%(n)d record found in table %(name)s.",
                           "%(n)d records found in table %(name)s.", n=n, name='xy')
            b1 = b.replace('5', '123')
            b2 = b1.localize(loc)
            tb1 = tb.replace('5', '123')
            assert b2 == tb1


class SelfTranslatableText(unittest.TestCase):

    def test_interpolation(self):
        text = "%(person1)s is smarter than %(person2)s."
        translations = {'cs': u"%(person1)s je chytřejší než %(person2)s."}
        a = lcg.SelfTranslatableText(text, person1="Joe", person2="Ann", translations=translations)
        a2 = lcg.SelfTranslatableText(text, translations=translations)
        a3 = a2.interpolate(lambda key: '-' + key + '-')
        assert a.localize(lcg.Localizer()) == \
            "Joe is smarter than Ann."
        assert a.localize(lcg.Localizer('cs', translation_path=translation_path)) == \
            u"Joe je chytřejší než Ann."
        assert a3.localize(lcg.Localizer()) == \
            "-person1- is smarter than -person2-."
        assert a3.localize(lcg.Localizer('cs', translation_path=translation_path)) == \
            u"-person1- je chytřejší než -person2-."


class LocalizableDateTime(unittest.TestCase):

    class tzinfo(datetime.tzinfo):

        def __init__(self, offset):
            self._offset = offset

        def utcoffset(self, dt):
            return datetime.timedelta(minutes=self._offset)

        def tzname(self, dt):
            offset = self._offset
            sign = offset // abs(offset)
            div, mod = divmod(abs(offset), 60)
            if mod:
                return "GMT %+d:%d" % (div * sign, mod)
            else:
                return "GMT %+d" % div * sign

        def dst(self, dt):
            return datetime.timedelta(0)

    def test_localize(self):
        en = lcg.Localizer('en', translation_path=translation_path)
        cs = lcg.Localizer('cs', translation_path=translation_path, timezone=self.tzinfo(-60))
        utc = lcg.LocalizableDateTime._UTC_TZ

        def localize(dt, localizer, **kwargs):
            return lcg.LocalizableDateTime(dt, **kwargs).localize(localizer)

        assert (localize("2006-12-21", en)
                == "21/12/2006")
        assert (localize(datetime.date(2006, 12, 21), en)
                == "21/12/2006")
        assert (localize("2006-12-21 02:43", en, show_time=False)
                == "21/12/2006")
        assert (localize("2006-12-21 02:43", en, show_time=False, utc=True)
                == "21/12/2006 UTC")
        assert (localize(datetime.datetime(2006, 12, 21, 2, 43), en, show_time=False)
                == "21/12/2006")
        assert (localize(datetime.datetime(2006, 12, 21, 2, 43, tzinfo=utc), en, show_time=False)
                == "21/12/2006 UTC")
        assert (localize("2006-12-21 02:43", en)
                == "21/12/2006 02:43 AM")
        assert (localize(datetime.datetime(2006, 12, 21, 2, 43), en, show_seconds=False)
                == "21/12/2006 02:43 AM")
        assert (localize("2006-12-21 18:43:32", en, show_weekday=True)
                == "Thu 21/12/2006 06:43:32 PM")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32), en, show_weekday=True)
                == "Thu 21/12/2006 06:43:32 PM")
        assert (localize("2006-01-30", en, leading_zeros=False)
                == "30/1/2006")
        assert (localize(datetime.date(2006, 1, 30), en, leading_zeros=False)
                == "30/1/2006")
        assert (localize("2006-12-21 18:43:32", en, utc=True)
                == "21/12/2006 06:43:32 PM UTC")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32), en)
                == "21/12/2006 06:43:32 PM")
        assert (localize("2006-12-21", cs)
                == "21.12.2006")
        assert (localize(datetime.date(2006, 12, 21), cs)
                == "21.12.2006")
        assert (localize("2006-12-21 02:43", cs, show_time=False)
                == "21.12.2006")
        assert (localize(datetime.datetime(2006, 12, 21, 2, 43, tzinfo=utc), cs, show_time=False)
                == "21.12.2006")
        assert (localize("2006-12-21 02:43", cs)
                == "21.12.2006 02:43")
        assert (localize("2006-12-21 02:43", cs, utc=True)
                == "21.12.2006 01:43")
        assert (localize(datetime.datetime(2006, 12, 21, 2, 43, tzinfo=utc), cs, show_seconds=False)
                == "21.12.2006 01:43")
        assert (localize("2006-12-21 18:43:32", cs, show_weekday=True)
                == u"Čt 21.12.2006 18:43:32")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32), cs)
                == u"21.12.2006 18:43:32")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32, tzinfo=utc), cs)
                == u"21.12.2006 17:43:32")
        assert (localize("2006-01-30", cs, leading_zeros=False)
                == "30.1.2006")
        assert (localize(datetime.date(2006, 1, 30), cs, leading_zeros=False)
                == "30.1.2006")
        assert (localize("2006-12-21 18:43:32", cs, utc=True)
                == u"21.12.2006 17:43:32")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32), cs, utc=True)
                == u"21.12.2006 17:43:32")

    def test_concat(self):
        c = "Date is: " + lcg.LocalizableDateTime("2006-01-30")
        assert c.localize(lcg.Localizer('en', translation_path=translation_path)) == \
            "Date is: 30/01/2006"
        assert c.localize(lcg.Localizer('cs', translation_path=translation_path)) == \
            "Date is: 30.01.2006"

    def test_replace(self):
        a = lcg.LocalizableDateTime("2006-01-30")
        en = lcg.Localizer('en', translation_path=translation_path)
        cs = lcg.Localizer('cs', translation_path=translation_path)
        b = a.replace('-', '+')
        assert unistr(b) == "2006+01+30"
        assert b.localize(en) == "30/01/2006"
        assert b.localize(cs) == "30.01.2006"
        c = a.replace('/', '|')
        assert unistr(c) == "2006-01-30"
        assert c.localize(en) == "30|01|2006"
        assert c.localize(cs) == "30.01.2006"
        d = a.replace('.', ':')
        assert unistr(d) == "2006-01-30"
        assert d.localize(en) == "30/01/2006"
        assert d.localize(cs) == "30:01:2006"


class LocalizableTime(unittest.TestCase):

    def test_format(self):
        t1 = lcg.LocalizableTime("02:43")
        t2 = lcg.LocalizableTime("18:43:32")
        cs = lcg.Localizer('cs', translation_path=translation_path)
        no = lcg.Localizer('no', translation_path=translation_path)
        assert t1.localize(cs) == "02:43"
        assert t2.localize(cs) == "18:43:32"
        assert t1.localize(no) == "02.43"
        assert t2.localize(no) == "18.43.32"


class TranslatableTextFactory(unittest.TestCase):

    def test_domain(self):
        a = _("%(name1)s is smarter than %(name2)s.", name1=_("Joe"), name2=_("Bob"))
        assert a.domain() == 'test'


class Monetary(unittest.TestCase):

    def test_format(self):
        a = lcg.Monetary(8975.5)
        a1 = lcg.Localizer().localize(a)
        a2 = lcg.Localizer('cs').localize(a)
        a3 = lcg.Localizer('en').localize(a)
        assert a1 == '8975.50'
        assert a2 == u'8\xa0975,50'
        assert a3 == '8,975.50'

    def test_precision(self):
        loc = lcg.Localizer()
        assert loc.localize(lcg.Monetary(8975.5, precision=0)) == '8976'
        assert loc.localize(lcg.Monetary(8975.5, precision=3)) == '8975.500'

    def test_transform(self):
        loc = lcg.Localizer()
        amount = lcg.Monetary(8975.5, precision=2)
        assert loc.localize(amount) == '8975.50'
        assert loc.localize(amount.transform(lambda x: x.replace('.', ','))) == '8975,50'


class GettextTranslator(unittest.TestCase):

    def test_translate(self):
        t = lcg.Localizer('cs', translation_path=translation_path).translator()
        assert t.gettext("%(name1)s is smarter than %(name2)s.", domain='test') == \
            u"%(name1)s je chytřejší než %(name2)s."


class ContentNode(unittest.TestCase):

    def test_node_structure(self):
        d = lcg.ContentNode('d')
        c = lcg.ContentNode('c', children=(d,))
        b = lcg.ContentNode('b')
        a = lcg.ContentNode('a', children=(b, c))
        assert a.id() == 'a'
        assert a.root() is b.root()
        assert c.root() is a
        assert d.root() is a
        assert b.next() is c
        assert b.prev() is a
        assert d.path() == (a, c, d)
        assert b.path() == (a, b)
        assert a.linear() == [a, b, c, d]
        assert b.linear() == [b]
        assert c.linear() == [c, d]

    def test_variants(self):
        n = lcg.ContentNode(
            'n', content=lcg.TextContent("C"),
            first_page_header=lcg.TextContent("FH"),
            right_page_footer=lcg.TextContent("RF"),
            page_background=lcg.TextContent("B"),
            variants=(
                lcg.Variant('en', content=lcg.TextContent('EN'),
                            page_header=lcg.TextContent('H.EN')),
                lcg.Variant('cs', content=lcg.TextContent('CS'),
                            page_footer=lcg.TextContent('F.CS'),
                            right_page_footer=lcg.TextContent('RF.CS')),
            ),
        )
        assert n.content('en').text() == 'EN'
        assert n.content('cs').text() == 'CS'
        assert n.content('fr').text() == 'C'
        assert n.first_page_header('en').text() == 'FH'
        assert n.first_page_header('cz').text() == 'FH'
        assert n.page_header('en').text() == 'H.EN'
        assert n.page_footer('en') is None
        assert n.right_page_footer('en').text() == 'RF'
        assert n.page_header('cs') is None
        assert n.page_footer('cs').text() == 'F.CS'
        assert n.right_page_footer('cs').text() == 'RF.CS'
        assert n.page_header('fr') is None
        assert n.page_background('en').text() == 'B'
        assert n.page_background('cs').text() == 'B'
        assert n.page_background('fr').text() == 'B'
        # Lang must be passed to .content() when variants are defined,
        # but may be omitted when no variants are passed to ContentNode.
        with pytest.raises(AssertionError):
            n.content()
        n2 = lcg.ContentNode('n', content=lcg.TextContent("C"))
        assert n2.content().text() == 'C'

    def test_resources(self):
        img = lcg.Image('a.png')
        n = lcg.ContentNode('n', content=lcg.TextContent("C", resources=(img,)))
        assert n.resource('a.png') is img
        assert n.resource('b.png') is None
        assert n.resources() == (img,)


class Resources(unittest.TestCase):

    def test_provider(self):
        warnings = []

        def warn(msg):
            warnings.append(msg)
        p = lcg.ResourceProvider(resources=(lcg.Audio('xxx.ogg'),))
        r = p.resource('xxx.xx', warn=warn)
        assert r is None
        assert len(warnings) == 1
        r = p.resource('xxx.mp3', warn=warn)
        assert r is None
        assert len(warnings) == 2
        r = p.resource('xxx.ogg')
        assert isinstance(r, lcg.Audio)
        assert len(warnings) == 2
        r = p.resource('default.css')
        assert isinstance(r, lcg.Stylesheet)
        assert len(warnings) == 2

    def test_dependencies(self):
        p = lcg.ResourceProvider(resources=(lcg.Audio('sound1.ogg'),
                                            lcg.Audio('sound2.ogg')))
        a = lcg.ContentNode('a', content=lcg.Content(), resource_provider=p)
        b = lcg.ContentNode('b', content=lcg.Content(), resource_provider=p)
        a.resource('default.css')
        b.resource('non-existing-file.js')
        assert tuple(sorted([r.filename() for r in a.resources()])) == \
            ('default.css', 'sound1.ogg', 'sound2.ogg')
        assert tuple(sorted([r.filename() for r in b.resources()])) == \
            ('sound1.ogg', 'sound2.ogg')


class Parser(unittest.TestCase):

    def setUp(self):
        self._parser = lcg.Parser()

    def _test_parser(self, text, content):
        """Parse given text and verify that the result matches given content."""
        def html(content):
            if not isinstance(content, lcg.Content):
                content = lcg.Container(content)
            node = lcg.ContentNode('test', title='Test', content=content)
            exporter = lcg.HtmlExporter()
            exporter._generator._sorted_attributes = True
            context = exporter.context(node, None)
            result = content.export(context)
            try:
                import bs4
            except ImportError:
                return result
            else:
                return bs4.BeautifulSoup(result, 'lxml').prettify()
        # Compare the HTML exports as comparison of lcg.Content elements
        # is currently not implemented well.  Also in case of error, the diff
        # of the HTML gives a good idea about what is wrong.
        parsed = self._parser.parse(text)
        assert html(parsed) == html(content)

    def test_simple_text(self):
        text = "Hello, how are you?\n\n  * one\n  * two\n  * three\n"
        self._test_parser(text, (
            lcg.p("Hello, how are you?"),
            lcg.ul(("one", "two", "three")),
        ))

    def test_sections(self):
        text = "= Main =\n== Sub1 ==\n== Sub2 ==\n=== SubSub1 ===\n== Sub3 =="
        self._test_parser(text, (
            lcg.sec('Main', (
                lcg.sec('Sub1', ()),
                lcg.sec('Sub2', (
                    lcg.sec('SubSub1', ()),
                )),
                lcg.sec('Sub3', ()),
            ))
        ))

    def test_parameters(self):
        text = '''
@parameter header hello
@parameter footer
@center
@PAGE@
@end footer
'''
        parameters = {}
        self._parser.parse(text, parameters)
        assert 'page_header' in parameters
        assert 'page_footer' in parameters
        assert 'first_page_header' not in parameters
        header = parameters['page_header']
        assert header.content()[0].content()[0].content()[0].text() == 'hello'
        footer = parameters['page_footer']
        assert footer.content()[0].halign() == lcg.HorizontalAlignment.CENTER

    def test_hrule(self):
        text = '''
blah blah

----

blah blah
'''
        self._test_parser(text, (
            lcg.p('blah blah'),
            lcg.hr(),
            lcg.p('blah blah'),
        ))

    def test_alignment(self):
        for alignment, constant in (('center', lcg.HorizontalAlignment.CENTER,),
                                    ('left', lcg.HorizontalAlignment.LEFT,),
                                    ('right', lcg.HorizontalAlignment.RIGHT,),):
            text = '''
blah blah

@%s
blah blah

blah blah
''' % (alignment,)
            c = self._parser.parse(text)
            assert len(c) == 3
            assert c[0].halign() is None
            assert c[1].halign() == constant
            assert c[2].halign() is None

    def test_table(self):
        text = '''
| *header* | *line* |
|-------------------|
| text1    | text2  |

|-------------------|
| *header* | *line* |
| text1    | text2  |
|-------------------|

| >        | <>     |
| <r20>    | <c>    |
| *header* | *line* |
| text1    | text2  |
'''
        c = self._parser.parse(text)
        assert len(c) == 3
        assert all([isinstance(x, lcg.Table) for x in c])
        for i in range(3):
            rows = c[i].content()
            assert len(rows) == 2
            assert all([isinstance(r, lcg.TableRow) for r in rows])
            for cell in rows[0].content():
                assert isinstance(cell, lcg.TableHeading)
            for cell in rows[1].content():
                assert isinstance(cell, lcg.TableCell)
        row = c[2].content()[1]
        cells = row.content()
        assert cells[0].align() == lcg.TableCell.RIGHT
        assert cells[1].align() == lcg.TableCell.CENTER
        bars = c[2].bars()
        assert 1 in bars
        assert 2 in bars
        assert 0 not in bars

    def test_lists(self):
        text = '''
* Unordered item 1.
  1. Ordered item 1.
  2. Ordered item 2.
     - Unordered item 11.
     - Unordered item 12.

* Unordered item 2.
  a. Ordered item 1.
     Next line 1.

     Next paragraph 1.

  b. Ordered item 2.

     Next paragraph 2.
* Unordered item 3.
'''
        c = self._parser.parse(text)
        assert len(c) == 1
        assert isinstance(c[0], lcg.ItemizedList)
        assert c[0].order() is None
        items = c[0].content()
        assert len(items) == 3
        # First item contents
        item_content = items[0].content()
        assert len(item_content) == 2
        assert isinstance(item_content[0], lcg.Container)
        assert isinstance(item_content[1], lcg.ItemizedList)
        assert item_content[1].order() == lcg.ItemizedList.NUMERIC
        assert len(item_content[1].content()) == 2
        # Second item contents
        item_content = items[1].content()
        assert len(item_content) == 2
        assert isinstance(item_content[0], lcg.Container)
        assert isinstance(item_content[1], lcg.ItemizedList)
        assert item_content[1].order() == lcg.ItemizedList.LOWER_ALPHA
        assert len(item_content[1].content()) == 2

    def test_paragraph_newline(self):
        c = self._parser.parse('hello\n\nworld')
        assert c[0].content()[0].content()[0].text()[-1] == 'o', \
            "Extra newline after paragraph?"

    def test_generic_container(self):
        text = '''
blah blah

>>

inner content

<<

blah
'''
        self._test_parser(text, (
            lcg.p("blah blah"),
            lcg.Container(lcg.p("inner content"), name='lcg-generic-container'),
            lcg.p("blah"),
        ))

    def test_generic_container_with_class(self):
        text = '''
>> .foo

blah

<<
'''
        self._test_parser(text, (
            lcg.Container(lcg.p("blah"), name='foo'),
        ))

    def test_generic_container_with_id_and_class(self):
        text = '''
>> bar

blah

<<
'''
        self._test_parser(text, (
            lcg.Container(lcg.p("blah"), id='bar', name='lcg-generic-container'),
        ))

    def test_nested_generic_container(self):
        text = '''
blah

>>

inner content

>>>
1st nested
<<<

>>>
2nd nested
<<<
<<
'''
        self._test_parser(text, (
            lcg.p("blah"),
            lcg.Container((
                lcg.p("inner content"),
                lcg.Container(lcg.p("1st nested"), name='lcg-generic-container'),
                lcg.Container(lcg.p("2nd nested"), name='lcg-generic-container'),
            ), name='lcg-generic-container'),
        ))

    def test_generic_container_with_nested_section(self):
        text = '''
>>

blah blah

= Top Section =

>>>

== Section One ==

one

== Section Two ==

two

<<<

blah blah

<<
'''
        self._test_parser(text, (
            lcg.Container((
                lcg.p("blah blah"),
                lcg.Section(title='Top Section', name='default-section', content=(
                    lcg.Container((
                        lcg.Section(title='Section One', name='default-section',
                                    content=lcg.p('one')),
                        lcg.Section(title='Section Two', name='default-section',
                                    content=lcg.p('two')),
                    ), name='lcg-generic-container'),
                    lcg.p("blah blah"),
                )),
            ), name='lcg-generic-container'),
        ))

    def test_collapsible_pane(self):
        text = '''
[Read more...] >> xx

blah

<<
'''
        self._test_parser(text, (
            lcg.CollapsiblePane("Read more...", lcg.p("blah"), id='xx'),
        ))

    def test_collapsible_pane_expanded(self):
        text = '''
[Read more...]+ >> xx

blah

<<
'''
        self._test_parser(text, (
            lcg.CollapsiblePane("Read more...", lcg.p("blah"), collapsed=False, id='xx'),
        ))

    def test_external_video_links(self):
        for text, content in (
                ('http://www.youtube.com/watch?v=xyz123',
                 lcg.p(lcg.InlineExternalVideo('youtube', 'xyz123'))),
                ('http://www.vimeo.com/123456',
                 lcg.p(lcg.InlineExternalVideo('vimeo', '123456'))),
                ('[http://www.vimeo.com/123456:330x220]',
                 lcg.p(lcg.InlineExternalVideo('vimeo', '123456', size=(330, 220)))),
                ('[http://www.vimeo.com/123456 My Special Video]',
                 lcg.p(lcg.InlineExternalVideo('vimeo', '123456', title='My Special Video'))),
        ):
            self._test_parser(text, content)


class MacroParser(unittest.TestCase):

    def test_simple_condition(self):
        text = "@if x\nX\n@else\nY@endif\n"
        r = lcg.MacroParser(globals=dict(x=True)).parse(text)
        assert r == "X\n"

    def test_condition(self):
        def check(condition, expected_result, **globals):
            text = ("@if " + condition + "\nTrue\n@else\nFalse\n@endif")
            parser = lcg.MacroParser(globals=globals)
            result = parser.parse(text).strip() == 'True'
            assert result == expected_result
        # Some more complicated condition.
        c1 = "a in ('A', 'B', 'C') and b > 3 and b+5 <= c and c is not None"
        check(c1, True, a='A', b=5, c=55)
        check(c1, False, a='X', b=5, c=None)
        # Try using builtins.
        c2 = "ord(a) == b and chr(b) == a and sum((b,c,3)) >= 70 and any([True, False, a == b])"
        check(c2, True, a='A', b=65, c=2)
        check(c2, False, a='X', b=5, c=2)

    def test_exception(self):
        text = "A\n@if a//b == c\nX@else\nY\n@endif\n\nB\n\n"
        r = lcg.MacroParser(globals=dict(a=5, b=0, c=2)).parse(text)
        assert r == "A\nZeroDivisionError: integer division or modulo by zero\nB\n\n"

    def test_condition_newlines(self):
        text = "A\n@if x\nX\n@endif\n\nB\n\n"
        r = lcg.MacroParser(globals=dict(x=True)).parse(text)
        assert r == "A\nX\n\nB\n\n"

    def test_nested_condition(self):
        def join(*lines):
            return "".join([line + "\n" for line in lines])
        text = join("A",
                    "@if b",
                    "B",
                    "@else",
                    "@if c",
                    "C",
                    "@endif",
                    "D",
                    "@endif",
                    "E")
        r1 = lcg.MacroParser(globals=dict(b=True, c=True)).parse(text)
        r2 = lcg.MacroParser(globals=dict(b=False, c=True)).parse(text)
        r3 = lcg.MacroParser(globals=dict(b=False, c=False)).parse(text)
        assert r1 == join("A", "B", "E")
        assert r2 == join("A", "C", "D", "E")
        assert r3 == join("A", "D", "E")

    def test_inclusion(self):
        text = "Foo\n@include bar\nBaz\n"
        r = lcg.MacroParser(globals=dict(bar='Bar')).parse(text)
        assert r == "Foo\nBar\nBaz\n"


class HtmlImport(unittest.TestCase):

    def test_html(self):
        # This HTML preserves the formatting produced by ckeditor, only long lines are wrapped
        # in order to make Flycheck happy...
        html = u''' <p>some text
   <span class="lcg-mathml" contenteditable="false" style="display: inline-block;">
     <math contenteditable="false" style="display:inline-block"
         xmlns="http://www.w3.org/1998/Math/MathML">
       <semantics><mstyle displaystyle="true"><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup>
         <mi>y</mi><mn>2</mn></msup></mstyle><annotation encoding="ASCII">x^2 + y^2</annotation>
       </semantics></math></span></p>
 <ol start="1" style="list-style-type: lower-alpha;">
         <li>
                 jedna</li>
         <li>
                 dvě</li>
 </ol>
 <ul>
         <li>
                 psi</li>
         <li>
                 kočky</li>
 </ul>
 <ol>
         <li>
                 za prvé</li>
         <li>
                 za druhé</li>
 </ol>
 <hr />
 <p>
         Písmo <strong>tučné</strong>, <em>zvýrazněné</em>, <u>podtržené</u>,
         <strike>škrtnuté</strike>, index<sub>dolní</sub> , index<sup>horní</sup>.</p>
 <h1>
         Sekce nová</h1>
 <p>
         Odstavec sekce.</p>
 <pre>
 předformátovaný
 řádkovaný text</pre>
 <div>
         obecný blok</div>
 <p>
         a zase jeden odstavec</p>
 <p>
         <a href="http://www.brailcom.org">Vložíme link na http://www.brailcom.org</a>,
         a uděláme <a name="kotva">kotvu</a>.</p>
 <p>
         Teď se odkážeme na tu <a href="#kotva">kotvu</a>.
         Budeme taky <a href="mailto:info@brailcom.org?subject=LCG%20testing">mailovat</a>.</p>
 <h1>
         Další sekce</h1>
 <p style="text-align: center;">
         Odstavec na střed.</p>
 <blockquote>
         <p>
                 Hello, world!</p>
 </blockquote>
 <p style="text-align: right;">
         anonymous</p>
 <div style="page-break-after: always;">
         <span style="display: none;">&nbsp;</span></div>
 <table border="1" cellpadding="1" cellspacing="1" style="width: 500px;">
         <caption>
                 tabulka</caption>
         <thead>
                 <tr>
                         <th scope="col">
                                 a</th>
                         <th scope="col">
                                 b</th>
                 </tr>
         </thead>
         <tbody>
                 <tr>
                         <td>
                                 c</td>
                         <td style="text-align: right;">
                                 d</td>
                 </tr>
                 <tr>
                         <td>
                                 e</td>
                         <td>
                                 f</td>
                 </tr>
         </tbody>
 </table>

 Inline Resource Image: <img data-lcg-resource="popup-arrow.png" src="/whatever/popup-arrow.png" />
 Inline External Image: <img src="http://www.freebsoft.org/img/logo.gif" />
 Image link: <a href="http://www.freebsoft.org">
   <img src="http://www.freebsoft.org/img/logo.gif" /></a>
 Audio: <a class="lcg-audio" data-lcg-resource="my-song.mp3" href="/whatever/my-song.mp3">
   My Song</a>
 Video: <a class="lcg-video" data-lcg-resource="my-video.flv" href="/whatever/my-video.flv">
   My Video</a>

<div class="lcg-exercise" contenteditable="false" data-type="MultipleChoiceQuestions"
     style="display: inline-block;">
<pre class="lcg-exercise-instructions">
Choose the correct answer
</pre>
<pre class="lcg-exercise-example">
</pre>
<pre class="lcg-exercise-src">
A screen reader is:
- A person.
- A device.
+ A program.
</pre>
<pre class="lcg-exercise-transcript">
</pre>
<pre class="lcg-exercise-reading">
</pre>
<pre class="lcg-exercise-explanation">
</pre>
</div>

 '''
        content = lcg.html2lcg(html)
        p = lcg.ResourceProvider()
        sec = lcg.Section("Section One", id='sec1', content=lcg.Content())
        n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                            content=lcg.Container((sec,)), resource_provider=p)
        context = lcg.HtmlExporter().context(n, None)
        content.export(context)
        lcg.html2data(html, lcg.HTML2XML)


class HtmlExport(unittest.TestCase):

    def test_generator(self):
        g = lcg.HtmlGenerator(sorted_attributes=True)
        # Tags with trivial export.
        for tag in ('html', 'head', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'title',
                    'style', 'body', 'div', 'section', 'span', 'map', 'strong',
                    'em', 'u', 'code', 'pre', 'sup', 'sub', 'p', 'blockquote',
                    'footer', 'figure', 'figcaption', 'a', 'ol', 'ul', 'li', 'dl',
                    'dt', 'dd', 'abbr', 'time', 'table', 'tr', 'th', 'td', 'thead',
                    'tfoot', 'tbody', 'object', 'label', 'button', 'optgroup',
                    'option', 'textarea', 'noscript', 'select', 'fieldset', 'legend'):
            method = getattr(g, tag)
            assert method('x') == '<%s>x</%s>' % (tag, tag)
            assert method(content='x') == '<%s>x</%s>' % (tag, tag)
            assert method(content=('x', 'y')) == '<%s>xy</%s>' % (tag, tag)
            assert method(content=()) == '<%s></%s>' % (tag, tag)
        for tag in ('link', 'meta', 'br', 'hr', 'param'):
            assert getattr(g, tag)() == '<%s/>' % tag
        # These tags require positional arguemnts or have non-trivial export.
        assert g.script('x') == u'<script type="text/javascript">x</script>'
        assert g.submit('x') == u'<button type="submit">x</button>'
        assert g.form('x') == u'<form action="#">x</form>'
        assert g.h('x', level=8) == u'<h8>x</h8>'
        assert g.img('x') == u'<img alt="" src="x"/>'
        assert g.iframe('x') == u'<iframe src="x"><a href="x">x</a></iframe>'
        assert g.input(type='text') == u'<input type="text"/>'
        assert g.field(name='a') == (u'<input class="text" name="a" size="20" '
                                     u'type="text" value=""/>')
        assert g.checkbox('a') == u'<input name="a" type="checkbox"/>'
        assert g.hidden('a', 'x') == u'<input name="a" type="hidden" value="x"/>'
        assert g.radio('a') == u'<input name="a" type="radio"/>'
        assert g.upload('a') == u'<input name="a" type="file"/>'
        assert g.audio('x') == u'<audio controls="controls" src="x"/>'
        assert g.video('x') == u'<video controls="controls" src="x"/>'
        assert g.source('x') == u'<source src="x"/>'
        # Now test with *some* typical optional arguments.
        assert g.a('x', href='a') == '<a href="a">x</a>'
        assert g.a('x', name='a') == '<a name="a">x</a>'
        assert g.button('X', disabled=True) == '<button disabled="disabled">X</button>'
        # Testing backwards compatibility of deprecated select() arguemnts.
        assert g.select('a', options=(('X', 'x'), ('Y', 'y'))) == (
            u'<select name="a"><option value="x">X</option>'
            u'<option value="y">Y</option></select>')
        assert g.select('a', options=(('X', 'x', False, 'c'), ('Y', 'y', True, 'cc'))) == (
            u'<select name="a"><option class="c" disabled="disabled" value="x">X</option>'
            u'<option class="cc" value="y">Y</option></select>')
        assert g.select('a', (('aa', (('X', 'x'), ('Y', 'y'))), ('bb', (('Z', 'z'),)))) == (
            u'<select name="a"><optgroup label="aa"><option value="x">X</option>'
            u'<option value="y">Y</option></optgroup>'
            u'<optgroup label="bb"><option value="z">Z</option>'
            u'</optgroup></select>')

    def test_export(self):
        n = lcg.ContentNode('test', title='Test', content=lcg.Content(),
                            globals=dict(x='value of x'))
        context = lcg.HtmlExporter().context(n, None, sec_lang='es')
        context._generator._sorted_attributes = True
        for content, html in (
            (('a', ' ', lcg.strong('b ', lcg.em('c'), ' ', lcg.u('d')), ' ', lcg.code('e')),
             'a <strong>b <em>c</em> <u>d</u></strong> <code>e</code>'),
            (lcg.cite('x'),
             '<span class="lcg-citation" lang="es">x</span>'),
            (lcg.br(),
             '<br/>'),
            (lcg.hr(),
             '<hr/>'),
            (lcg.Quotation(lcg.p("blah")),
             u'<blockquote class="lcg-quotation"><p>blah</p></blockquote>'),
            (lcg.Quotation(lcg.TextContent("blah"), source='Hugo', uri='http://hugo.org'),
             (u'<blockquote class="lcg-quotation">blah<footer>— '
              u'<a href="http://hugo.org">Hugo</a></footer></blockquote>')),
            (lcg.NewPage(),
             '<hr class="new-page"/>'),
            (lcg.Substitution('x'),
             'value of x'),
            ((lcg.Subscript(lcg.TextContent('sub')), lcg.Superscript(lcg.TextContent('sup'))),
             '<sub>sub</sub><sup>sup</sup>'),
            (lcg.p('Anchor: ', lcg.Anchor('x', text='here'), halign=lcg.HorizontalAlignment.RIGHT),
             '<p style="text-align: right;">Anchor: <span id="x">here</span></p>'),
            (lcg.container('blah'),
             'blah'),
            (lcg.container('blah', id='foo'),
             '<div id="foo">blah</div>'),
            (lcg.container('blah', name='bar'),
             '<div class="bar">blah</div>'),
            (lcg.container('blah', name=('foo', 'bar')),
             '<div class="foo bar">blah</div>'),
            (lcg.container('blah', id='foo', name='bar'),
             '<div class="bar" id="foo">blah</div>'),
            (lcg.sec('Section', 'blah'),
             ('<div class="section section-level-2 default-section" id="sec1">'
              '<div class="section-container section-level-2">'
              '<div class="section-heading section-level-2"><h2>Section</h2></div>'
              '<div class="section-content section-level-2">'
              '<div class="section-content-wrapper">blah</div></div></div></div>')),
            (lcg.sec('Section', 'blah', id='foo', heading='The Section'),
             ('<div class="section section-level-2 default-section" id="foo">'
              '<div class="section-container section-level-2">'
              '<div class="section-heading section-level-2"><h2>The Section</h2></div>'
              '<div class="section-content section-level-2">'
              '<div class="section-content-wrapper">blah</div></div></div></div>')),
            (lcg.InlineExternalVideo('vimeo', 'xyz'),
             ('<div class="external-video" style="max-width: 640px;">'
              '<div class="wrapper" style="padding-bottom: 75.0%">'
              '<iframe allowfullscreen="allowfullscreen" frameborder="0"'
              ' height="480" mozallowfullscreen="mozallowfullscreen"'
              ' src="https://player.vimeo.com/video/xyz" title="Video"'
              ' type="text/html" webkitallowfullscreen="webkitallowfullscreen" width="640">'
              '<a href="https://player.vimeo.com/video/xyz">'
              'https://player.vimeo.com/video/xyz</a>'
              '</iframe></div></div>')),
            (lcg.InlineExternalVideo('youtube', 'xyz', size=(330, 220), title='My Video'),
             ('<div class="external-video" style="max-width: 330px;">'
              '<div class="wrapper" style="padding-bottom: 66.0%">'
              '<iframe allowfullscreen="allowfullscreen" frameborder="0"'
              ' height="220" mozallowfullscreen="mozallowfullscreen"'
              ' src="https://www.youtube.com/embed/xyz" title="My Video"'
              ' type="text/html" webkitallowfullscreen="webkitallowfullscreen" width="330">'
              '<a href="https://www.youtube.com/embed/xyz">'
              'https://www.youtube.com/embed/xyz</a>'
              '</iframe></div></div>')),
        ):
            assert lcg.coerce(content).export(context) == html

    def test_formatting(self):
        resources = (lcg.Resource('text.txt', uri='/resources/texts/text.txt'),
                     lcg.Audio('xx.mp3'),
                     lcg.Image('aa.jpg'),
                     lcg.Image('bb.jpg'),
                     lcg.Image('cc.png', title="Image C", descr="Nice picture"))
        p = lcg.ResourceProvider(resources=resources)
        sec = lcg.Section("Section One", id='sec1', content=lcg.Content())
        n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                            content=lcg.Container((sec,)), resource_provider=p)
        context = lcg.HtmlExporter().context(n, None)
        context.generator()._sorted_attributes = True
        for text, expected in (
            ('a *b /c/ _d_* =e=',
             'a <strong>b <em>c</em> <u>d</u></strong> <code>e</code>'),
            ('a */b',  # Unfinished markup (we probably don't want that, but now it works so).
             'a <strong><em>b</em></strong>'),
            (' x ',
             ' x '),
            ('# comment',
             ''),
            # Escapes
            (r'\*one* \\*two* \\\*three* \\\\*four* \\\\\*five*',
             r'*one* \<strong>two</strong> \*three* \\<strong>four</strong> \\*five*'),
            # Absolute links
            ('https://www.freebsoft.org',
             '<a href="https://www.freebsoft.org">https://www.freebsoft.org</a>'),
            ('See http://www.freebsoft.org.',
             'See <a href="http://www.freebsoft.org">http://www.freebsoft.org</a>.'),
            ('(see http://www.freebsoft.org)',
             '(see <a href="http://www.freebsoft.org">http://www.freebsoft.org</a>)'),
            ('(see http://www.freebsoft.org).',
             '(see <a href="http://www.freebsoft.org">http://www.freebsoft.org</a>).'),
            ('[http://www.freebsoft.org]',
             '<a href="http://www.freebsoft.org">http://www.freebsoft.org</a>'),
            ('[http://www.freebsoft.org Free(b)soft website]',
             '<a href="http://www.freebsoft.org">Free(b)soft website</a>'),
            ('[http://www.freebsoft.org label | descr]',
             '<a href="http://www.freebsoft.org" title="descr">label</a>'),
            # XSS attacks
            ('[javascript:alert("XSS"); click me]',
             '[javascript:alert("XSS"); click me]'),
            ('[JavascrIpt:alert("XSS"); click me]',
             '[JavascrIpt:alert("XSS"); click me]'),
            ('[vbscript:msgbox("XSS"); click me]',
             '[vbscript:msgbox("XSS"); click me]'),
            ('["javascript:alert("XSS");" click me]',
             '<a href=\'"javascript:alert("XSS");"\'>click me</a>'),
            ('[http://xss.me <script>alert("XSS");</script>]',
             '<a href="http://xss.me">&lt;script&gt;alert("XSS");&lt;/script&gt;</a>'),
            # Inline images
            ('[aa.jpg]',
             u'<img alt="" class="lcg-image image-aa" src="images/aa.jpg"/>'),
            ('*[aa.jpg]*',
             '<strong><img alt="" class="lcg-image image-aa" src="images/aa.jpg"/></strong>'),
            ('[aa.jpg label]',
             u'<img alt="label" class="lcg-image image-aa" src="images/aa.jpg"/>'),
            ('[aa.jpg:20x30 label]',
             (u'<img alt="label" class="lcg-image image-aa"'
              u' src="images/aa.jpg" style="width: 20px; height: 30px;"/>')),
            ('[>aa.jpg]',
             (u'<img align="right" alt="" class="lcg-image right-aligned image-aa"'
              u' src="images/aa.jpg"/>')),
            ('[<aa.jpg]',
             (u'<img align="left" alt="" class="lcg-image left-aligned image-aa" '
              u'src="images/aa.jpg"/>')),
            ('[aa.jpg label | descr]',
             u'<img alt="label: descr" class="lcg-image image-aa" src="images/aa.jpg"/>'),
            (u'[http://www.freebsoft.org/img/logo.gif Free(b)soft logo]',
             (u'<img alt="Free(b)soft logo" class="lcg-image image-logo"'
              u' src="http://www.freebsoft.org/img/logo.gif"/>')),
            ('[cc.png]',
             u'<img alt="Image C: Nice picture" class="lcg-image image-cc" src="images/cc.png"/>'),
            # Image links (links with an image instead of a label)
            ('[aa.jpg bb.jpg label | descr]',
             (u'<a href="images/aa.jpg" title="descr">'
              u'<img alt="label" class="lcg-image image-bb" src="images/bb.jpg"/></a>')),
            ('[aa.jpg bb.jpg | descr]',
             ('<a href="images/aa.jpg" title="descr">'
              u'<img alt="" class="lcg-image image-bb" src="images/bb.jpg"/></a>')),
            ('[>aa.jpg bb.jpg label | descr]',
             (u'<a href="images/aa.jpg" title="descr">'
              u'<img align="right" alt="label"'
              u' class="lcg-image right-aligned image-bb" src="images/bb.jpg"/></a>')),
            ('[test bb.jpg bb]',
             (u'<a href="test" title="Some description">'
              u'<img alt="bb" class="lcg-image image-bb" src="images/bb.jpg"/></a>')),
            ('[http://www.freebsoft.org /img/logo.gif]',
             (u'<a href="http://www.freebsoft.org">'
              u'<img alt="" class="lcg-image image-logo" src="/img/logo.gif"/></a>')),
            ('[http://www.freebsoft.org /img/logo.gif Free(b)soft website]',
             (u'<a href="http://www.freebsoft.org">'
              u'<img alt="Free(b)soft website" class="lcg-image image-logo" src="/img/logo.gif"/>'
              u'</a>')),
            (('[http://www.freebsoft.org /img/logo.gif Free(b)soft website | '
              'Go to Free(b)soft website]'),
             (u'<a href="http://www.freebsoft.org" title="Go to Free(b)soft website">'
              u'<img alt="Free(b)soft website" class="lcg-image image-logo" '
              'src="/img/logo.gif"/></a>')),
            # Absolute image links
            ('http://www.freebsoft.org/img/logo.gif',
             (u'<img alt="" class="lcg-image image-logo"'
              u' src="http://www.freebsoft.org/img/logo.gif"/>')),
            # Audio player links
            ('[xx.mp3]',
             re.compile(r'<a class="media-control-link" href="media/xx.mp3"'
                        r' id="[a-z0-9-]+">xx.mp3</a>')),
            ('[/somewhere/some.mp3]',
             re.compile(r'<a class="media-control-link" href="/somewhere/some.mp3" id="[a-z0-9-]+"'
                        r'>/somewhere/some.mp3</a>')),
            # Internal Reference Links
            ('[text.txt]',
             u'<a href="/resources/texts/text.txt">text.txt</a>'),
            ('[test]',
             u'<a href="test" title="Some description">Test Node</a>'),
            ('[test#sec1]',
             u'<a href="test#sec1">Section One</a>'),
            ('[#sec1]',
             u'<a href="test#sec1">Section One</a>'),
            # HTML special
            (r'<bla>',
             r'&lt;bla&gt;'),
        ):
            content = lcg.Parser().parse_inline_markup(text)
            result = content.export(context)
            if isinstance(expected, basestring):
                assert result == expected
            else:
                assert expected.match(result)

    def test_mathml(self):
        n = lcg.ContentNode('test', title='Test', content=lcg.Content(),
                            globals=dict(x='value of x'))
        context = lcg.HtmlExporter().context(n, None)

        def export(content):
            return content.export(context)
        content = lcg.MathML(u"""
<math xmlns="http://www.w3.org/1998/Math/MathML">
  <mi>&#x03C0;<!-- π --></mi>
  <mo>&#x2062;<!-- &InvisibleTimes; --></mo>
  <msup>
    <mi>r</mi>
    <mn>2</mn>
  </msup>
</math>""")
        assert isinstance(export(content), basestring)
        for xml in (u'</math><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>',
                    u'<math xmlns="http://www.w3.org/1998/Math/MathML"><script>1</script></math>',
                    u'<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>' +
                    u'<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>',):
            content = lcg.MathML(xml)
            with pytest.raises(lcg.ParseError):
                export(content)
        content = lcg.MathML(u'<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>')
        assert isinstance(export(content), basestring)

    def test_html_content(self):
        # Make sure the HTML content is not escaped when wrappped in another HTML element.
        c = lcg.Container(lcg.HtmlContent('<b>B</b>'), name='x')
        context = lcg.HtmlExporter().context(lcg.ContentNode('y'), None)
        assert c.export(context) == '<div class="x"><b>B</b></div>'

    def test_js_value(self):
        import json
        g = lcg.HtmlGenerator()
        for value in ('a', 1, True,
                      [1, 2, 3], [3, 2, 1],
                      {'a': 'A', 'b': 'B'}, {'1': 1, '2': 2},
                      "foo'ba{r}", '"foo"[bar]', '<a>'):
            assert value == json.loads(g.js_value(value))


class EpubExport(unittest.TestCase):

    def test_export(self):
        #m = lcg.Metadata()
        p = lcg.ResourceProvider()
        d = lcg.ContentNode('d', resource_provider=p)
        c = lcg.ContentNode('c', children=(d,), resource_provider=p)
        b = lcg.ContentNode('b', resource_provider=p)
        a = lcg.ContentNode('a', children=(b, c), resource_provider=p)  # , metadata=m)
        e = lcg.EpubExporter()
        context = e.context(a, 'en')
        epub = e.export(context)
        archive = zipfile.ZipFile(io.BytesIO(epub))
        pkg_opf = archive.read('rsrc/pkg.opf')
        assert pkg_opf[:19] == '<?xml version="1.0"'


class ImsExport(unittest.TestCase):

    def test_export(self):
        # m = lcg.Metadata()
        p = lcg.ResourceProvider()
        d = lcg.ContentNode('d', resource_provider=p)
        c = lcg.ContentNode('c', children=(d,), resource_provider=p)
        b = lcg.ContentNode('b', resource_provider=p)
        a = lcg.ContentNode('a', children=(b, c), resource_provider=p)  # , metadata=m)
        e = lcg.IMSExporter()
        manifest = e.manifest(a).xml()
        assert manifest[:19] == '<?xml version="1.0"'


@pytest.mark.skipif(not hasattr(lcg, 'BrailleExporter'), reason="Braille support not present")
class BrailleExport(unittest.TestCase):

    def _load_presentation(self):
        return lcg.braille_presentation(presentation_file='presentation-braille-test.py')

    def _test(self, text, braille, header, footer, presentation, lang, sec_lang=None,
              full_parse=False):
        page_height = presentation.page_height
        presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
        parser = lcg.Parser()
        if full_parse:
            content = parser.parse(text)
        else:
            content = lcg.Container((parser.parse_inline_markup(text),))
        n = lcg.ContentNode('test', title='Test Node', descr="Some description", content=content)
        exporter = lcg.BrailleExporter()
        context = exporter.context(n, lang=lang, sec_lang=sec_lang, presentation=presentation_set)
        page_lines = page_height.size()
        if isinstance(braille, basestring):
            n_lines = page_lines - len(braille.split('\n')) - 2
            expected = [header + braille + '\n' * n_lines + footer]
        elif isinstance(braille, (tuple, list)):
            expected = [header + braille[0] +
                        '\n' * (page_lines - len(braille[0].split('\n')) - 2) + footer[0]]
            expected.extend([b + '\n' * (page_lines - len(b.split('\n'))) + f
                             for b, f in zip(braille, footer)[1:]])
        else:
            with pytest.raises(braille):
                exporter.export(context)
            return
        assert exporter.export(context).replace('\r\n', '\n').split('\f')[:-1] == expected

    def test_formatting(self):
        presentation = self._load_presentation()
        for text, braille in (
            (u'abc', u'⠁⠃⠉',),
            (u'a a11a 1', u'⠁⠀⠁⠼⠁⠁⠐⠁⠀⠼⠁',),
            (u'*tučný*', u'⠔⠰⠞⠥⠩⠝⠯⠰⠔',),
            (u'/šikmý/', u'⠔⠨⠱⠊⠅⠍⠯⠨⠔',),
            (u'_podtržený_', u'⠸⠏⠕⠙⠞⠗⠮⠑⠝⠯',),
            (u'_hodně podtržený_', u'⠔⠸⠓⠕⠙⠝⠣⠀⠏⠕⠙⠞⠗⠮⠑⠝⠯⠸⠔',),
            (u'zkouška českého dělení slov', u'⠵⠅⠕⠥⠱⠅⠁⠀⠩⠑⠎⠅⠜⠓⠕⠀⠙⠣⠤\n⠇⠑⠝⠌⠀⠎⠇⠕⠧',),
        ):
            self._test(text, braille, u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                       presentation, 'cs')
        tests = ((u'abc', u'⠁⠃⠉',),
                 (u'long line to be hyphenated', u'⠇⠕⠝⠛⠀⠇⠊⠝⠑⠀⠞⠕⠀⠃⠑⠀⠓⠽⠤\n⠏⠓⠑⠝⠁⠞⠑⠙',),
                 (u'*bold*', u'⠸⠃⠕⠇⠙',),
                 (u'/italic/', u'⠨⠊⠞⠁⠇⠊⠉',),
                 (u'_underlined_', u'⠥⠝⠙⠑⠗⠇⠊⠝⠑⠙',),)
        if False:
            # buggy in current liblouis
            tests += ((u'a a11a 1', u'⠁⠀⠁⠼⠁⠁⠐⠁⠀⠼⠁',),)
        for text, braille in tests:
            self._test(text, braille, u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                       presentation, 'en')

    def test_languages(self):
        presentation = self._load_presentation()
        self._test(u'řwe >>world<< řwe', u'⠺⠷⠑⠀⠺⠕⠗⠇⠙⠀⠺⠷⠑', u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', 'en')

    def test_special_formatting(self):
        presentation = self._load_presentation()
        self._test(u'50 %, 12 ‰', u'⠼⠑⠚⠼⠏⠂⠀⠼⠁⠃⠼⠗', u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                   presentation, 'cs')

    def test_tables(self):
        presentation = self._load_presentation()
        # Simple tables
        self._test(u'| first | line | x |\n| second | row | y |',
                   u'⠋⠊⠗⠎⠞⠀⠀⠀⠇⠊⠝⠑⠀⠀⠭\n⠎⠑⠉⠕⠝⠙⠀⠀⠗⠕⠷⠀⠀⠀⠽',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| *heading* | *h* | *h* |\n| first | line | x |\n| second | row | y |',
                   u'⠓⠑⠁⠙⠊⠝⠛⠀⠀⠓⠀⠀⠀⠀⠀⠓\n⠋⠊⠗⠎⠞⠀⠀⠀⠀⠇⠊⠝⠑⠀⠀⠭\n⠎⠑⠉⠕⠝⠙⠀⠀⠀⠗⠕⠷⠀⠀⠀⠽',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        # Compact wide tables
        self._test(u'| Narrow | Table |', u'⠠⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| Less Narrow | Table |', u'⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| Less Narrow | Table |\n| Less Narrow | Table |',
                   u'⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑\n⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| *a* | *b* |\n| prefixed lines | table |\n| prefixed rows | cell |\n',
                   u'⠏⠗⠑⠋⠊⠭⠑⠙⠀⠁⠀⠀⠃⠀⠀⠀⠀\n⠇⠊⠝⠑⠎⠀⠀⠀⠀⠀⠀⠀⠞⠁⠃⠇⠑\n⠗⠕⠷⠎⠀⠀⠀⠀⠀⠀⠀⠀⠉⠑⠇⠇⠀',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| *a* | *b* |\n| line & suffix | table |\n| row & suffix | cell |\n',
                   u'⠁⠀⠼⠯⠀⠎⠥⠋⠋⠊⠭⠀⠀⠃⠀⠀⠀⠀\n⠇⠊⠝⠑⠀⠀⠀⠀⠀⠀⠀⠀⠀⠞⠁⠃⠇⠑\n⠗⠕⠷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠑⠇⠇⠀',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        # Double page tables
        self._test(u'| this is | a double page | table |\n| the | columns | are too wide |',
                   (u'⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    u'⠞⠓⠊⠎⠀⠊⠎⠀⠀⠁⠀⠙⠕⠥⠃⠇⠑⠀⠏⠁\n⠞⠓⠑⠀⠀⠀⠀⠀⠀⠉⠕⠇⠥⠍⠝⠎⠀⠀⠀⠀',
                    u'⠛⠑⠀⠀⠞⠁⠃⠇⠑⠀⠀⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠁⠗⠑⠀⠞⠕⠕⠀⠷⠊⠙⠑',),
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   (u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                    u'⠼⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀',
                    u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠉',),
                   presentation, 'cs', full_parse=True)
        self._test((u'some text\n\n'
                    u'| this is | a double page | table |\n| the | columns | are too wide |\n\n'
                    u'another text\n'),
                   (u'⠎⠕⠍⠑⠀⠞⠑⠭⠞\n\n⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    u'⠞⠓⠊⠎⠀⠊⠎⠀⠀⠁⠀⠙⠕⠥⠃⠇⠑⠀⠏⠁\n⠞⠓⠑⠀⠀⠀⠀⠀⠀⠉⠕⠇⠥⠍⠝⠎⠀⠀⠀⠀',
                    u'⠛⠑⠀⠀⠞⠁⠃⠇⠑⠀⠀⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠁⠗⠑⠀⠞⠕⠕⠀⠷⠊⠙⠑',
                    u'⠁⠝⠕⠞⠓⠑⠗⠀⠞⠑⠭⠞',),
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   (u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                    u'⠼⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀',
                    u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠉',
                    u'⠼⠙⠀⠀⠀⠀⠀⠀⠀⠀⠀',),
                   presentation, 'cs', full_parse=True)
        # Super wide tables
        self._test(u'| extremely wide table | very very wide table |\n| next | line |',
                   (u'⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎\n⠞⠗⠁⠝⠎⠏⠕⠎⠑⠙⠄\n\n⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    u'⠑⠭⠞⠗⠑⠍⠑⠇⠽⠀⠷⠊⠙⠑⠀⠞⠁⠃⠇⠑\n⠧⠑⠗⠽⠀⠧⠑⠗⠽⠀⠷⠊⠙⠑⠀⠞⠁⠃⠇⠑',
                    u'⠀⠀⠝⠑⠭⠞\n⠀⠀⠇⠊⠝⠑',),
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   (u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                    u'⠼⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀',
                    u'⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠉',),
                   presentation, 'cs', full_parse=True)

    def test_mathml(self):
        import louis
        python_version = sys.version_info
        louis_version = louis.version().split()[0].split('.')
        can_parse_entities = (python_version[0] >= 3 or
                              python_version[0] == 2 and python_version[1] >= 7)
        entity_regexp = re.compile('&[a-zA-Z]+;')

        def test(mathml, expected_result, min_louis=None):
            if not can_parse_entities and entity_regexp.search(mathml):
                return
            if min_louis:
                min_louis_list = min_louis.split('.')
                for i in range(len(min_louis_list)):
                    if i >= len(louis_version):
                        break
                    v_min = int(min_louis_list[i])
                    v_louis = int(louis_version[i])
                    if v_min > v_louis:
                        return
                    if v_min < v_louis:
                        break
            content = lcg.MathML(mathml)
            presentation = self._load_presentation()
            presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
            n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                                content=content)
            exporter = lcg.BrailleExporter()
            context = exporter.context(n, lang='cs', presentation=presentation_set)
            exported = exporter.export(context)
            result = exported.replace('\r\n', '\n').split('\n\n')[1]
            assert result == expected_result, (
                "\n  - source text: %r\n  - expected:    %r\n  - got:         %r" %
                (mathml, expected_result, result))
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3,14</mn></mrow>
</math>''', u'⠼⠉⠂⠁⠙')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1 000,5</mn></mrow>
</math>''', u'⠼⠁⠚⠚⠚⠂⠑')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mn>1</mn><mo>=</mo><mn>2</mn></mrow>
</math>''', u'⠼⠁⠀⠲⠼⠁⠀⠶⠼⠃')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>a</mi><mo>=</mo><mo>-</mo><mn>7</mn></mrow>
</math>''', u'⠁⠀⠶⠤⠼⠛')
        test(u'''<math display="block" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow>
  <mfrac>
    <mrow><mfrac><mrow><mn>1</mn></mrow><mrow><mn>2</mn></mrow></mfrac></mrow>
    <mrow><mfrac><mrow><mn>3</mn><mo>+</mo><mn>4</mn></mrow><mrow><mn>5</mn></mrow></mfrac></mrow>
  </mfrac>
</mrow>
</math>''', u'''⠆⠆⠼⠁⠻⠼⠃⠰⠻⠻⠆⠼⠉⠀⠲⠼⠙⠻
⠻⠼⠑⠰⠰''')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn><mi>a</mi></mrow>
</math>''', u'⠼⠁⠃⠐⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn></mrow><mrow><mi>a</mi></mrow>
</math>''', u'⠼⠁⠃⠐⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn><mi>k</mi></mrow>
</math>''', u'⠼⠁⠃⠅')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn></mrow><mrow><mi mathvariant="bold">a</mi><mi>b</mi></mrow>
</math>''', u'⠼⠁⠃⠔⠰⠁⠰⠔⠃')
        test(u'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1 plus MathML 2.0//EN"
  "http://www.w3.org/TR/MathML2/dtd/xhtml-math11-f.dtd" [
 <!ENTITY mathml "http://www.w3.org/1998/Math/MathML">
 ]>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>untitled</title></head>
<body>
<math display="block" xmlns="http://www.w3.org/1998/Math/MathML"><mrow>
<msub><mi>x</mi><mtext>1,2</mtext></msub><mo>=</mo>
<mfrac><mrow>
<mo>-</mo><mi>b</mi><mo>&PlusMinus;</mo>
<msqrt><msup><mi>b</mi><mn>2</mn></msup><mo>-</mo><mn>4</mn><mi>a</mi><mi>c</mi></msqrt></mrow>
<mrow><mn>2</mn><mi>a</mi>
</mrow></mfrac>
</mrow></math>
</body></html>
''', u'''⠭⠡⠼⠁⠂⠀⠼⠃⠱⠀⠶⠆⠤⠃⠀⠲⠤⠩
⠩⠃⠌⠼⠃⠱⠀⠤⠼⠙⠐⠁⠉⠱⠻⠼⠃⠐⠁⠰''')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msqrt><mn>2</mn></msqrt><mo>+</mo><mroot><mrow><mn>2</mn></mrow><mrow><mn>3</mn></mrow>
</mroot></mrow>
</math>''', u'⠩⠼⠃⠱⠀⠲⠠⠌⠼⠉⠩⠼⠃⠱')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>&#x2208;</mo><mi>R</mi></mrow>
</math>''', u'⠭⠀⠘⠑⠀⠠⠗')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>∈</mo><mi>R</mi></mrow>
</math>''', u'⠭⠀⠘⠑⠀⠠⠗')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>α</mi><mo>+</mo><mi>β</mi></mrow>
</math>''', u'⠘⠁⠀⠲⠘⠃')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mrow><mn>5</mn></mrow><mrow><mn>6</mn></mrow></mfrac><mo>-</mo><mfrac><mrow><mn>2</mn>
</mrow><mrow><mn>3</mn></mrow></mfrac><mo>=</mo><mfrac><mrow><mn>5</mn><mo>-</mo><mn>4</mn></mrow>
<mrow><mn>6</mn></mrow></mfrac></mrow>
</math>''', u'⠆⠼⠑⠻⠼⠋⠰⠀⠤⠆⠼⠃⠻⠼⠉⠰⠀⠶\n⠶⠆⠼⠑⠀⠤⠼⠙⠻⠼⠋⠰')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>5</mn><mfrac><mrow><mn>2</mn></mrow><mrow><mn>3</mn></mrow></mfrac></mrow>
</math>''', u'⠼⠑⠆⠼⠃⠻⠼⠉⠰')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>2,</mn><mover accent="true"><mn>32</mn><mo>&macr;</mo></mover></mrow>
</math>''', u'⠼⠃⠂⠉⠃⠉⠃⠤')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="&langle;" close="&rangle;" separators="|"><mi>a</mi><mi>b</mi><mi>c</mi></mfenced>
</math>''', u'⠈⠣⠁⠸⠀⠃⠸⠀⠉⠈⠜')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="&langle;" close="&rangle;" separators=","><mi>a</mi><mi>b</mi></mfenced>
</math>''', u'⠈⠣⠁⠂⠀⠃⠈⠜')
        test(u'''<math contenteditable="false" style="display:inline-block"
        xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mstyle displaystyle="true">
<msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mstyle>
<annotation encoding="ASCII">x^2 + y^2</annotation></semantics></math>''',
             u'⠭⠌⠼⠃⠱⠀⠲⠽⠌⠼⠃⠱')

    def test_inline_mathml(self):
        mathml = u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mn>1</mn><mo>=</mo><mn>2</mn></mrow>
</math>'''
        mathml_content = lcg.MathML(mathml)
        content = lcg.p(u"Trocha matematiky (", mathml_content, u") neuškodí.")
        presentation = self._load_presentation()
        presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
        n = lcg.ContentNode('test', title='Test Node', descr="Some description", content=content)
        exporter = lcg.BrailleExporter()
        context = exporter.context(n, lang='cs', presentation=presentation_set)
        exported = exporter.export(context)
        result = exported.replace('\r\n', '\n').split('\n\n')[1]
        assert result == u'''⠠⠞⠗⠕⠉⠓⠁⠀⠍⠁⠞⠑⠍⠁⠞⠊⠅⠽
⠦⠼⠁⠀⠲⠼⠁⠀⠶⠼⠃⠴
⠝⠑⠥⠱⠅⠕⠙⠌⠄'''

    def test_mathml_nemeth(self):
        python_version = sys.version_info
        can_parse_entities = (python_version[0] >= 3 or
                              python_version[0] == 2 and python_version[1] >= 7)
        entity_regexp = re.compile('&[a-zA-Z]+;')

        def test(mathml, expected_result, lang='cs', page_width=None, page_height=None,
                 pre=None, post=None):
            if not can_parse_entities and entity_regexp.search(mathml):
                return
            content = lcg.MathML(mathml)
            if pre is not None or post is not None:
                content = (content,)
                if pre is not None:
                    content = (lcg.TextContent(pre),) + content
                if post is not None:
                    content = content + (lcg.TextContent(post),)
                content = lcg.Container(content)
            presentation = self._load_presentation()
            presentation.braille_math_rules = 'nemeth'
            if page_width is True:
                presentation.page_width = lcg.USpace(40)
            elif page_width is not None:
                presentation.page_width = page_width
            if page_height is True:
                presentation.page_height = lcg.USpace(25)
            presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
            n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                                content=content)
            exporter = lcg.BrailleExporter()
            context = exporter.context(n, lang=lang, presentation=presentation_set)
            exported = exporter.export(context)
            result = exported.replace('\r\n', '\n').split('\n\n')[1]
            if post == '.':
                result = result[:-2] + u'⠲'
            elif post == ',':
                result = result[:-2] + u'⠠'
            if result != expected_result:
                print('---')
                print(mathml)
                print('---')
                print(" expected: |%s|" % (expected_result,))
                print("      got: |%s|" % (result,))
                print('---')
            assert result == expected_result
        # §8
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3,76</mn></mrow>
</math>''', u'⠼⠒⠨⠶⠖', lang='cs')  # decimal point
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', u'⠼⠒⠨⠶⠖', lang='cs')  # decimal point
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1,378</mn></mrow>
</math>''', u'⠼⠂⠠⠒⠶⠦', lang='en')  # comma
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', u'⠼⠒⠨⠶⠖', lang='en')  # decimal point
        # §9
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>27</mn></mrow>
</math>''', u'⠼⠆⠶')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>7</mn></mrow>
</math>''', u'⠠⠐⠮⠀⠶⠀⠼⠶⠀⠃⠁⠇⠇⠎⠲', lang='en2', pre="There were ", post=" balls.")
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mi>x</mi><mo>+</mo><mi>y</mi><mo>=</mo><mn>0</mn></mrow>
</math>''', u'⠼⠂⠬⠭⠬⠽⠀⠨⠅⠀⠼⠴')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>y</mi><mo>=</mo><mn>2</mn><mi>sin</mi><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', u'⠽⠀⠨⠅⠀⠼⠆⠎⠊⠝⠀⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mn>1</mn></mrow>
</math>''', u'⠎⠊⠝⠀⠼⠂')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>sin</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mn>2</mn><mi>x</mi></mrow>
</math>''', u'⠎⠊⠝⠘⠆⠀⠼⠆⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>0.333</mn><mo>&hellip;</mo><mn>3</mn><mo>&hellip;</mo></mrow>
</math>''', u'⠼⠴⠨⠒⠒⠒⠀⠄⠄⠄⠀⠼⠒⠀⠄⠄⠄', lang='en')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>log</mi><mn>10</mn></msub><mo>&ApplyFunction;</mo><mn>2</mn></mrow>
</math>''', u'⠇⠕⠛⠂⠴⠀⠼⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&angle;</mo><mn>1</mn></mrow>
</math>''', u'⠫⠪⠀⠼⠂')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>x</mi><mo>=</mo><mn>0</mn><mo>)</mo></mrow>
</math>''', u'⠷⠭⠀⠨⠅⠀⠼⠴⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>-1</mn></mrow>
</math>''', u'⠤⠼⠂')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>-.3</mn></mrow>
</math>''', u'⠤⠼⠨⠒')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="|" close="|" separators=","><mtable>
 <mtr><mtd><mn>1</mn></mtd><mtd><mn>2</mn></mtd></mtr>
 <mtr><mtd><mn>-3</mn></mtd><mtd><mn>-4</mn></mtd></mtr>
</mtable></mfenced></math>''', u'⠠⠳⠼⠂⠀⠀⠼⠆⠀⠠⠳\n⠠⠳⠤⠼⠒⠀⠤⠼⠲⠠⠳')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3</mn><mo>#</mo><mn>4</mn></mrow>
</math>''', u'⠼⠒⠨⠼⠼⠲')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3</mn><mo>*</mo><mn>4</mn></mrow>
</math>''', u'⠼⠒⠈⠼⠼⠲')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn mathvariant="italic">3</mn></mrow>
</math>''', u'⠨⠼⠒')
        # §11
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>[</mo><mn>0</mn><mo>,</mo><mn>1</mn><mo>]</mo></mrow>
</math>''', u'⠈⠷⠴⠠⠀⠂⠈⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="[" close="]" separators=","><mn>0</mn><mn>1</mn></mfenced></mrow>
</math>''', u'⠈⠷⠴⠠⠀⠂⠈⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
  <mrow><mn>1</mn><mo>+</mo><mi>h</mi></mrow>
  <mrow><mn>2</mn><mo>+</mo><mi>k</mi></mrow>
  <mrow><mn>0</mn></mrow>
</mfenced></mrow></math>''', u'⠷⠂⠬⠓⠠⠀⠆⠬⠅⠠⠀⠴⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
 <mrow><mn>0</mn></mrow><mrow><mo>-</mo><mn>1</mn></mrow><mrow><mo>&PlusMinus;</mo><mn>2</mn></mrow>
</mfenced></mrow></math>''', u'⠷⠴⠠⠀⠤⠂⠠⠀⠬⠤⠆⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
  <mrow><mn>2</mn><mi>sin</mi><mo>&ApplyFunction;</mo><mn>30</mn><mo>°</mo></mrow>
  <mrow><mn>3</mn><mi>cos</mi><mo>&ApplyFunction;</mo><mn>60</mn><mo>°</mo></mrow>
</mfenced></mrow></math>''', u'⠷⠆⠎⠊⠝⠀⠼⠒⠴⠘⠨⠡⠠⠀⠒⠉⠕⠎\n⠀⠀⠼⠖⠴⠘⠨⠡⠐⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
  <mrow><mi>x</mi></mrow><mrow><mn>7</mn></mrow><mrow><mn mathvariant="bold">8</mn></mrow>
  <mrow><mi>y</mi></mrow>
</mfenced></mrow></math>''', u'⠷⠭⠠⠀⠶⠠⠀⠸⠼⠦⠠⠀⠽⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&pi;</mi><mo>=</mo><mn>3,14159 26535</mn><mo>&hellip;</mo></mrow>
</math>''', u'⠨⠏⠀⠨⠅⠀⠼⠒⠨⠂⠲⠂⠢⠔⠀⠆⠖⠢⠒⠢\n⠀⠀⠄⠄⠄')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&pi;</mi><mo>=</mo><mn>3,14159 26535 9</mn></mrow>
</math>''', u'⠨⠏⠀⠨⠅⠀⠼⠒⠨⠂⠲⠂⠢⠔⠀⠆⠖⠢⠒⠢\n⠀⠀⠼⠔')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>2</mn></msup></mrow>
</math>''', u'⠭⠘⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><mrow><mn>3</mn></mrow><mrow><mi>x</mi></mrow></mfrac>
</math>''', u'⠹⠒⠌⠭⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>-</mo><mn>5</mn></mrow>
</math>''', u'⠭⠤⠢')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>2</mn><mo>&times;</mo><mn>4</mn></mrow>
</math>''', u'⠼⠆⠈⠡⠲')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mn>10,000</mn>
</math>''', u'⠼⠂⠴⠠⠴⠴⠴', lang='en')  # comma
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="|" close="|" separators=","><mrow><mo>-</mo><mn>3</mn></mrow></mfenced>
</math>''', u'⠳⠤⠒⠳')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="|" close="|" separators=","><mrow><mn>-3</mn></mrow></mfenced>
</math>''', u'⠳⠤⠒⠳')
        # §24
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mi>&alpha;</mi>
</math>''', u'⠨⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mi>&Sigma;</mi>
</math>''', u'⠨⠠⠎')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>&alefsym;</mi><mn>0</mn></msub>
</math>''', u'⠠⠠⠁⠴')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&alpha;</mi><mi>&beta;</mi></mrow>
</math>''', u'⠨⠁⠨⠃')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&alpha;&beta;</mi></mrow>
</math>''', u'⠨⠁⠨⠃')
        # §25
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mo>&prime;</mo></msup><mo>,</mo><msup><mi>x</mi><mo>&Prime;</mo></msup>
<mo>,</mo><msub><mi>x</mi><mn>1</mn></msub><mo>,</mo><msub><mi>x</mi><mi>a</mi></msub><mo>,</mo>
<msup><mi>x</mi><mn>2</mn></msup><mo>,</mo><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover>
</mrow>
</math>''', u'⠭⠄⠠⠀⠭⠄⠄⠠⠀⠭⠂⠠⠀⠭⠰⠁⠠⠀⠭⠘⠆⠠⠀⠭⠱', page_width=True)
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow>
</math>''', u'⠭⠬⠽')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>cd</mi></mrow>
</math>''', u'⠰⠉⠙⠀⠊⠎⠀⠏⠜⠁⠇⠇⠑⠇⠀⠞⠕⠀', lang='en2', post=' is parallel to ')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>e</mi><mi>f</mi></mrow>
</math>''', u'⠀⠊⠎⠀⠏⠜⠁⠇⠇⠑⠇⠀⠞⠕⠀⠑⠋⠸⠲', lang='en2', pre=' is parallel to ', post='.')
        # §26
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi mathvariant="bold">A</mi><mi mathvariant="bold">B</mi></mrow>
</math>''', u'⠸⠰⠠⠁⠸⠰⠠⠃')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi mathvariant="italic">a</mi><mi mathvariant="italic">b</mi></mrow>
</math>''', u'⠨⠰⠁⠨⠰⠃')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=","><mi>a</mi><mrow><mn>2</mn><mi>x</mi></mrow>
<mrow><mi>y</mi><mo>=</mo><mi>z</mi></mrow></mfenced>
</math>''', u'⠷⠰⠁⠠⠀⠼⠆⠭⠠⠀⠽⠀⠨⠅⠀⠵⠾')
        # §27
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>cos</mi><mo>&ApplyFunction;</mo><mi>A</mi></mrow>
</math>''', u'⠉⠕⠎⠀⠠⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>arc</mi><mo>&ApplyFunction;</mo><mi>a</mi><mi>b</mi></mrow>
</math>''', u'⠁⠗⠉⠀⠁⠃')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>e</mi><mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mi>x</mi></mrow></msup></mrow>
</math>''', u'⠑⠘⠎⠊⠝⠀⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&angle;</mo><mi>a</mi></mrow>
</math>''', u'⠫⠪⠀⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&triangle;</mo><mi>a</mi><mi>c</mi><mi>r</mi></mrow>
</math>''', u'⠫⠞⠀⠁⠉⠗')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>&#x25FD;</mo><mi>y</mi></mrow>
</math>''', u'⠭⠀⠫⠲⠀⠽')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>|</mo><mtable><mtr><mtd><mi>a</mi></mtd><mtd><mi>b</mi></mtd><mtd><mi>c</mi></mtd></mtr>
<mtr><mtd><mi>d</mi></mtd><mtd><mi>e</mi></mtd><mtd><mi>f</mi></mtd></mtr>
<mtr><mtd><mi>g</mi></mtd><mtd><mi>h</mi></mtd><mtd><mi>i</mi></mtd></mtr></mtable><mo>|</mo></mrow>
</math>''', u'⠠⠳⠁⠀⠃⠀⠉⠠⠳\n⠠⠳⠙⠀⠑⠀⠋⠠⠳\n⠠⠳⠛⠀⠓⠀⠊⠠⠳')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=","><mn>0</mn><mi>a</mi><mn>1</mn><mi>b</mi><mn>2</mn>
</mfenced>
</math>''', u'⠷⠴⠠⠀⠁⠠⠀⠂⠠⠀⠃⠠⠀⠆⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="{" close="}" separators=","><mi>a</mi><mi>b</mi><mi>c</mi><mi>d</mi>
</mfenced>
</math>''', u'⠨⠷⠁⠠⠀⠃⠠⠀⠉⠠⠀⠙⠨⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=",">
<mrow><mi>a</mi><mi>b</mi></mrow><mrow><mi>c</mi><mi>d</mi></mrow><mrow><mi>e</mi><mi>f</mi></mrow>
</mfenced>
</math>''', u'⠷⠁⠃⠠⠀⠉⠙⠠⠀⠑⠋⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=","><mi>a</mi><mrow><mn>2</mn><mi>x</mi></mrow><mi>b</mi>
</mfenced>
</math>''', u'⠷⠁⠠⠀⠆⠭⠠⠀⠃⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>a</mi><mi>cos</mi><mo>&ApplyFunction;</mo><mi>B</mi></mrow>
</math>''', u'⠁⠉⠕⠎⠀⠠⠃')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>m</mi><mo>&angle;</mo><mi>b</mi></mrow>
</math>''', u'⠍⠫⠪⠀⠃')
        # §28
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="" close="" separators=",">
<mfenced open="|" close="|"><mi>x</mi></mfenced>
<mfenced open="[" close="]"><mi>x</mi></mfenced>
<mfenced open="&DoubleVerticalBar;" close="&DoubleVerticalBar;"><mi>f</mi></mfenced>
</mfenced>
</math>''', u'⠳⠭⠳⠠⠀⠈⠷⠭⠈⠾⠠⠀⠳⠳⠋⠳⠳')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>a</mi><mi>b</mi><mo>)</mo><mo>+</mo><mo>(</mo><mi>c</mi><mi>d</mi><mo>)</mo>
</mrow>
</math>''', u'⠷⠁⠃⠾⠬⠷⠉⠙⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>j</mi><mo>=</mo><mn>1</mn><mo>,</mo><mn>2</mn><mo>,</mo><mo>&hellip;</mo>
<mo>,</mo><mi>n</mi><mo>)</mo></mrow>
</math>''', u'⠷⠚⠀⠨⠅⠀⠼⠂⠠⠀⠼⠆⠠⠀⠄⠄⠄⠠⠀⠰⠝⠾', page_width=True)
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>a</mi><mi>b</mi><mo>=</mo><mi>c</mi><mi>d</mi><mo>)</mo></mrow>
</math>''', u'⠷⠁⠃⠀⠨⠅⠀⠉⠙⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msubsup><mrow><mi>s</mi><mo>]</mo></mrow><mi>a</mi><mi>b</mi></msubsup></mrow>
</math>''', u'⠎⠈⠾⠰⠁⠘⠃')
        # §32
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn mathvariant="bold">0</mn></mrow>
</math>''', u'⠸⠼⠴')
        # §37
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>1</mn><mn>2</mn></mfrac></mrow>
</math>''', u'⠹⠂⠌⠆⠼⠠', lang='en2', post=',')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>3</mn><mn>4</mn></mfrac></mrow>
</math>''', u'⠹⠒⠌⠲⠼⠸⠲', lang='en2', post='.')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>0</mn></mrow>
</math>''', u'⠼⠴⠸⠲', lang='en2', post='.')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>c</mi></mrow>
</math>''', u'⠰⠉⠸⠲', lang='en2', post='.')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo lspace="0" rspace="0">&square;</mo><mo>+</mo>
<mo lspace="0" rspace="0">&bigcirc;</mo><mo>=</mo><mo>&bigtriangleup;</mo></mrow>
</math>''', u'⠦⠫⠲⠬⠫⠉⠀⠨⠅⠀⠫⠞⠸⠴', lang='en2', pre=u'“', post=u'”')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>sin</mi></mrow>
</math>''', u'⠦⠎⠊⠝⠸⠴', lang='en2', pre=u'“', post=u'”')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>0</mn></mrow>
</math>''', u'⠼⠴⠠⠸⠴', lang='en2', post=u',”')
        # §42
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mo>&mdash;</mo><mn>15</mn></mfrac><mo>=</mo><mfrac><mn>2</mn><mn>3</mn></mfrac></mrow>
</math>''', u'⠹⠤⠤⠤⠤⠀⠌⠂⠢⠼⠀⠨⠅⠀⠹⠆⠌⠒⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=","><mo>&mdash;</mo><mn>4</mn><mn>6</mn><mn>8</mn>
<mo>&mdash;</mo></mfenced></mrow>
</math>''', u'⠷⠤⠤⠤⠤⠠⠀⠲⠠⠀⠖⠠⠀⠦⠠⠀⠤⠤⠤⠤⠾', page_width=True)
        # §43
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>+</mo><mi>y</mi><mo>+</mo><mi>&hellip;</mi></mrow>
</math>''', u'⠭⠬⠽⠬⠀⠄⠄⠄⠸⠲', lang='en2', post='.')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="" close="" separators=","><mn>1</mn><mn>3</mn><mn>5</mn><mo>&hellip;</mo>
<mn>15</mn></mfenced></mrow>
</math>''', u'⠼⠂⠠⠀⠼⠒⠠⠀⠼⠢⠠⠀⠄⠄⠄⠠⠀⠼⠂⠢⠸⠲', lang='en2', post='.', page_width=True)
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow>
<msup><msub><mi>p</mi><mn>1</mn></msub><msub><mi>&alpha;</mi><mn>1</mn></msub></msup>
<mo>&hellip;</mo>
<msup><msub><mi>p</mi><mi>r</mi></msub><msub><mi>&alpha;</mi><mi>r</mi></msub></msup>
</mrow>
</math>''', u'⠏⠂⠘⠨⠁⠘⠰⠂⠐⠄⠄⠄⠀⠏⠰⠗⠘⠨⠁⠘⠰⠗', page_width=True)
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=","><mo>&hellip;</mo><mn>-1</mn><mn>0</mn><mn>1</mn>
<mo>&hellip;</mo></mfenced></mrow>
</math>''', u'⠷⠄⠄⠄⠠⠀⠤⠂⠠⠀⠴⠠⠀⠂⠠⠀⠄⠄⠄⠾')
        # §57
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>?</mo><mo>+</mo><mo>?</mo><mo>=</mo><mn>10</mn></mrow>
</math>''', u'⠿⠬⠿⠀⠨⠅⠀⠼⠂⠴')
        # §62
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>1</mn><mn>3</mn></mfrac></mrow>
</math>''', u'⠹⠂⠌⠒⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mrow><mi>a</mi><mo>+</mo><mi>b</mi></mrow><mi>c</mi></mfrac></mrow>
</math>''', u'⠹⠁⠬⠃⠌⠉⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><msup><mi>x</mi><mfrac><mn>1</mn><mn>2</mn></mfrac></msup><mn>2</mn></mfrac></mrow>
</math>''', u'⠹⠭⠘⠹⠂⠌⠆⠼⠐⠌⠆⠼')
        # §64
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>4</mn><mfrac><mn>3</mn><mn>8</mn></mfrac></mrow>
</math>''', u'⠼⠲⠸⠹⠒⠌⠦⠸⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mfrac><mn>3</mn><mn>8</mn></mfrac></mrow>
</math>''', u'⠭⠹⠒⠌⠦⠼')
        # §65
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mfrac><mn>3</mn><mn>8</mn></mfrac><mn>5</mn></mfrac></mrow>
</math>''', u'⠠⠹⠹⠒⠌⠦⠼⠠⠌⠢⠠⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>5</mn><mrow><mn>4</mn><mfrac><mn>3</mn><mn>8</mn></mfrac></mrow></mfrac></mrow>
</math>''', u'⠠⠹⠢⠠⠌⠲⠸⠹⠒⠌⠦⠸⠼⠠⠼')
        # §67
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><mi>a</mi><msup><mi>b</mi>
<mfrac><mfrac><mn>3</mn><mn>4</mn></mfrac><mfrac><mn>5</mn><mn>6</mn></mfrac></mfrac></msup></mfrac>
</math>''', u'⠹⠁⠌⠃⠘⠠⠹⠹⠒⠌⠲⠼⠠⠌⠹⠢⠌⠖⠼⠠⠼⠐⠼', page_width=True)
        # §74
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mn>2</mn></msup>
</math>''', u'⠭⠘⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mo>*</mo></msup>
</math>''', u'⠭⠘⠈⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mn>-2</mn></msup>
</math>''', u'⠭⠘⠤⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mi>a</mi></msub>
</math>''', u'⠭⠰⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mn>-2</mn></msub>
</math>''', u'⠭⠰⠤⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>n</mi><msup><mi>x</mi><mi>y</mi></msup></msup>
</math>''', u'⠝⠘⠭⠘⠘⠽')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><msup><mi>n</mi><mi>a</mi></msup></msub>
</math>''', u'⠭⠰⠝⠰⠘⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><msub><mi>y</mi><msup><mi>a</mi><mi>n</mi></msup></msub></msup>
</math>''', u'⠭⠘⠽⠘⠰⠁⠘⠰⠘⠝')
        # §77
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mn>1</mn></msub>
</math>''', u'⠭⠂')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mn>11</mn></msub>
</math>''', u'⠭⠂⠂')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><msup><mi>x</mi><mo>&prime;</mo></msup><mn>1</mn></msub>
</math>''', u'⠭⠄⠂')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><msub><mi>i</mi><mn>1</mn></msub></msub>
</math>''', u'⠭⠰⠊⠰⠰⠂')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>log</mi><mn>2</mn></msub><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', u'⠇⠕⠛⠆⠀⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mn>12</mn><mn>7</mn></msub>
</math>''', u'⠼⠂⠆⠰⠶')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mrow><mo>(</mo><mi>C</mi><msub><mi>O</mi><mn>3</mn></msub><mo>)</mo></mrow><mi>2</mi></msub>
</math>''', u'⠷⠠⠉⠠⠕⠒⠾⠰⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>Na</mi><mn>2</mn></msub><mi>C</mi><msub><mi>O</mi><mn>3</mn></msub></mrow>
</math>''', u'⠠⠝⠁⠆⠠⠉⠠⠕⠒')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>seven</mi><mn>3</mn></msub>
</math>''', u'⠎⠑⠧⠑⠝⠰⠒')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msubsup><mo>&Sum;</mo><mn>0</mn><mi>n</mi></msubsup><msub><mi>a</mi><mi>k</mi></msub></mrow>
</math>''', u'⠨⠠⠎⠴⠘⠝⠐⠁⠰⠅')
        # §78
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mfenced open="" close="" separators=","><mi>i</mi><mi>j</mi><mi>k</mi></mfenced>
</msub>
</math>''', u'⠭⠰⠊⠪⠚⠪⠅')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mfenced open="(" close=")" separators=","><mi>a</mi><mi>b</mi></mfenced></msub>
</math>''', u'⠭⠰⠷⠁⠪⠃⠾')
        # §79
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>x</mi><mi>a</mi></msub><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mrow>
</math>''', u'⠭⠰⠁⠐⠬⠽⠘⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><msup><mi>e</mi><msup><mi>x</mi><mn>2</mn></msup></msup><mn>2</mn></mfrac>
</math>''', u'⠹⠑⠘⠭⠘⠘⠆⠐⠌⠆⠼')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mn>2</mn></msup>
</math>''', u'⠭⠘⠆⠸⠲', lang='en2', post='.')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>2</mn></msup><mo>,</mo><msup><mi>x</mi><mn>3</mn></msup></mrow>
</math>''', u'⠭⠘⠆⠠⠀⠭⠘⠒')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>10,000</mn></msup></mrow>
</math>''', u'⠭⠘⠂⠴⠠⠴⠴⠴', lang='en2')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mrow><mi>i</mi><mo>,</mo><mi>j</mi></mrow></msub>
</math>''', u'⠭⠰⠊⠪⠚')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>P</mi><mfenced open="" close="" separators=",">
<msub><mi>n</mi><mn>1</mn></msub><msub><mi>n</mi><mn>2</mn></msub><mo>&hellip;</mo></mfenced></msub>
</math>''', u'⠠⠏⠰⠝⠰⠰⠂⠰⠪⠝⠰⠰⠆⠰⠪⠀⠄⠄⠄')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>b</mi><mrow><mo>&triangle;</mo><mi>A</mi><mi>B</mi><mi>C</mi></mrow></msub>
</math>''', u'⠃⠰⠫⠞⠀⠠⠁⠠⠃⠠⠉')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>cos</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', u'⠉⠕⠎⠘⠆⠀⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>e</mi><mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mi>x</mi><mo>+</mo>
<mi>i</mi><mi>cos</mi><mo>&ApplyFunction;</mo><mi>x</mi></mrow></msup>
</math>''', u'⠑⠘⠎⠊⠝⠀⠭⠬⠊⠉⠕⠎⠀⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>e</mi><mrow><msup><mi>sin</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mi>x</mi>
<mo>+</mo><msup><mi>sin</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mi>y</mi></mrow></msup>
</math>''', u'⠑⠘⠎⠊⠝⠘⠘⠆⠀⠭⠬⠎⠊⠝⠘⠘⠆⠀⠽')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>s</mi><mn>1</mn></msub><mo>&hellip;</mo><msub><mi>s</mi><mi>n</mi></msub></mrow>
</math>''', u'⠎⠂⠀⠄⠄⠄⠀⠎⠰⠝')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup><mo>+</mo>
<msup><mi>z</mi><mn>2</mn></msup><mo>=</mo><msup><mi>r</mi><mn>2</mn></msup></mrow>
</math>''', u'⠭⠘⠆⠐⠬⠽⠘⠆⠐⠬⠵⠘⠆⠀⠨⠅⠀⠗⠘⠆', page_width=True)
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>q</mi><mrow><msub><mi>log</mi><mi>q</mi></msub><mo>&ApplyFunction;</mo><mi>a</mi>
</mrow></msup><mo>=</mo><mi>a</mi></mrow>
</math>''', u'⠟⠘⠇⠕⠛⠘⠰⠟⠀⠁⠀⠨⠅⠀⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mrow><mo>(</mo><mn>1</mn><mo>-</mo><msup><mi>sin</mi><mn>2</mn></msup>
<mo>&ApplyFunction;</mo><mi>x</mi><mo>)</mo></mrow><mi>2</mi></msup><mo>=</mo>
<msup><mi>cos</mi><mn>4</mn></msup><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', u'⠷⠂⠤⠎⠊⠝⠘⠆⠀⠭⠾⠘⠆⠀⠨⠅⠀⠉⠕⠎⠘⠲⠀⠭', page_width=True)
        # §81
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><msub><mi>x</mi><mn>1</mn></msub><msub><mi>y</mi><mn>1</mn></msub><mo>+</mo>
<msub><mi>x</mi><mn>2</mn></msub><msub><mi>y</mi><mn>2</mn></msub><mo>)</mo></mrow>
</math>''', u'⠷⠭⠂⠽⠂⠬⠭⠆⠽⠆⠾')
        # §83
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mo>&prime;</mo></msup>
</math>''', u'⠭⠄')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msubsup><mi>x</mi><mi>a</mi><mo>&prime;</mo></msubsup>
</math>''', u'⠭⠄⠰⠁')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mrow><mo>&prime;</mo><mn>2</mn></mrow></msup>
</math>''', u'⠭⠄⠘⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msubsup><mi>x</mi><mi>a</mi><mrow><mo>&prime;</mo><mi>b</mi></mrow></msubsup>
</math>''', u'⠭⠄⠰⠁⠘⠃')
        # §86
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<munder accentunder="true"><mi>x</mi><mo>&macr;</mo></munder>
</math>''', u'⠐⠭⠩⠱⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><mrow><mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow></mrow><mo>&macr;</mo></mover>
</math>''', u'⠐⠭⠬⠽⠣⠱⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><munder accentunder="true"><mi>lim</mi><mrow><mi>x</mi><mo>&rarr;</mo><mn>0</mn></mrow>
</munder><mo>&ApplyFunction;</mo>
<mi>f</mi><mfenced open="(" close=")" separators=","><mrow><mi>x</mi></mrow></mfenced>
</mrow>
</math>''', u'⠐⠇⠊⠍⠩⠭⠀⠫⠕⠀⠼⠴⠻⠀⠋⠷⠭⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><msup><mi>x</mi><mn>2</mn></msup><mo>&macr;</mo></mover>
</math>''', u'⠐⠭⠘⠆⠐⠣⠱⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><msup><mi>x</mi><mo>&prime;</mo></msup><mo>&macr;</mo></mover>
</math>''', u'⠐⠭⠄⠣⠱⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><msub><mi>x</mi><mn>1</mn></msub><mo>&macr;</mo></mover>
</math>''', u'⠐⠭⠂⠣⠱⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><mi>x</mi><mo>&macr;</mo></mover>
</math>''', u'⠭⠱')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover><mo>+</mo>
<mover accent="true"><mi>y</mi><mo>&macr;</mo></mover></mrow>
</math>''', u'⠭⠱⠬⠽⠱')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover><mn>2</mn></msup>
</math>''', u'⠭⠱⠘⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover><mo>&prime;</mo></msup>
</math>''', u'⠭⠱⠄')
        # §88
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<munderover><mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow><mo>&macr;</mo><mo>&macr;</mo></munderover>
</math>''', u'⠐⠭⠬⠽⠩⠱⠣⠱⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><munderover><mo>&Sum;</mo><mrow><mi>n</mi><mo>=</mo><mn>1</mn></mrow><mo>&infin;</mo>
</munderover><mfrac><mrow><mn>1</mn></mrow><mrow><msup><mn>2</mn><mi>n</mi></msup></mrow></mfrac>
<mo>=</mo><mn>1</mn></mrow>
</math>''', u'⠐⠨⠠⠎⠩⠝⠀⠨⠅⠀⠼⠂⠣⠠⠿⠻⠹⠂⠌⠆⠘⠝⠐⠼⠀⠨⠅⠀⠼⠂', page_width=True)
        # §90
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mfrac linethickness="0"><mi>n</mi><mi>k</mi></mfrac><mo>)</mo></mrow>
</math>''', u'⠷⠝⠩⠅⠾')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mfrac linethickness="0"><msub><mi>g</mi><mi>j</mi></msub><msub><mi>a</mi><mi>j</mi>
</msub></mfrac><mo>)</mo></mrow>
</math>''', u'⠷⠛⠰⠚⠐⠩⠁⠰⠚⠐⠾')
        # §91
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>A</mi><mrow><mover><mi>x</mi><mo>~</mo></mover><mo>+</mo><mover><mi>y</mi><mo>~</mo>
</mover></mrow></msub>
</math>''', u'⠠⠁⠰⠐⠭⠣⠈⠱⠻⠬⠰⠐⠽⠣⠈⠱⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>A</mi><mrow><mover><mi>x</mi><mo>&macr;</mo></mover><mo>+</mo><mover><mi>y</mi>
<mo>&macr;</mo></mover></mrow></msub>
</math>''', u'⠠⠁⠰⠭⠱⠬⠽⠱')
        # §96
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><mrow><mrow><mi>A</mi><mi>B</mi></mrow></mrow><mo>&rarr;</mo></mover>
</math>''', u'⠐⠠⠁⠠⠃⠣⠫⠕⠻')
        # §97
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.57</mn><mover><mn>29</mn><mo>&macr;</mo></mover></mrow>
</math>''', u'⠼⠒⠨⠢⠶⠐⠆⠔⠣⠱⠻')
        # §103
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msqrt><mn>2</mn></msqrt>
</math>''', u'⠜⠆⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msqrt><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><mn>1</mn></msqrt>
</math>''', u'⠜⠭⠘⠆⠐⠬⠂⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mroot><mrow><mn>2</mn></mrow><mrow><mn>3</mn></mrow></mroot>
</math>''', u'⠣⠒⠜⠆⠻')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mroot><mrow><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><mroot><mrow>
<msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mrow><mrow>
<mn>3</mn></mrow></mroot><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mrow><mrow><mn>3</mn></mrow>
</mroot>
</math>''', u'⠣⠒⠜⠭⠘⠆⠐⠬⠨⠣⠒⠜⠭⠘⠆⠐⠬⠽⠘⠆⠐⠨⠻⠬⠽⠘⠆⠐⠻', page_width=True)
        # §138
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>=</mo><mo>-</mo><mi>y</mi></mrow>
</math>''', u'⠭⠀⠨⠅⠀⠤⠽')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mo>-</mo><mi>x</mi></mrow>
</math>''', u'⠎⠊⠝⠀⠤⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mn>2</mn><mo>+</mo><mo>&hellip;</mo><mo>+</mo><mi>n</mi></mrow>
</math>''', u'⠼⠂⠬⠆⠬⠀⠄⠄⠄⠀⠬⠝')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mi mathvariant="normal">yd</mi><mo>+</mo>
<mn>2</mn><mi mathvariant="normal">yd</mi><mo>=</mo>
<mn>3</mn><mi mathvariant="normal">yd</mi></mrow>
</math>''', u'⠼⠂⠀⠽⠙⠀⠬⠆⠀⠽⠙⠀⠨⠅⠀⠼⠒⠀⠽⠙', page_width=True)
        # §169
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>n</mi><mo>!</mo></mrow>
</math>''', u'⠝⠯')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&forall;</mo><mi>x</mi><mo>&isin;</mo><mi>A</mi></mrow>
</math>''', u'⠈⠯⠭⠀⠈⠑⠀⠠⠁')
        # §177
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mn>5</mn></mrow>
</math>''', u'⠭⠐⠢')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>c</mi><mn>0</mn></msub><msup><mn>10</mn><mn>2</mn></msup><mo>+</mo>
<msub><mi>c</mi><mn>1</mn></msub><mn>10</mn><mo>+</mo><msub><mi>c</mi><mn>2</mn></msub></mrow>
</math>''', u'⠉⠴⠐⠂⠴⠘⠆⠐⠬⠉⠂⠐⠂⠴⠬⠉⠆')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>|</mo><mi>x</mi><mo>|</mo><mo>|</mo><mi>y</mi><mo>|</mo></mrow>
</math>''', u'⠳⠭⠳⠐⠳⠽⠳')
        # §178
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mstack>
<mn>508</mn><mn>2876</mn><mn>59</mn><msrow><mo>+</mo><mn>427</mn></msrow><msline/><mn>3870</mn>
</mstack>
</math>''', u'⠀⠀⠀⠢⠴⠦\n⠀⠀⠆⠦⠶⠖\n⠀⠀⠀⠀⠢⠔\n⠀⠬⠀⠲⠆⠶\n⠒⠒⠒⠒⠒⠒⠒\n⠀⠀⠒⠦⠶⠴')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mstack>
<mn>35.50</mn><msrow><mo>+</mo><mn>77.25</mn></msrow><msline/><mn>112.75</mn>
</mstack>
</math>''', u'⠀⠀⠒⠢⠨⠢⠴\n⠀⠬⠶⠶⠨⠆⠢\n⠒⠒⠒⠒⠒⠒⠒⠒\n⠀⠂⠂⠆⠨⠶⠢')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mstack>
<mn>3.704</mn><msrow><mo>-</mo><mn>.915</mn></msrow><msline/><mn>2.789</mn>
</mstack>
</math>''', u'⠀⠀⠒⠨⠶⠴⠲\n⠀⠤⠀⠨⠔⠂⠢\n⠒⠒⠒⠒⠒⠒⠒⠒\n⠀⠀⠆⠨⠶⠦⠔')
        # §179
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mstack>
  <msgroup>
    <mn>23</mn>
    <msrow><mo>&times;</mo><mn>54</mn></msrow>
  </msgroup>
  <msline/>
  <msgroup shift="1">
    <mn>92</mn>
    <mn>115</mn>
  </msgroup>
  <msline/>
  <mn>1242</mn>
</mstack>
</math>''', u'⠀⠀⠀⠆⠒\n⠀⠈⠡⠢⠲\n⠒⠒⠒⠒⠒⠒\n⠀⠀⠀⠔⠆\n⠀⠂⠂⠢\n⠒⠒⠒⠒⠒⠒\n⠀⠂⠆⠲⠆', page_height=True)

    def test_mathml_nemeth_liblouis(self):
        # We don't aim to test correctness of liblouisutdml here, just that the
        # bindings to it work and that there is no big problem.
        def test(mathml, expected_result):
            content = lcg.MathML(mathml)
            presentation = self._load_presentation()
            presentation.braille_math_rules = 'nemeth-liblouis'
            presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
            n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                                content=content)
            exporter = lcg.BrailleExporter()
            context = exporter.context(n, lang='cs', presentation=presentation_set)
            exported = exporter.export(context)
            result = exported.replace('\r\n', '\n').split('\n\n')[1]
            assert result == expected_result, (
                "\n  - source text: %r\n  - expected:    %r\n  - got:         %r" %
                (mathml, expected_result, result))
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', u'⠼⠒⠨⠶⠖')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mi>x</mi><mo>+</mo><mi>y</mi><mo>=</mo><mn>0</mn></mrow>
</math>''', u'⠼⠂⠬⠭⠬⠽⠀⠨⠅⠀⠼⠴')
        # Of course, comma is not recognized as a decimal point, how could
        # liblouisutdml know about that?
#         test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
# <mrow><mn>3,76</mn></mrow>
# </math>''', u'⠼⠒⠨⠶⠖')
        # Doesn't work correctly in liblouisutdml:
#         test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
# <mrow><msub><mi>log</mi><mtext>10</mtext></msub><mn>2</mn></mrow>
# </math>''', u'⠇⠕⠛⠂⠴⠀⠼⠆')
        # Doesn't work correctly in liblouisutdml:
#         test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
# <mfrac><mfrac><mn>3</mn><mn>8</mn></mfrac><mn>5</mn></mfrac>
# </math>''', u'⠠⠹⠹⠒⠌⠦⠼⠠⠌⠢⠠⠼')


class PDFExport(unittest.TestCase):

    def test_export(self):
        # Just test for crashes
        path = os.path.join(lcg_dir, 'doc/src')
        name = 'structured-text'
        reader = lcg.reader(path, name, ext='txt', recourse=False)
        node = reader.build()
        exporter = lcg.PDFExporter()
        context = exporter.context(node, 'cs')
        exporter.export(context)


class Presentations(unittest.TestCase):

    def test_style_file(self):
        style_file = lcg.StyleFile()
        f = open(os.path.join(lcg_dir, 'styles', 'standard'))
        style_file.read(f)
        f.close()
        f = os.tmpfile()
        style_file.write(f)
        f.seek(0)
        style_file_2 = lcg.StyleFile()
        style_file_2.read(f)
        f.close()
        for pm_1, pm_2 in zip(style_file.presentations(), style_file_2.presentations()):
            p_1, p_2 = pm_1[0], pm_2[0]
            for attr in dir(p_1):
                if attr[0] in string.ascii_lowercase:
                    value_1, value_2 = getattr(p_1, attr), getattr(p_2, attr)
                    assert value_1 == value_2


if __name__ == '__main__':
    unittest.main()
