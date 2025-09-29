#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2004-2017 OUI Technology Ltd.
# Copyright (C) 2019-2025 Tomáš Cerha <t.cerha@gmail.com>
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
import tempfile
import warnings

from decimal import Decimal

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
translation_path = [os.path.join(os.path.normpath(os.path.dirname(__file__)), 'translations')]

if os.getenv('CI') == 'true' and repo_root in sys.path:
    # Make sure to import lcg from the installed package, not from the current directory
    # when running within a CI workflow
    sys.path.remove(repo_root)

import lcg
try:
    from matplotlib import pyplot
except ImportError:
    pyplot = None
else:
    import lcg.plot

_ = lcg.TranslatableTextFactory('test')
standard_library.install_aliases()
unistr = type('')  # Python 2/3 transition hack.
if sys.version_info[0] > 2:
    basestring = str


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
        with pytest.raises(TypeError):
            e = a + 1

    def test_concat(self):
        a = lcg.concat(lcg.TranslatableText("Version %s", "1.0") + 'xx', 'yy', separator="\n")
        assert isinstance(a, lcg.Concatenation)
        items = a.items()
        assert len(items) == 2
        assert items[1] == ('xx\nyy')
        b = lcg.concat('a', ('b', 'c', 'd'), 'e', 'f', separator='-')
        assert isinstance(b, unistr)
        assert b == 'a-b-c-d-e-f'
        c = lcg.concat('a', ('b', 'c', 'd'), 'e', 'f', separator='-')
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
        assert _.pgettext('noun', 'force').localize(cs) == 'síla'

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
        for n, translated in ((1, "Mám 1 problém."),
                              (2, "Mám 2 problémy."),
                              (5, "Mám 5 problémů.")):
            a = _.ngettext("I have %d problem.", "I have %d problems.", n)
            b = a.localize(loc)
            assert b == translated

    def test_interpolation(self):
        t = lcg.Localizer('cs', translation_path=translation_path)
        for n, translated in ((1, "1 záznam nalezen v tabulce xy."),
                              (2, "2 záznamy nalezeny v tabulce xy."),
                              (5, "5 záznamů nalezeno v tabulce xy.")):
            a = _.ngettext("%(n)d record found in table %(name)s.",
                           "%(n)d records found in table %(name)s.", n=n, name='xy')
            b = a.localize(t)
            assert b == translated

    def test_replace(self):
        loc = lcg.Localizer('cs', translation_path=translation_path)
        for n, ta, tb in ((1, "Mám 1 problém.", "1 záznam nalezen v tabulce xy."),
                          (2, "Mám 2 problémy.", "2 záznamy nalezeny v tabulce xy."),
                          (5, "Mám 5 problémů.", "5 záznamů nalezeno v tabulce xy.")):
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
        translations = {'cs': "%(person1)s je chytřejší než %(person2)s."}
        a = lcg.SelfTranslatableText(text, person1="Joe", person2="Ann", translations=translations)
        a2 = lcg.SelfTranslatableText(text, translations=translations)
        a3 = a2.interpolate(lambda key: '-' + key + '-')
        assert a.localize(lcg.Localizer()) == \
            "Joe is smarter than Ann."
        assert a.localize(lcg.Localizer('cs', translation_path=translation_path)) == \
            "Joe je chytřejší než Ann."
        assert a3.localize(lcg.Localizer()) == \
            "-person1- is smarter than -person2-."
        assert a3.localize(lcg.Localizer('cs', translation_path=translation_path)) == \
            "-person1- je chytřejší než -person2-."


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
                == "Čt 21.12.2006 18:43:32")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32), cs)
                == "21.12.2006 18:43:32")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32, tzinfo=utc), cs)
                == "21.12.2006 17:43:32")
        assert (localize("2006-01-30", cs, leading_zeros=False)
                == "30.1.2006")
        assert (localize(datetime.date(2006, 1, 30), cs, leading_zeros=False)
                == "30.1.2006")
        assert (localize("2006-12-21 18:43:32", cs, utc=True)
                == "21.12.2006 17:43:32")
        assert (localize(datetime.datetime(2006, 12, 21, 18, 43, 32), cs, utc=True)
                == "21.12.2006 17:43:32")

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


class TranslatedTextFactory(unittest.TestCase):

    def test_translated(self):
        cs = lcg.Localizer('cs', translation_path=translation_path)
        assert _.pgettext('verb', 'force').localize(cs) == 'donutit'
        __ = lcg.TranslatedTextFactory('test', lang='cs', translation_path=translation_path)
        assert __("Bob") == 'Bobik'
        assert __.pgettext('verb', 'force') == 'donutit'
        assert __.pgettext('noun', 'force') == 'síla'
        assert __.ngettext("I have %d problem.", "I have %d problems.", 1) == "Mám 1 problém."
        assert __.ngettext("I have %d problem.", "I have %d problems.", 4) == "Mám 4 problémy."
        assert __.ngettext("I have %d problem.", "I have %d problems.", 6) == "Mám 6 problémů."

    def test_datetime(self):
        __ = lcg.TranslatedTextFactory('test', lang='cs', translation_path=translation_path)
        dt = __.datetime(datetime.datetime(2024, 6, 11, 10, 44, 37), leading_zeros=False)
        assert dt == '11.6.2024 10:44:37'
        assert isinstance(dt, lcg.LocalizableDateTime)
        de = lcg.Localizer('en', translation_path=translation_path)
        assert dt.localize(de) == '11/6/2024 10:44:37 AM'


class Monetary(unittest.TestCase):

    def test_format(self):
        a = lcg.Monetary(8975.5)
        a1 = lcg.Localizer().localize(a)
        a2 = lcg.Localizer('cs').localize(a)
        a3 = lcg.Localizer('en').localize(a)
        assert a1 == '8975.50'
        assert a2 == '8\xa0975,50'
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
            "%(name1)s je chytřejší než %(name2)s."


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
        def warn(msg):
            messages.append(msg)

        messages= []
        p = lcg.ResourceProvider(resources=(lcg.Audio('xxx.ogg'),))
        r = p.resource('xxx.xx', warn=warn)
        assert r is None
        assert len(messages) == 1
        r = p.resource('xxx.mp3', warn=warn)
        assert r is None
        assert len(messages) == 2
        r = p.resource('xxx.ogg')
        assert isinstance(r, lcg.Audio)
        assert len(messages) == 2
        r = p.resource('default.css')
        assert isinstance(r, lcg.Stylesheet)
        assert len(messages) == 2

    def test_dependencies(self):
        p = lcg.ResourceProvider(resources=(lcg.Audio('sound1.ogg'),
                                            lcg.Audio('sound2.mp3', descr="Nice song")))
        a = lcg.ContentNode('a', content=lcg.Content(), resource_provider=p)
        b = lcg.ContentNode('b', content=lcg.Content(), resource_provider=p)
        assert a.resource('sound1.ogg') is not None
        assert a.resource('sound2.mp3').descr() == 'Nice song'
        assert len(p.resources()) == 2
        assert a.resource('default.css') is not None
        assert b.resource('non-existing-file.js') is None
        assert len(p.resources()) == 3
        assert tuple(r.filename() for r in a.resources()) == ('sound1.ogg', 'sound2.mp3',
                                                              'default.css')
        assert tuple(r.filename() for r in b.resources()) == ('sound1.ogg', 'sound2.mp3')


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

    def _unindent(self, text):
        return '\n'.join(line.lstrip() for line in text.splitlines())

    def _parse(self, text, **kwargs):
        return lcg.MacroParser(globals=kwargs).parse(text)

    def test_simple_condition(self):
        assert self._parse("@if x\nX\n@else\nY@endif\n", x=True) == "X\n"

    def test_condition(self):
        def test(condition, **kwargs):
            text = ("@if " + condition + "\nTrue\n@else\nFalse\n@endif")
            return self._parse(text, **kwargs).strip()
        # Some more complicated condition.
        c1 = "a in ('A', 'B', 'C') and b > 3 and b + 5 <= c and c is not None"
        assert test(c1, a='A', b=5, c=55) == 'True'
        assert test(c1, a='X', b=5, c=None) == 'False'
        # Try using builtins.
        c2 = "ord(a) == b and chr(b) == a and sum((b, c, 3)) >= 70 and any([True, False, a == b])"
        assert test(c2, a='A', b=65, c=2) == 'True'
        assert test(c2, a='X', b=5, c=2) == 'False'

    def test_exception(self):
        text = self._unindent("""
        A
        @if a//b == c
        X
        @else
        Y
        @endif

        B

        """)
        assert self._parse(text, a=5, b=0, c=2) == \
            "\nA\nZeroDivisionError: integer division or modulo by zero\nB\n\n"

    def test_condition_newlines(self):
        text = "A\n@if x\nX\n@endif\n\nB\n\n"
        assert self._parse(text, x=True) == "A\nX\n\nB\n\n"

    def test_nested_condition(self):
        text = self._unindent("""
        A
        @if b
        B
        @else
        @if c
        C
        @endif
        D
        @endif
        E
        """)
        assert self._parse(text, b=True, c=True).strip() == 'A\nB\nE'
        assert self._parse(text, b=False, c=True).strip() == 'A\nC\nD\nE'
        assert self._parse(text, b=False, c=False).strip() == 'A\nD\nE'

    def test_inclusion(self):
        self._parse("Foo\n@include bar\nBaz\n", bar='Bar') == "Foo\nBar\nBaz\n"


class HtmlImport(unittest.TestCase):

    def test_html(self):
        # This HTML preserves the formatting produced by ckeditor, only long lines are wrapped
        # in order to make Flycheck happy...
        html = ''' <p>some text
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

<div class="lcg-exercise" contenteditable="false" data-type="GapFilling"
     style="display: inline-block;">
<pre class="lcg-exercise-src">
If you want to send money to somebody, you can ____ a transfer.
- do
+ make
- have

To change money between two currencies you need to know the ____ rate.
- success
- interest
+ exchange
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
        assert g.script('x') == '<script type="text/javascript">x</script>'
        assert g.submit('x') == '<button type="submit">x</button>'
        assert g.form('x') == '<form action="#">x</form>'
        assert g.h('x', level=8) == '<h8>x</h8>'
        assert g.img('x') == '<img alt="" src="x"/>'
        assert g.iframe('x') == '<iframe src="x"><a href="x">x</a></iframe>'
        assert g.input(type='text') == '<input type="text"/>'
        assert g.field(name='a') == ('<input class="text" name="a" size="20" '
                                     'type="text" value=""/>')
        assert g.checkbox('a') == '<input name="a" type="checkbox"/>'
        assert g.hidden('a', 'x') == '<input name="a" type="hidden" value="x"/>'
        assert g.radio('a') == '<input name="a" type="radio"/>'
        assert g.upload('a') == '<input name="a" type="file"/>'
        assert g.audio('x') == '<audio controls="controls" src="x"/>'
        assert g.video('x') == '<video controls="controls" src="x"/>'
        assert g.source('x') == '<source src="x"/>'
        # Now test with *some* typical optional arguments.
        assert g.a('x', href='a') == '<a href="a">x</a>'
        assert g.a('x', name='a') == '<a name="a">x</a>'
        assert g.button('X', disabled=True) == '<button disabled="disabled">X</button>'
        # Testing backwards compatibility of deprecated select() arguemnts.
        assert g.select([], name='a') == '<select name="a"></select>'
        assert g.option('X', value='x') == '<option value="x">X</option>'
        assert g.option('X', value='x', disabled=True, cls='c') == (
            '<option class="c" disabled="disabled" value="x">X</option>')
        assert g.optgroup([], label='aa') == '<optgroup label="aa"></optgroup>'

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
             '<blockquote class="lcg-quotation"><p>blah</p></blockquote>'),
            (lcg.Quotation(lcg.TextContent("blah"), source='Hugo', uri='http://hugo.org'),
             ('<blockquote class="lcg-quotation">blah<footer>— '
              '<a href="http://hugo.org">Hugo</a></footer></blockquote>')),
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
              '<div class="wrapper" style="padding-bottom: 66.7%">'
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
             '<img alt="" class="lcg-image image-aa" src="images/aa.jpg"/>'),
            ('*[aa.jpg]*',
             '<strong><img alt="" class="lcg-image image-aa" src="images/aa.jpg"/></strong>'),
            ('[aa.jpg label]',
             '<img alt="label" class="lcg-image image-aa" src="images/aa.jpg"/>'),
            ('[aa.jpg:20x30 label]',
             ('<img alt="label" class="lcg-image image-aa"'
              ' src="images/aa.jpg" style="width: 20px; height: 30px;"/>')),
            ('[>aa.jpg]',
             ('<img align="right" alt="" class="lcg-image right-aligned image-aa"'
              ' src="images/aa.jpg"/>')),
            ('[<aa.jpg]',
             ('<img align="left" alt="" class="lcg-image left-aligned image-aa" '
              'src="images/aa.jpg"/>')),
            ('[aa.jpg label | descr]',
             '<img alt="label: descr" class="lcg-image image-aa" src="images/aa.jpg"/>'),
            ('[http://www.freebsoft.org/img/logo.gif Free(b)soft logo]',
             ('<img alt="Free(b)soft logo" class="lcg-image image-logo"'
              ' src="http://www.freebsoft.org/img/logo.gif"/>')),
            ('[cc.png]',
             '<img alt="Image C: Nice picture" class="lcg-image image-cc" src="images/cc.png"/>'),
            # Image links (links with an image instead of a label)
            ('[aa.jpg bb.jpg label | descr]',
             ('<a href="images/aa.jpg" title="descr">'
              '<img alt="label" class="lcg-image image-bb" src="images/bb.jpg"/></a>')),
            ('[aa.jpg bb.jpg | descr]',
             ('<a href="images/aa.jpg" title="descr">'
              '<img alt="" class="lcg-image image-bb" src="images/bb.jpg"/></a>')),
            ('[>aa.jpg bb.jpg label | descr]',
             ('<a href="images/aa.jpg" title="descr">'
              '<img align="right" alt="label"'
              ' class="lcg-image right-aligned image-bb" src="images/bb.jpg"/></a>')),
            ('[test bb.jpg bb]',
             ('<a href="test" title="Some description">'
              '<img alt="bb" class="lcg-image image-bb" src="images/bb.jpg"/></a>')),
            ('[http://www.freebsoft.org /img/logo.gif]',
             ('<a href="http://www.freebsoft.org">'
              '<img alt="" class="lcg-image image-logo" src="/img/logo.gif"/></a>')),
            ('[http://www.freebsoft.org /img/logo.gif Free(b)soft website]',
             ('<a href="http://www.freebsoft.org">'
              '<img alt="Free(b)soft website" class="lcg-image image-logo" src="/img/logo.gif"/>'
              '</a>')),
            (('[http://www.freebsoft.org /img/logo.gif Free(b)soft website | '
              'Go to Free(b)soft website]'),
             ('<a href="http://www.freebsoft.org" title="Go to Free(b)soft website">'
              '<img alt="Free(b)soft website" class="lcg-image image-logo" '
              'src="/img/logo.gif"/></a>')),
            # Absolute image links
            ('http://www.freebsoft.org/img/logo.gif',
             ('<img alt="" class="lcg-image image-logo"'
              ' src="http://www.freebsoft.org/img/logo.gif"/>')),
            # Audio player links
            ('[xx.mp3]',
             re.compile(r'<a class="media-control-link" href="media/xx.mp3"'
                        r' id="[a-z0-9-]+">xx.mp3</a>')),
            ('[/somewhere/some.mp3]',
             re.compile(r'<a class="media-control-link" href="/somewhere/some.mp3" id="[a-z0-9-]+"'
                        r'>/somewhere/some.mp3</a>')),
            # Internal Reference Links
            ('[text.txt]',
             '<a href="/resources/texts/text.txt">text.txt</a>'),
            ('[test]',
             '<a href="test" title="Some description">Test Node</a>'),
            ('[test#sec1]',
             '<a href="test#sec1">Section One</a>'),
            ('[#sec1]',
             '<a href="test#sec1">Section One</a>'),
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
        mathml = """
<math xmlns="http://www.w3.org/1998/Math/MathML">
  <mi>&#x03C0;<!-- π --></mi>
  <mo>&#x2062;&eplus;<!-- &InvisibleTimes; --></mo>
  <msup>
    <mi>r</mi>
    <mn>2</mn>
  </msup>
</math>"""
        content = lcg.MathML(mathml)
        assert export(content).replace('\n', '') == mathml.replace('\n', '')
        for xml in ('</math><math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>',
                    '<math xmlns="http://www.w3.org/1998/Math/MathML"><script>1</script></math>',
                    '<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>' +
                    '<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>',):
            content = lcg.MathML(xml)
            with pytest.raises(lcg.ParseError):
                export(content)
        mathml = '<math xmlns="http://www.w3.org/1998/Math/MathML"><mn>1</mn></math>'
        content = lcg.MathML(mathml)
        assert export(content).replace('\n', '') == mathml.replace('\n', '')

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
        assert pkg_opf.startswith(b'<?xml version="1.0"')


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
            ('abc', '⠁⠃⠉',),
            ('a a11a 1', '⠁⠀⠁⠼⠁⠁⠐⠁⠀⠼⠁',),
            ('*tučný*', '⠔⠰⠞⠥⠩⠝⠯⠰⠔',),
            ('/šikmý/', '⠔⠨⠱⠊⠅⠍⠯⠨⠔',),
            ('_podtržený_', '⠸⠏⠕⠙⠞⠗⠮⠑⠝⠯',),
            ('_hodně podtržený_', '⠔⠸⠓⠕⠙⠝⠣⠀⠏⠕⠙⠞⠗⠮⠑⠝⠯⠸⠔',),
            ('zkouška českého dělení slov', '⠵⠅⠕⠥⠱⠅⠁⠀⠩⠑⠎⠅⠜⠓⠕⠀⠙⠣⠤\n⠇⠑⠝⠌⠀⠎⠇⠕⠧',),
        ):
            self._test(text, braille, '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                       presentation, 'cs')
        tests = (('abc', '⠁⠃⠉',),
                 ('long line to be hyphenated', '⠇⠕⠝⠛⠀⠇⠊⠝⠑⠀⠞⠕⠀⠃⠑⠀⠓⠽⠤\n⠏⠓⠑⠝⠁⠞⠑⠙',),
                 ('*bold*', '⠸⠃⠕⠇⠙',),
                 ('/italic/', '⠨⠊⠞⠁⠇⠊⠉',),
                 ('_underlined_', '⠥⠝⠙⠑⠗⠇⠊⠝⠑⠙',),)
        if False:
            # buggy in current liblouis
            tests += (('a a11a 1', '⠁⠀⠁⠼⠁⠁⠐⠁⠀⠼⠁',),)
        for text, braille in tests:
            self._test(text, braille, '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                       presentation, 'en')

    def test_languages(self):
        presentation = self._load_presentation()
        self._test('řwe >>world<< řwe', '⠺⠷⠑⠀⠺⠕⠗⠇⠙⠀⠺⠷⠑', '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', 'en')

    def test_special_formatting(self):
        presentation = self._load_presentation()
        self._test('50 %, 12 ‰', '⠼⠑⠚⠼⠏⠂⠀⠼⠁⠃⠼⠗', '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                   presentation, 'cs')

    def test_tables(self):
        presentation = self._load_presentation()
        # Simple tables
        self._test('| first | line | x |\n| second | row | y |',
                   '⠋⠊⠗⠎⠞⠀⠀⠀⠇⠊⠝⠑⠀⠀⠭\n⠎⠑⠉⠕⠝⠙⠀⠀⠗⠕⠷⠀⠀⠀⠽',
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test('| *heading* | *h* | *h* |\n| first | line | x |\n| second | row | y |',
                   '⠓⠑⠁⠙⠊⠝⠛⠀⠀⠓⠀⠀⠀⠀⠀⠓\n⠋⠊⠗⠎⠞⠀⠀⠀⠀⠇⠊⠝⠑⠀⠀⠭\n⠎⠑⠉⠕⠝⠙⠀⠀⠀⠗⠕⠷⠀⠀⠀⠽',
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        # Compact wide tables
        self._test('| Narrow | Table |', '⠠⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test('| Less Narrow | Table |', '⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test('| Less Narrow | Table |\n| Less Narrow | Table |',
                   '⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑\n⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test('| *a* | *b* |\n| prefixed lines | table |\n| prefixed rows | cell |\n',
                   '⠏⠗⠑⠋⠊⠭⠑⠙⠀⠁⠀⠀⠃⠀⠀⠀⠀\n⠇⠊⠝⠑⠎⠀⠀⠀⠀⠀⠀⠀⠞⠁⠃⠇⠑\n⠗⠕⠷⠎⠀⠀⠀⠀⠀⠀⠀⠀⠉⠑⠇⠇⠀',
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test('| *a* | *b* |\n| line & suffix | table |\n| row & suffix | cell |\n',
                   '⠁⠀⠼⠯⠀⠎⠥⠋⠋⠊⠭⠀⠀⠃⠀⠀⠀⠀\n⠇⠊⠝⠑⠀⠀⠀⠀⠀⠀⠀⠀⠀⠞⠁⠃⠇⠑\n⠗⠕⠷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠑⠇⠇⠀',
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        # Double page tables
        self._test('| this is | a double page | table |\n| the | columns | are too wide |',
                   ('⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    '⠞⠓⠊⠎⠀⠊⠎⠀⠀⠁⠀⠙⠕⠥⠃⠇⠑⠀⠏⠁\n⠞⠓⠑⠀⠀⠀⠀⠀⠀⠉⠕⠇⠥⠍⠝⠎⠀⠀⠀⠀',
                    '⠛⠑⠀⠀⠞⠁⠃⠇⠑⠀⠀⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠁⠗⠑⠀⠞⠕⠕⠀⠷⠊⠙⠑',),
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   ('⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                    '⠼⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀',
                    '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠉',),
                   presentation, 'cs', full_parse=True)
        self._test(('some text\n\n'
                    '| this is | a double page | table |\n| the | columns | are too wide |\n\n'
                    'another text\n'),
                   ('⠎⠕⠍⠑⠀⠞⠑⠭⠞\n\n⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    '⠞⠓⠊⠎⠀⠊⠎⠀⠀⠁⠀⠙⠕⠥⠃⠇⠑⠀⠏⠁\n⠞⠓⠑⠀⠀⠀⠀⠀⠀⠉⠕⠇⠥⠍⠝⠎⠀⠀⠀⠀',
                    '⠛⠑⠀⠀⠞⠁⠃⠇⠑⠀⠀⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠁⠗⠑⠀⠞⠕⠕⠀⠷⠊⠙⠑',
                    '⠁⠝⠕⠞⠓⠑⠗⠀⠞⠑⠭⠞',),
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   ('⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                    '⠼⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀',
                    '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠉',
                    '⠼⠙⠀⠀⠀⠀⠀⠀⠀⠀⠀',),
                   presentation, 'cs', full_parse=True)
        # Super wide tables
        self._test('| extremely wide table | very very wide table |\n| next | line |',
                   ('⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎\n⠞⠗⠁⠝⠎⠏⠕⠎⠑⠙⠄\n\n⠠⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    '⠑⠭⠞⠗⠑⠍⠑⠇⠽⠀⠷⠊⠙⠑⠀⠞⠁⠃⠇⠑\n⠧⠑⠗⠽⠀⠧⠑⠗⠽⠀⠷⠊⠙⠑⠀⠞⠁⠃⠇⠑',
                    '⠀⠀⠝⠑⠭⠞\n⠀⠀⠇⠊⠝⠑',),
                   '⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   ('⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠁',
                    '⠼⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀',
                    '⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠼⠉',),
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
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3,14</mn></mrow>
</math>''', '⠼⠉⠂⠁⠙')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1 000,5</mn></mrow>
</math>''', '⠼⠁⠚⠚⠚⠂⠑')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mn>1</mn><mo>=</mo><mn>2</mn></mrow>
</math>''', '⠼⠁⠀⠲⠼⠁⠀⠶⠼⠃')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>a</mi><mo>=</mo><mo>-</mo><mn>7</mn></mrow>
</math>''', '⠁⠀⠶⠤⠼⠛')
        test('''<math display="block" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow>
  <mfrac>
    <mrow><mfrac><mrow><mn>1</mn></mrow><mrow><mn>2</mn></mrow></mfrac></mrow>
    <mrow><mfrac><mrow><mn>3</mn><mo>+</mo><mn>4</mn></mrow><mrow><mn>5</mn></mrow></mfrac></mrow>
  </mfrac>
</mrow>
</math>''', '''⠆⠆⠼⠁⠻⠼⠃⠰⠻⠻⠆⠼⠉⠀⠲⠼⠙⠻
⠻⠼⠑⠰⠰''')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn><mi>a</mi></mrow>
</math>''', '⠼⠁⠃⠐⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn></mrow><mrow><mi>a</mi></mrow>
</math>''', '⠼⠁⠃⠐⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn><mi>k</mi></mrow>
</math>''', '⠼⠁⠃⠅')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>12</mn></mrow><mrow><mi mathvariant="bold">a</mi><mi>b</mi></mrow>
</math>''', '⠼⠁⠃⠔⠰⠁⠰⠔⠃')
        test('''<?xml version="1.0" encoding="UTF-8"?>
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
''', '''⠭⠡⠼⠁⠂⠀⠼⠃⠱⠀⠶⠆⠤⠃⠀⠲⠤⠩
⠩⠃⠌⠼⠃⠱⠀⠤⠼⠙⠐⠁⠉⠱⠻⠼⠃⠐⠁⠰''')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msqrt><mn>2</mn></msqrt><mo>+</mo><mroot><mrow><mn>2</mn></mrow><mrow><mn>3</mn></mrow>
</mroot></mrow>
</math>''', '⠩⠼⠃⠱⠀⠲⠠⠌⠼⠉⠩⠼⠃⠱')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>&#x2208;</mo><mi>R</mi></mrow>
</math>''', '⠭⠀⠘⠑⠀⠠⠗')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>∈</mo><mi>R</mi></mrow>
</math>''', '⠭⠀⠘⠑⠀⠠⠗')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>α</mi><mo>+</mo><mi>β</mi></mrow>
</math>''', '⠘⠁⠀⠲⠘⠃')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mrow><mn>5</mn></mrow><mrow><mn>6</mn></mrow></mfrac><mo>-</mo><mfrac><mrow><mn>2</mn>
</mrow><mrow><mn>3</mn></mrow></mfrac><mo>=</mo><mfrac><mrow><mn>5</mn><mo>-</mo><mn>4</mn></mrow>
<mrow><mn>6</mn></mrow></mfrac></mrow>
</math>''', '⠆⠼⠑⠻⠼⠋⠰⠀⠤⠆⠼⠃⠻⠼⠉⠰⠀⠶\n⠶⠆⠼⠑⠀⠤⠼⠙⠻⠼⠋⠰')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>5</mn><mfrac><mrow><mn>2</mn></mrow><mrow><mn>3</mn></mrow></mfrac></mrow>
</math>''', '⠼⠑⠆⠼⠃⠻⠼⠉⠰')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>2,</mn><mover accent="true"><mn>32</mn><mo>&macr;</mo></mover></mrow>
</math>''', '⠼⠃⠂⠉⠃⠉⠃⠤')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="&langle;" close="&rangle;" separators="|"><mi>a</mi><mi>b</mi><mi>c</mi></mfenced>
</math>''', '⠈⠣⠁⠸⠀⠃⠸⠀⠉⠈⠜')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="&langle;" close="&rangle;" separators=","><mi>a</mi><mi>b</mi></mfenced>
</math>''', '⠈⠣⠁⠂⠀⠃⠈⠜')
        test('''<math contenteditable="false" style="display:inline-block"
        xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mstyle displaystyle="true">
<msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mstyle>
<annotation encoding="ASCII">x^2 + y^2</annotation></semantics></math>''',
             '⠭⠌⠼⠃⠱⠀⠲⠽⠌⠼⠃⠱')

    def test_inline_mathml(self):
        mathml = '''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mn>1</mn><mo>=</mo><mn>2</mn></mrow>
</math>'''
        mathml_content = lcg.MathML(mathml)
        content = lcg.p("Trocha matematiky (", mathml_content, ") neuškodí.")
        presentation = self._load_presentation()
        presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
        n = lcg.ContentNode('test', title='Test Node', descr="Some description", content=content)
        exporter = lcg.BrailleExporter()
        context = exporter.context(n, lang='cs', presentation=presentation_set)
        exported = exporter.export(context)
        result = exported.replace('\r\n', '\n').split('\n\n')[1]
        assert result == '''⠠⠞⠗⠕⠉⠓⠁⠀⠍⠁⠞⠑⠍⠁⠞⠊⠅⠽
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
                result = result[:-2] + '⠲'
            elif post == ',':
                result = result[:-2] + '⠠'
            if result != expected_result:
                print('---')
                print(mathml)
                print('---')
                print(" expected: |%s|" % (expected_result,))
                print("      got: |%s|" % (result,))
                print('---')
            assert result == expected_result
        # §8
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3,76</mn></mrow>
</math>''', '⠼⠒⠨⠶⠖', lang='cs')  # decimal point
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', '⠼⠒⠨⠶⠖', lang='cs')  # decimal point
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1,378</mn></mrow>
</math>''', '⠼⠂⠠⠒⠶⠦', lang='en')  # comma
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', '⠼⠒⠨⠶⠖', lang='en')  # decimal point
        # §9
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>27</mn></mrow>
</math>''', '⠼⠆⠶')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>7</mn></mrow>
</math>''', '⠠⠐⠮⠀⠶⠀⠼⠶⠀⠃⠁⠇⠇⠎⠲', lang='en2', pre="There were ", post=" balls.")
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mi>x</mi><mo>+</mo><mi>y</mi><mo>=</mo><mn>0</mn></mrow>
</math>''', '⠼⠂⠬⠭⠬⠽⠀⠨⠅⠀⠼⠴')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>y</mi><mo>=</mo><mn>2</mn><mi>sin</mi><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', '⠽⠀⠨⠅⠀⠼⠆⠎⠊⠝⠀⠭')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mn>1</mn></mrow>
</math>''', '⠎⠊⠝⠀⠼⠂')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>sin</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mn>2</mn><mi>x</mi></mrow>
</math>''', '⠎⠊⠝⠘⠆⠀⠼⠆⠭')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>0.333</mn><mo>&hellip;</mo><mn>3</mn><mo>&hellip;</mo></mrow>
</math>''', '⠼⠴⠨⠒⠒⠒⠀⠄⠄⠄⠀⠼⠒⠀⠄⠄⠄', lang='en')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>log</mi><mn>10</mn></msub><mo>&ApplyFunction;</mo><mn>2</mn></mrow>
</math>''', '⠇⠕⠛⠂⠴⠀⠼⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&angle;</mo><mn>1</mn></mrow>
</math>''', '⠫⠪⠀⠼⠂')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>x</mi><mo>=</mo><mn>0</mn><mo>)</mo></mrow>
</math>''', '⠷⠭⠀⠨⠅⠀⠼⠴⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>-1</mn></mrow>
</math>''', '⠤⠼⠂')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>-.3</mn></mrow>
</math>''', '⠤⠼⠨⠒')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="|" close="|" separators=","><mtable>
 <mtr><mtd><mn>1</mn></mtd><mtd><mn>2</mn></mtd></mtr>
 <mtr><mtd><mn>-3</mn></mtd><mtd><mn>-4</mn></mtd></mtr>
</mtable></mfenced></math>''', '⠠⠳⠼⠂⠀⠀⠼⠆⠀⠠⠳\n⠠⠳⠤⠼⠒⠀⠤⠼⠲⠠⠳')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3</mn><mo>#</mo><mn>4</mn></mrow>
</math>''', '⠼⠒⠨⠼⠼⠲')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3</mn><mo>*</mo><mn>4</mn></mrow>
</math>''', '⠼⠒⠈⠼⠼⠲')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn mathvariant="italic">3</mn></mrow>
</math>''', '⠨⠼⠒')
        # §11
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>[</mo><mn>0</mn><mo>,</mo><mn>1</mn><mo>]</mo></mrow>
</math>''', '⠈⠷⠴⠠⠀⠂⠈⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="[" close="]" separators=","><mn>0</mn><mn>1</mn></mfenced></mrow>
</math>''', '⠈⠷⠴⠠⠀⠂⠈⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
  <mrow><mn>1</mn><mo>+</mo><mi>h</mi></mrow>
  <mrow><mn>2</mn><mo>+</mo><mi>k</mi></mrow>
  <mrow><mn>0</mn></mrow>
</mfenced></mrow></math>''', '⠷⠂⠬⠓⠠⠀⠆⠬⠅⠠⠀⠴⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
 <mrow><mn>0</mn></mrow><mrow><mo>-</mo><mn>1</mn></mrow><mrow><mo>&PlusMinus;</mo><mn>2</mn></mrow>
</mfenced></mrow></math>''', '⠷⠴⠠⠀⠤⠂⠠⠀⠬⠤⠆⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
  <mrow><mn>2</mn><mi>sin</mi><mo>&ApplyFunction;</mo><mn>30</mn><mo>°</mo></mrow>
  <mrow><mn>3</mn><mi>cos</mi><mo>&ApplyFunction;</mo><mn>60</mn><mo>°</mo></mrow>
</mfenced></mrow></math>''', '⠷⠆⠎⠊⠝⠀⠼⠒⠴⠘⠨⠡⠠⠀⠒⠉⠕⠎\n⠀⠀⠼⠖⠴⠘⠨⠡⠐⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=",">
  <mrow><mi>x</mi></mrow><mrow><mn>7</mn></mrow><mrow><mn mathvariant="bold">8</mn></mrow>
  <mrow><mi>y</mi></mrow>
</mfenced></mrow></math>''', '⠷⠭⠠⠀⠶⠠⠀⠸⠼⠦⠠⠀⠽⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&pi;</mi><mo>=</mo><mn>3,14159 26535</mn><mo>&hellip;</mo></mrow>
</math>''', '⠨⠏⠀⠨⠅⠀⠼⠒⠨⠂⠲⠂⠢⠔⠀⠆⠖⠢⠒⠢\n⠀⠀⠄⠄⠄')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&pi;</mi><mo>=</mo><mn>3,14159 26535 9</mn></mrow>
</math>''', '⠨⠏⠀⠨⠅⠀⠼⠒⠨⠂⠲⠂⠢⠔⠀⠆⠖⠢⠒⠢\n⠀⠀⠼⠔')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>2</mn></msup></mrow>
</math>''', '⠭⠘⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><mrow><mn>3</mn></mrow><mrow><mi>x</mi></mrow></mfrac>
</math>''', '⠹⠒⠌⠭⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>-</mo><mn>5</mn></mrow>
</math>''', '⠭⠤⠢')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>2</mn><mo>&times;</mo><mn>4</mn></mrow>
</math>''', '⠼⠆⠈⠡⠲')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mn>10,000</mn>
</math>''', '⠼⠂⠴⠠⠴⠴⠴', lang='en')  # comma
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="|" close="|" separators=","><mrow><mo>-</mo><mn>3</mn></mrow></mfenced>
</math>''', '⠳⠤⠒⠳')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="|" close="|" separators=","><mrow><mn>-3</mn></mrow></mfenced>
</math>''', '⠳⠤⠒⠳')
        # §24
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mi>&alpha;</mi>
</math>''', '⠨⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mi>&Sigma;</mi>
</math>''', '⠨⠠⠎')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>&alefsym;</mi><mn>0</mn></msub>
</math>''', '⠠⠠⠁⠴')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&alpha;</mi><mi>&beta;</mi></mrow>
</math>''', '⠨⠁⠨⠃')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>&alpha;&beta;</mi></mrow>
</math>''', '⠨⠁⠨⠃')
        # §25
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mo>&prime;</mo></msup><mo>,</mo><msup><mi>x</mi><mo>&Prime;</mo></msup>
<mo>,</mo><msub><mi>x</mi><mn>1</mn></msub><mo>,</mo><msub><mi>x</mi><mi>a</mi></msub><mo>,</mo>
<msup><mi>x</mi><mn>2</mn></msup><mo>,</mo><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover>
</mrow>
</math>''', '⠭⠄⠠⠀⠭⠄⠄⠠⠀⠭⠂⠠⠀⠭⠰⠁⠠⠀⠭⠘⠆⠠⠀⠭⠱', page_width=True)
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow>
</math>''', '⠭⠬⠽')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>cd</mi></mrow>
</math>''', '⠰⠉⠙⠀⠊⠎⠀⠏⠜⠁⠇⠇⠑⠇⠀⠞⠕⠀', lang='en2', post=' is parallel to ')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>e</mi><mi>f</mi></mrow>
</math>''', '⠀⠊⠎⠀⠏⠜⠁⠇⠇⠑⠇⠀⠞⠕⠀⠑⠋⠸⠲', lang='en2', pre=' is parallel to ', post='.')
        # §26
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi mathvariant="bold">A</mi><mi mathvariant="bold">B</mi></mrow>
</math>''', '⠸⠰⠠⠁⠸⠰⠠⠃')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi mathvariant="italic">a</mi><mi mathvariant="italic">b</mi></mrow>
</math>''', '⠨⠰⠁⠨⠰⠃')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=","><mi>a</mi><mrow><mn>2</mn><mi>x</mi></mrow>
<mrow><mi>y</mi><mo>=</mo><mi>z</mi></mrow></mfenced>
</math>''', '⠷⠰⠁⠠⠀⠼⠆⠭⠠⠀⠽⠀⠨⠅⠀⠵⠾')
        # §27
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>cos</mi><mo>&ApplyFunction;</mo><mi>A</mi></mrow>
</math>''', '⠉⠕⠎⠀⠠⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>arc</mi><mo>&ApplyFunction;</mo><mi>a</mi><mi>b</mi></mrow>
</math>''', '⠁⠗⠉⠀⠁⠃')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>e</mi><mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mi>x</mi></mrow></msup></mrow>
</math>''', '⠑⠘⠎⠊⠝⠀⠭')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&angle;</mo><mi>a</mi></mrow>
</math>''', '⠫⠪⠀⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&triangle;</mo><mi>a</mi><mi>c</mi><mi>r</mi></mrow>
</math>''', '⠫⠞⠀⠁⠉⠗')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>&#x25FD;</mo><mi>y</mi></mrow>
</math>''', '⠭⠀⠫⠲⠀⠽')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>|</mo><mtable><mtr><mtd><mi>a</mi></mtd><mtd><mi>b</mi></mtd><mtd><mi>c</mi></mtd></mtr>
<mtr><mtd><mi>d</mi></mtd><mtd><mi>e</mi></mtd><mtd><mi>f</mi></mtd></mtr>
<mtr><mtd><mi>g</mi></mtd><mtd><mi>h</mi></mtd><mtd><mi>i</mi></mtd></mtr></mtable><mo>|</mo></mrow>
</math>''', '⠠⠳⠁⠀⠃⠀⠉⠠⠳\n⠠⠳⠙⠀⠑⠀⠋⠠⠳\n⠠⠳⠛⠀⠓⠀⠊⠠⠳')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=","><mn>0</mn><mi>a</mi><mn>1</mn><mi>b</mi><mn>2</mn>
</mfenced>
</math>''', '⠷⠴⠠⠀⠁⠠⠀⠂⠠⠀⠃⠠⠀⠆⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="{" close="}" separators=","><mi>a</mi><mi>b</mi><mi>c</mi><mi>d</mi>
</mfenced>
</math>''', '⠨⠷⠁⠠⠀⠃⠠⠀⠉⠠⠀⠙⠨⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=",">
<mrow><mi>a</mi><mi>b</mi></mrow><mrow><mi>c</mi><mi>d</mi></mrow><mrow><mi>e</mi><mi>f</mi></mrow>
</mfenced>
</math>''', '⠷⠁⠃⠠⠀⠉⠙⠠⠀⠑⠋⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="(" close=")" separators=","><mi>a</mi><mrow><mn>2</mn><mi>x</mi></mrow><mi>b</mi>
</mfenced>
</math>''', '⠷⠁⠠⠀⠆⠭⠠⠀⠃⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>a</mi><mi>cos</mi><mo>&ApplyFunction;</mo><mi>B</mi></mrow>
</math>''', '⠁⠉⠕⠎⠀⠠⠃')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>m</mi><mo>&angle;</mo><mi>b</mi></mrow>
</math>''', '⠍⠫⠪⠀⠃')
        # §28
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="" close="" separators=",">
<mfenced open="|" close="|"><mi>x</mi></mfenced>
<mfenced open="[" close="]"><mi>x</mi></mfenced>
<mfenced open="&DoubleVerticalBar;" close="&DoubleVerticalBar;"><mi>f</mi></mfenced>
</mfenced>
</math>''', '⠳⠭⠳⠠⠀⠈⠷⠭⠈⠾⠠⠀⠳⠳⠋⠳⠳')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>a</mi><mi>b</mi><mo>)</mo><mo>+</mo><mo>(</mo><mi>c</mi><mi>d</mi><mo>)</mo>
</mrow>
</math>''', '⠷⠁⠃⠾⠬⠷⠉⠙⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>j</mi><mo>=</mo><mn>1</mn><mo>,</mo><mn>2</mn><mo>,</mo><mo>&hellip;</mo>
<mo>,</mo><mi>n</mi><mo>)</mo></mrow>
</math>''', '⠷⠚⠀⠨⠅⠀⠼⠂⠠⠀⠼⠆⠠⠀⠄⠄⠄⠠⠀⠰⠝⠾', page_width=True)
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>a</mi><mi>b</mi><mo>=</mo><mi>c</mi><mi>d</mi><mo>)</mo></mrow>
</math>''', '⠷⠁⠃⠀⠨⠅⠀⠉⠙⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msubsup><mrow><mi>s</mi><mo>]</mo></mrow><mi>a</mi><mi>b</mi></msubsup></mrow>
</math>''', '⠎⠈⠾⠰⠁⠘⠃')
        # §32
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn mathvariant="bold">0</mn></mrow>
</math>''', '⠸⠼⠴')
        # §37
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>1</mn><mn>2</mn></mfrac></mrow>
</math>''', '⠹⠂⠌⠆⠼⠠', lang='en2', post=',')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>3</mn><mn>4</mn></mfrac></mrow>
</math>''', '⠹⠒⠌⠲⠼⠸⠲', lang='en2', post='.')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>0</mn></mrow>
</math>''', '⠼⠴⠸⠲', lang='en2', post='.')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>c</mi></mrow>
</math>''', '⠰⠉⠸⠲', lang='en2', post='.')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo lspace="0" rspace="0">&square;</mo><mo>+</mo>
<mo lspace="0" rspace="0">&bigcirc;</mo><mo>=</mo><mo>&bigtriangleup;</mo></mrow>
</math>''', '⠦⠫⠲⠬⠫⠉⠀⠨⠅⠀⠫⠞⠸⠴', lang='en2', pre='“', post='”')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>sin</mi></mrow>
</math>''', '⠦⠎⠊⠝⠸⠴', lang='en2', pre='“', post='”')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>0</mn></mrow>
</math>''', '⠼⠴⠠⠸⠴', lang='en2', post=',”')
        # §42
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mo>&mdash;</mo><mn>15</mn></mfrac><mo>=</mo><mfrac><mn>2</mn><mn>3</mn></mfrac></mrow>
</math>''', '⠹⠤⠤⠤⠤⠀⠌⠂⠢⠼⠀⠨⠅⠀⠹⠆⠌⠒⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=","><mo>&mdash;</mo><mn>4</mn><mn>6</mn><mn>8</mn>
<mo>&mdash;</mo></mfenced></mrow>
</math>''', '⠷⠤⠤⠤⠤⠠⠀⠲⠠⠀⠖⠠⠀⠦⠠⠀⠤⠤⠤⠤⠾', page_width=True)
        # §43
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>+</mo><mi>y</mi><mo>+</mo><mi>&hellip;</mi></mrow>
</math>''', '⠭⠬⠽⠬⠀⠄⠄⠄⠸⠲', lang='en2', post='.')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="" close="" separators=","><mn>1</mn><mn>3</mn><mn>5</mn><mo>&hellip;</mo>
<mn>15</mn></mfenced></mrow>
</math>''', '⠼⠂⠠⠀⠼⠒⠠⠀⠼⠢⠠⠀⠄⠄⠄⠠⠀⠼⠂⠢⠸⠲', lang='en2', post='.', page_width=True)
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow>
<msup><msub><mi>p</mi><mn>1</mn></msub><msub><mi>&alpha;</mi><mn>1</mn></msub></msup>
<mo>&hellip;</mo>
<msup><msub><mi>p</mi><mi>r</mi></msub><msub><mi>&alpha;</mi><mi>r</mi></msub></msup>
</mrow>
</math>''', '⠏⠂⠘⠨⠁⠘⠰⠂⠐⠄⠄⠄⠀⠏⠰⠗⠘⠨⠁⠘⠰⠗', page_width=True)
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="(" close=")" separators=","><mo>&hellip;</mo><mn>-1</mn><mn>0</mn><mn>1</mn>
<mo>&hellip;</mo></mfenced></mrow>
</math>''', '⠷⠄⠄⠄⠠⠀⠤⠂⠠⠀⠴⠠⠀⠂⠠⠀⠄⠄⠄⠾')
        # §57
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>?</mo><mo>+</mo><mo>?</mo><mo>=</mo><mn>10</mn></mrow>
</math>''', '⠿⠬⠿⠀⠨⠅⠀⠼⠂⠴')
        # §62
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>1</mn><mn>3</mn></mfrac></mrow>
</math>''', '⠹⠂⠌⠒⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mrow><mi>a</mi><mo>+</mo><mi>b</mi></mrow><mi>c</mi></mfrac></mrow>
</math>''', '⠹⠁⠬⠃⠌⠉⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><msup><mi>x</mi><mfrac><mn>1</mn><mn>2</mn></mfrac></msup><mn>2</mn></mfrac></mrow>
</math>''', '⠹⠭⠘⠹⠂⠌⠆⠼⠐⠌⠆⠼')
        # §64
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>4</mn><mfrac><mn>3</mn><mn>8</mn></mfrac></mrow>
</math>''', '⠼⠲⠸⠹⠒⠌⠦⠸⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mfrac><mn>3</mn><mn>8</mn></mfrac></mrow>
</math>''', '⠭⠹⠒⠌⠦⠼')
        # §65
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mfrac><mn>3</mn><mn>8</mn></mfrac><mn>5</mn></mfrac></mrow>
</math>''', '⠠⠹⠹⠒⠌⠦⠼⠠⠌⠢⠠⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><mn>5</mn><mrow><mn>4</mn><mfrac><mn>3</mn><mn>8</mn></mfrac></mrow></mfrac></mrow>
</math>''', '⠠⠹⠢⠠⠌⠲⠸⠹⠒⠌⠦⠸⠼⠠⠼')
        # §67
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><mi>a</mi><msup><mi>b</mi>
<mfrac><mfrac><mn>3</mn><mn>4</mn></mfrac><mfrac><mn>5</mn><mn>6</mn></mfrac></mfrac></msup></mfrac>
</math>''', '⠹⠁⠌⠃⠘⠠⠹⠹⠒⠌⠲⠼⠠⠌⠹⠢⠌⠖⠼⠠⠼⠐⠼', page_width=True)
        # §74
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mn>2</mn></msup>
</math>''', '⠭⠘⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mo>*</mo></msup>
</math>''', '⠭⠘⠈⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mn>-2</mn></msup>
</math>''', '⠭⠘⠤⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mi>a</mi></msub>
</math>''', '⠭⠰⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mn>-2</mn></msub>
</math>''', '⠭⠰⠤⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>n</mi><msup><mi>x</mi><mi>y</mi></msup></msup>
</math>''', '⠝⠘⠭⠘⠘⠽')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><msup><mi>n</mi><mi>a</mi></msup></msub>
</math>''', '⠭⠰⠝⠰⠘⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><msub><mi>y</mi><msup><mi>a</mi><mi>n</mi></msup></msub></msup>
</math>''', '⠭⠘⠽⠘⠰⠁⠘⠰⠘⠝')
        # §77
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mn>1</mn></msub>
</math>''', '⠭⠂')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mn>11</mn></msub>
</math>''', '⠭⠂⠂')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><msup><mi>x</mi><mo>&prime;</mo></msup><mn>1</mn></msub>
</math>''', '⠭⠄⠂')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><msub><mi>i</mi><mn>1</mn></msub></msub>
</math>''', '⠭⠰⠊⠰⠰⠂')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>log</mi><mn>2</mn></msub><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', '⠇⠕⠛⠆⠀⠭')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mn>12</mn><mn>7</mn></msub>
</math>''', '⠼⠂⠆⠰⠶')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mrow><mo>(</mo><mi>C</mi><msub><mi>O</mi><mn>3</mn></msub><mo>)</mo></mrow><mi>2</mi></msub>
</math>''', '⠷⠠⠉⠠⠕⠒⠾⠰⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>Na</mi><mn>2</mn></msub><mi>C</mi><msub><mi>O</mi><mn>3</mn></msub></mrow>
</math>''', '⠠⠝⠁⠆⠠⠉⠠⠕⠒')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>seven</mi><mn>3</mn></msub>
</math>''', '⠎⠑⠧⠑⠝⠰⠒')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msubsup><mo>&Sum;</mo><mn>0</mn><mi>n</mi></msubsup><msub><mi>a</mi><mi>k</mi></msub></mrow>
</math>''', '⠨⠠⠎⠴⠘⠝⠐⠁⠰⠅')
        # §78
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mfenced open="" close="" separators=","><mi>i</mi><mi>j</mi><mi>k</mi></mfenced>
</msub>
</math>''', '⠭⠰⠊⠪⠚⠪⠅')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mfenced open="(" close=")" separators=","><mi>a</mi><mi>b</mi></mfenced></msub>
</math>''', '⠭⠰⠷⠁⠪⠃⠾')
        # §79
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>x</mi><mi>a</mi></msub><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mrow>
</math>''', '⠭⠰⠁⠐⠬⠽⠘⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><msup><mi>e</mi><msup><mi>x</mi><mn>2</mn></msup></msup><mn>2</mn></mfrac>
</math>''', '⠹⠑⠘⠭⠘⠘⠆⠐⠌⠆⠼')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mn>2</mn></msup>
</math>''', '⠭⠘⠆⠸⠲', lang='en2', post='.')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>2</mn></msup><mo>,</mo><msup><mi>x</mi><mn>3</mn></msup></mrow>
</math>''', '⠭⠘⠆⠠⠀⠭⠘⠒')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>10,000</mn></msup></mrow>
</math>''', '⠭⠘⠂⠴⠠⠴⠴⠴', lang='en2')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>x</mi><mrow><mi>i</mi><mo>,</mo><mi>j</mi></mrow></msub>
</math>''', '⠭⠰⠊⠪⠚')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>P</mi><mfenced open="" close="" separators=",">
<msub><mi>n</mi><mn>1</mn></msub><msub><mi>n</mi><mn>2</mn></msub><mo>&hellip;</mo></mfenced></msub>
</math>''', '⠠⠏⠰⠝⠰⠰⠂⠰⠪⠝⠰⠰⠆⠰⠪⠀⠄⠄⠄')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>b</mi><mrow><mo>&triangle;</mo><mi>A</mi><mi>B</mi><mi>C</mi></mrow></msub>
</math>''', '⠃⠰⠫⠞⠀⠠⠁⠠⠃⠠⠉')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>cos</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', '⠉⠕⠎⠘⠆⠀⠭')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>e</mi><mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mi>x</mi><mo>+</mo>
<mi>i</mi><mi>cos</mi><mo>&ApplyFunction;</mo><mi>x</mi></mrow></msup>
</math>''', '⠑⠘⠎⠊⠝⠀⠭⠬⠊⠉⠕⠎⠀⠭')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>e</mi><mrow><msup><mi>sin</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mi>x</mi>
<mo>+</mo><msup><mi>sin</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mi>y</mi></mrow></msup>
</math>''', '⠑⠘⠎⠊⠝⠘⠘⠆⠀⠭⠬⠎⠊⠝⠘⠘⠆⠀⠽')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>s</mi><mn>1</mn></msub><mo>&hellip;</mo><msub><mi>s</mi><mi>n</mi></msub></mrow>
</math>''', '⠎⠂⠀⠄⠄⠄⠀⠎⠰⠝')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup><mo>+</mo>
<msup><mi>z</mi><mn>2</mn></msup><mo>=</mo><msup><mi>r</mi><mn>2</mn></msup></mrow>
</math>''', '⠭⠘⠆⠐⠬⠽⠘⠆⠐⠬⠵⠘⠆⠀⠨⠅⠀⠗⠘⠆', page_width=True)
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>q</mi><mrow><msub><mi>log</mi><mi>q</mi></msub><mo>&ApplyFunction;</mo><mi>a</mi>
</mrow></msup><mo>=</mo><mi>a</mi></mrow>
</math>''', '⠟⠘⠇⠕⠛⠘⠰⠟⠀⠁⠀⠨⠅⠀⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mrow><mo>(</mo><mn>1</mn><mo>-</mo><msup><mi>sin</mi><mn>2</mn></msup>
<mo>&ApplyFunction;</mo><mi>x</mi><mo>)</mo></mrow><mi>2</mi></msup><mo>=</mo>
<msup><mi>cos</mi><mn>4</mn></msup><mo>&ApplyFunction;</mo><mi>x</mi></mrow>
</math>''', '⠷⠂⠤⠎⠊⠝⠘⠆⠀⠭⠾⠘⠆⠀⠨⠅⠀⠉⠕⠎⠘⠲⠀⠭', page_width=True)
        # §81
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><msub><mi>x</mi><mn>1</mn></msub><msub><mi>y</mi><mn>1</mn></msub><mo>+</mo>
<msub><mi>x</mi><mn>2</mn></msub><msub><mi>y</mi><mn>2</mn></msub><mo>)</mo></mrow>
</math>''', '⠷⠭⠂⠽⠂⠬⠭⠆⠽⠆⠾')
        # §83
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mo>&prime;</mo></msup>
</math>''', '⠭⠄')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msubsup><mi>x</mi><mi>a</mi><mo>&prime;</mo></msubsup>
</math>''', '⠭⠄⠰⠁')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mi>x</mi><mrow><mo>&prime;</mo><mn>2</mn></mrow></msup>
</math>''', '⠭⠄⠘⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msubsup><mi>x</mi><mi>a</mi><mrow><mo>&prime;</mo><mi>b</mi></mrow></msubsup>
</math>''', '⠭⠄⠰⠁⠘⠃')
        # §86
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<munder accentunder="true"><mi>x</mi><mo>&macr;</mo></munder>
</math>''', '⠐⠭⠩⠱⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><mrow><mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow></mrow><mo>&macr;</mo></mover>
</math>''', '⠐⠭⠬⠽⠣⠱⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><munder accentunder="true"><mi>lim</mi><mrow><mi>x</mi><mo>&rarr;</mo><mn>0</mn></mrow>
</munder><mo>&ApplyFunction;</mo>
<mi>f</mi><mfenced open="(" close=")" separators=","><mrow><mi>x</mi></mrow></mfenced>
</mrow>
</math>''', '⠐⠇⠊⠍⠩⠭⠀⠫⠕⠀⠼⠴⠻⠀⠋⠷⠭⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><msup><mi>x</mi><mn>2</mn></msup><mo>&macr;</mo></mover>
</math>''', '⠐⠭⠘⠆⠐⠣⠱⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><msup><mi>x</mi><mo>&prime;</mo></msup><mo>&macr;</mo></mover>
</math>''', '⠐⠭⠄⠣⠱⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><msub><mi>x</mi><mn>1</mn></msub><mo>&macr;</mo></mover>
</math>''', '⠐⠭⠂⠣⠱⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><mi>x</mi><mo>&macr;</mo></mover>
</math>''', '⠭⠱')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover><mo>+</mo>
<mover accent="true"><mi>y</mi><mo>&macr;</mo></mover></mrow>
</math>''', '⠭⠱⠬⠽⠱')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover><mn>2</mn></msup>
</math>''', '⠭⠱⠘⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msup><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover><mo>&prime;</mo></msup>
</math>''', '⠭⠱⠄')
        # §88
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<munderover><mrow><mi>x</mi><mo>+</mo><mi>y</mi></mrow><mo>&macr;</mo><mo>&macr;</mo></munderover>
</math>''', '⠐⠭⠬⠽⠩⠱⠣⠱⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><munderover><mo>&Sum;</mo><mrow><mi>n</mi><mo>=</mo><mn>1</mn></mrow><mo>&infin;</mo>
</munderover><mfrac><mrow><mn>1</mn></mrow><mrow><msup><mn>2</mn><mi>n</mi></msup></mrow></mfrac>
<mo>=</mo><mn>1</mn></mrow>
</math>''', '⠐⠨⠠⠎⠩⠝⠀⠨⠅⠀⠼⠂⠣⠠⠿⠻⠹⠂⠌⠆⠘⠝⠐⠼⠀⠨⠅⠀⠼⠂', page_width=True)
        # §90
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mfrac linethickness="0"><mi>n</mi><mi>k</mi></mfrac><mo>)</mo></mrow>
</math>''', '⠷⠝⠩⠅⠾')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mfrac linethickness="0"><msub><mi>g</mi><mi>j</mi></msub><msub><mi>a</mi><mi>j</mi>
</msub></mfrac><mo>)</mo></mrow>
</math>''', '⠷⠛⠰⠚⠐⠩⠁⠰⠚⠐⠾')
        # §91
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>A</mi><mrow><mover><mi>x</mi><mo>~</mo></mover><mo>+</mo><mover><mi>y</mi><mo>~</mo>
</mover></mrow></msub>
</math>''', '⠠⠁⠰⠐⠭⠣⠈⠱⠻⠬⠰⠐⠽⠣⠈⠱⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msub><mi>A</mi><mrow><mover><mi>x</mi><mo>&macr;</mo></mover><mo>+</mo><mover><mi>y</mi>
<mo>&macr;</mo></mover></mrow></msub>
</math>''', '⠠⠁⠰⠭⠱⠬⠽⠱')
        # §96
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mover accent="true"><mrow><mrow><mi>A</mi><mi>B</mi></mrow></mrow><mo>&rarr;</mo></mover>
</math>''', '⠐⠠⠁⠠⠃⠣⠫⠕⠻')
        # §97
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.57</mn><mover><mn>29</mn><mo>&macr;</mo></mover></mrow>
</math>''', '⠼⠒⠨⠢⠶⠐⠆⠔⠣⠱⠻')
        # §103
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msqrt><mn>2</mn></msqrt>
</math>''', '⠜⠆⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<msqrt><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><mn>1</mn></msqrt>
</math>''', '⠜⠭⠘⠆⠐⠬⠂⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mroot><mrow><mn>2</mn></mrow><mrow><mn>3</mn></mrow></mroot>
</math>''', '⠣⠒⠜⠆⠻')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mroot><mrow><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><mroot><mrow>
<msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mrow><mrow>
<mn>3</mn></mrow></mroot><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mrow><mrow><mn>3</mn></mrow>
</mroot>
</math>''', '⠣⠒⠜⠭⠘⠆⠐⠬⠨⠣⠒⠜⠭⠘⠆⠐⠬⠽⠘⠆⠐⠨⠻⠬⠽⠘⠆⠐⠻', page_width=True)
        # §138
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>=</mo><mo>-</mo><mi>y</mi></mrow>
</math>''', '⠭⠀⠨⠅⠀⠤⠽')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mo>-</mo><mi>x</mi></mrow>
</math>''', '⠎⠊⠝⠀⠤⠭')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mn>2</mn><mo>+</mo><mo>&hellip;</mo><mo>+</mo><mi>n</mi></mrow>
</math>''', '⠼⠂⠬⠆⠬⠀⠄⠄⠄⠀⠬⠝')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mi mathvariant="normal">yd</mi><mo>+</mo>
<mn>2</mn><mi mathvariant="normal">yd</mi><mo>=</mo>
<mn>3</mn><mi mathvariant="normal">yd</mi></mrow>
</math>''', '⠼⠂⠀⠽⠙⠀⠬⠆⠀⠽⠙⠀⠨⠅⠀⠼⠒⠀⠽⠙', page_width=True)
        # §169
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>n</mi><mo>!</mo></mrow>
</math>''', '⠝⠯')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&forall;</mo><mi>x</mi><mo>&isin;</mo><mi>A</mi></mrow>
</math>''', '⠈⠯⠭⠀⠈⠑⠀⠠⠁')
        # §177
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mn>5</mn></mrow>
</math>''', '⠭⠐⠢')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>c</mi><mn>0</mn></msub><msup><mn>10</mn><mn>2</mn></msup><mo>+</mo>
<msub><mi>c</mi><mn>1</mn></msub><mn>10</mn><mo>+</mo><msub><mi>c</mi><mn>2</mn></msub></mrow>
</math>''', '⠉⠴⠐⠂⠴⠘⠆⠐⠬⠉⠂⠐⠂⠴⠬⠉⠆')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>|</mo><mi>x</mi><mo>|</mo><mo>|</mo><mi>y</mi><mo>|</mo></mrow>
</math>''', '⠳⠭⠳⠐⠳⠽⠳')
        # §178
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mstack>
<mn>508</mn><mn>2876</mn><mn>59</mn><msrow><mo>+</mo><mn>427</mn></msrow><msline/><mn>3870</mn>
</mstack>
</math>''', '⠀⠀⠀⠢⠴⠦\n⠀⠀⠆⠦⠶⠖\n⠀⠀⠀⠀⠢⠔\n⠀⠬⠀⠲⠆⠶\n⠒⠒⠒⠒⠒⠒⠒\n⠀⠀⠒⠦⠶⠴')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mstack>
<mn>35.50</mn><msrow><mo>+</mo><mn>77.25</mn></msrow><msline/><mn>112.75</mn>
</mstack>
</math>''', '⠀⠀⠒⠢⠨⠢⠴\n⠀⠬⠶⠶⠨⠆⠢\n⠒⠒⠒⠒⠒⠒⠒⠒\n⠀⠂⠂⠆⠨⠶⠢')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mstack>
<mn>3.704</mn><msrow><mo>-</mo><mn>.915</mn></msrow><msline/><mn>2.789</mn>
</mstack>
</math>''', '⠀⠀⠒⠨⠶⠴⠲\n⠀⠤⠀⠨⠔⠂⠢\n⠒⠒⠒⠒⠒⠒⠒⠒\n⠀⠀⠆⠨⠶⠦⠔')
        # §179
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
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
</math>''', '⠀⠀⠀⠆⠒\n⠀⠈⠡⠢⠲\n⠒⠒⠒⠒⠒⠒\n⠀⠀⠀⠔⠆\n⠀⠂⠂⠢\n⠒⠒⠒⠒⠒⠒\n⠀⠂⠆⠲⠆', page_height=True)

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
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', '⠼⠒⠨⠶⠖')
        test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1</mn><mo>+</mo><mi>x</mi><mo>+</mo><mi>y</mi><mo>=</mo><mn>0</mn></mrow>
</math>''', '⠼⠂⠬⠭⠬⠽⠀⠨⠅⠀⠼⠴')
        # Of course, comma is not recognized as a decimal point, how could
        # liblouisutdml know about that?
#         test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
# <mrow><mn>3,76</mn></mrow>
# </math>''', '⠼⠒⠨⠶⠖')
        # Doesn't work correctly in liblouisutdml:
#         test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
# <mrow><msub><mi>log</mi><mtext>10</mtext></msub><mn>2</mn></mrow>
# </math>''', '⠇⠕⠛⠂⠴⠀⠼⠆')
        # Doesn't work correctly in liblouisutdml:
#         test('''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
# <mfrac><mfrac><mn>3</mn><mn>8</mn></mfrac><mn>5</mn></mfrac>
# </math>''', '⠠⠹⠹⠒⠌⠦⠼⠠⠌⠢⠠⠼')


class PDFExport(unittest.TestCase):

    def test_export(self):
        # Just test for crashes
        path = os.path.join(repo_root, 'doc/src')
        name = 'structured-text'
        reader = lcg.reader(path, name, ext='txt', recourse=False)
        node = reader.build()
        exporter = lcg.PDFExporter()
        context = exporter.context(node, 'cs')
        exporter.export(context)


class Presentations(unittest.TestCase):

    def test_style_file(self):
        style_file = lcg.StyleFile()
        f = open(os.path.join(repo_root, 'styles', 'standard'))
        style_file.read(f)
        f.close()
        f = tempfile.NamedTemporaryFile(mode='w+t')
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


@pytest.mark.skipif(pyplot is None, reason="matplotlib.pyplot not installed.")
class TestPlots:

    def _test_formatter(self, formatter, pairs, lang='en'):
        exporter = lcg.HtmlExporter(translations=translation_path)
        context = exporter.context(None, lang)
        for number, formatted in pairs:
            assert formatter(context, number, 0).replace(u'\xa0', ' ') == formatted


    def test_decimal_formatter(self):
        self._test_formatter(lcg.plot.DecimalFormatter(), (
            (1.0, '1'),
            (3.4, '3.40'),
            (120000, '120,000'),
            (2300000, '2,300,000'),
            (4234500000000, '4,234,500,000,000'),
        ))


    def test_decimal_formatter_with_precision(self):
        self._test_formatter(lcg.plot.DecimalFormatter(precision=3), (
            (1.0, '1.000'),
            (3.4, '3.400'),
            (1200, '1,200.000'),
        ))


    def test_abbreviating_monetary_formatter(self):
        self._test_formatter(lcg.plot.MonetaryFormatter(abbreviate=True), (
            (140000, '140,000'),
            (2400000, '2.4 mil.'),
            (3340000, '3.34 mil.'),
            (4341000, '4,341,000'),
            (5345100, '5,345,100'),
            (6500000000, '6.5 bil.'),
            (7530000000, '7.53 bil.'),
            (8532000000, '8.532 bil.'),
            (9000000000000, '9 tril.'),
            (1100000000000, '1.1 tril.'),
            (2120000000000, '2.12 tril.'),
            (3123000000000, '3.123 tril.'),
            (4123400000000, '4,123.400 bil.'),
            (5 * 10 ** 12, '5 tril.'),
        ))

    def test_translated_abbreviations(self):
        self._test_formatter(lcg.plot.MonetaryFormatter(abbreviate=True), (
            (1340000, '1,34 mil.'),
            (2500000000, '2,5 mld.'),
            (3100000000000, '3,1 bil.'),
        ), lang='cs')

    def plots(self):
        return (
            lcg.plot.LinePlot(
                (
                    (datetime.date(2019, 9, 10), 24),
                    (datetime.date(2019, 9, 18), 35),
                    (datetime.date(2019, 9, 24), 34),
                    (datetime.date(2019, 9, 25), 12),
                    (datetime.date(2019, 9, 28), 14),
                ),
                title='Zůstatek na účtu',
                lines=(lcg.plot.Line(x=datetime.date(2019, 9, 21), color='red'),),
            ),

            lcg.plot.LinePlot(
                (
                    (datetime.date(2019, 9, 10), 24),
                    (datetime.date(2019, 9, 18), 24),
                    (datetime.date(2019, 9, 18), 35),
                    (datetime.date(2019, 9, 24), 35),
                    (datetime.date(2019, 9, 24), 34),
                    (datetime.date(2019, 9, 25), 34),
                    (datetime.date(2019, 9, 25), 12),
                    (datetime.date(2019, 9, 28), 12),
                    (datetime.date(2019, 9, 28), 14),
                    (datetime.date(2019, 9, 30), 14),
                ),
                title='Zůstatek na účtu se skokovými změnami',
                size=(140, 50),
                lines=(
                    lcg.plot.Line(x=datetime.date(2019, 9, 21), color='red', style=':'),
                    lcg.plot.Line(y=15, color='red', style=':'),
                ),
            ),

            lcg.plot.LinePlot(
                ((1, 24, 11), (2, 35, 34), (3, 12, 32),
                 (5, 15, 20), (7, 10, 22), (8, 14, 4),
                 (10, 22, 8), (11, 18, 16), (12, 15, 20)),
                title='Dva grafy v jednom + grid',
                legend=('Praha', 'Brno'),
                grid=True,
                size=(300, 150),
                lines=(
                    lcg.plot.Line(x=8, width=3, style='dotted', color='red'),
                ),
            ),

            lcg.plot.LinePlot(
                (('leden', 24), ('únor', 15), ('březen', 28), ('duben', 14),
                 ('květen', 18), ('červen', 16), ('červenec', 24), ('srpen', 6),
                 ('zaří', 8), ('říjen', 14), ('listopad', 18), ('prosinec', 4)),
                title='Řetězcové hodnoty na ose X a anotace hodnot',
                annotate=True,
                grid=(True, True),
                size=(300, 150),
                xlabel='čas',
                ylabel='zůstatek',
            ),

            lcg.plot.BarPlot(
                (('leden', 24), ('únor', 15), ('březen', 28), ('duben', 14),
                 ('květen', 18), ('červen', 16), ('červenec', 24), ('srpen', 6),
                 ('zaří', 8), ('říjen', 14), ('listopad', 18), ('prosinec', 4)),
                title='Sloupcový graf',
                lines=(
                    lcg.plot.Line(y=20, width=3, style='dotted', color='red'),
                ),
                size=(300, 150),
            ),


            lcg.plot.BarPlot(
                ((1, 24, 11), (2, 35, 34), (3, 12, 32),
                 (5, 15, 20), (7, 10, 22), (8, 14, 4),
                 (10, 22, 8), (11, 18, 16), (12, 15, 20)),
                title='Vícesloupcový graf (dvě y hodnoty pro každou x)',
                legend=('Praha', 'Brno'),
                annotate=True,
                size=(300, 150),
            ),

            lcg.plot.BarPlot(
                (('leden', 24, 10), ('únor', 15, 20), ('březen', 28, 30), ('duben', 14, 20),
                 ('květen', 18, 10), ('červen', 16, 5), ('červenec', 24, 4), ('srpen', 6, 3),
                 ('zaří', 8, 2), ('říjen', 14, 1), ('listopad', 18, 1), ('prosinec', 4, 2)),
                title='Vícesloupcový graf s gridem',
                annotate=True,
                grid=(True, True),
                size=(300, 150),
            ),

            lcg.plot.BarPlot(
                (('leden', 24, 10, 2), ('únor', 15, 20, 4), ('březen', 28, 30, 8),
                 ('duben', 14, 20, 16), ('květen', 18, 10, 32), ('červen', 16, 5, 64),
                 ('červenec', 24, 4, 32), ('srpen', 6, 3, 16), ('zaří', 8, 2, 8),
                 ('říjen', 14, 1, 4), ('listopad', 18, 1, 2), ('prosinec', 4, 2, 1)),
                title='Vícenásobný sloupcový graf',
                legend=('foo', 'bar', 'baz'),
                annotate=True,
                grid=(True, True),
                xlabel='čas',
                ylabel='zůstatek',
                size=(300, 150),
            ),

            lcg.plot.BarPlot(
                (
                 (datetime.date(2019, 10, 1), Decimal('7439941.38'), Decimal('7034675.23')),
                 (datetime.date(2019, 10, 2), Decimal('7649941.38'), Decimal('6345646.70')),
                 (datetime.date(2019, 10, 3), Decimal('7196818.98'), Decimal('6718642.18')),
                ),
                title='Pokus',
                annotate=True,
                legend=('Moje', 'Tvoje'),
                size=(300, 150),
            ),

            lcg.plot.LinePlot(
                [(datetime.date(2019, 10, 1), Decimal('7589272.38'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 1), Decimal('7649941.38'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 2), Decimal('7649941.38'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 2), Decimal('7196818.98'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 3), Decimal('7196818.98'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 3), Decimal('7262582.48'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 4), Decimal('7262582.48'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 4), Decimal('7326663.36'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 5), Decimal('7326663.36'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 6), Decimal('7326663.36'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 7), Decimal('7326663.36'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 7), Decimal('7443477.51'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 8), Decimal('7443477.51'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 8), Decimal('7629532.21'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 9), Decimal('7629532.21'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 9), Decimal('7445157.82'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 10), Decimal('7445157.82'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 10), Decimal('7630049.76'), Decimal('7200000.00')),
                 (datetime.date(2019, 10, 11), Decimal('7630049.76'), Decimal('7200000.00'))],
                yformatter=lcg.plot.MonetaryFormatter(abbreviate=True),
                grid=(
                    lcg.plot.Line(style=':', color='black'),
                    True,
                    lcg.plot.Line(style=':', color='#eeeeee'),
                    True,
                ),
                size=(300, 150),
            ),
        )

    @pytest.mark.parametrize("output_format, exporter_cls, kwargs", [
        ('pdf', lcg.export.pdf.PDFExporter, {}),
        ('html', lcg.HtmlExporter, dict(allow_svg=True)),
        ('html', lcg.HtmlExporter, dict(allow_svg=False)),
    ])
    def test_plots(self, output_format, exporter_cls, kwargs):
        exporter = exporter_cls(translations=translation_path, **kwargs)
        node = lcg.ContentNode('x', title='Grafy', content=self.plots())
        context = exporter.context(node, 'cs')
        result = exporter.export(context)
        # HACK: Allow saving exported output to a file for review.
        if os.getenv('SAVE_PLOTS'):
            filename = '{}{}.{}'.format(os.getenv('SAVE_PLOTS'),
                                        '-svg' if kwargs.get('allow_svg') else '',
                                        output_format)
            warnings.warn("Writing output file: {}\n".format(filename))
            if output_format == 'html':
                result = result.encode('utf-8')
            with open(filename, 'wb') as f:
                f.write(result)


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__]))
