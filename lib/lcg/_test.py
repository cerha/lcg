#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004-2014 Brailcom, o.p.s.
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

import datetime
import os
import re
import string
import sys
import unittest

import lcg

_ = lcg.TranslatableTextFactory('test')

class TestSuite(unittest.TestSuite):
    def add(self, cls, prefix='test_'):
        tests = [cls(attr) for attr in dir(cls) if attr.startswith(prefix)]
        self.addTests(tests)

tests = TestSuite()

lcg_dir = os.path.normpath(os.path.join(__file__, '..', '..', '..'))
lcg.config.default_resource_dir = os.path.join(lcg_dir, 'resources')
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
        assert a1 == "Hi Joe, say hello to Bob.", a1
        assert b1 == "Hi Joe, say hello to Bob.", b1
        assert c1 == "Hi -person1-, say hello to -person2-.", c1
        
    def test_addition(self):
        a = lcg.TranslatableText("Version %s", "1.0")
        b = "xxx"
        c = a + b
        assert isinstance(c, lcg.Concatenation), c
        assert c == "Version 1.0xxx", c
        d = c + b
        assert isinstance(d, lcg.Concatenation), d
        e = b + a
        assert isinstance(e, lcg.Concatenation), e
        assert e == "xxxVersion 1.0", e
        f = b + c
        assert isinstance(f, lcg.Concatenation), f
        assert f == "xxxVersion 1.0xxx", f
        try:
            e = a + 1
        except TypeError as e:
            pass
        assert isinstance(e, TypeError), e
            
    def test_concat(self):
        a = lcg.concat(lcg.TranslatableText("Version %s", "1.0") + 'xx',
                       'yy', separator="\n")
        assert isinstance(a, lcg.Concatenation), a
        items = a.items()
        assert len(items) == 2, items
        assert items[1] == ('xx\nyy'), items[1]
        b = lcg.concat('a', ('b', 'c', 'd'), 'e', 'f', separator='-')
        assert isinstance(b, str), b
        assert b == 'a-b-c-d-e-f', b
        c = lcg.concat('a', (u'b', 'c', 'd'), 'e', 'f', separator='-')
        assert isinstance(c, unicode), c
        assert c == 'a-b-c-d-e-f', c
        
    def test_replace(self):
        t = lcg.TranslatableText("Version %s", "xox")
        a = t + '-yoy'
        b = t.replace('o', '-')
        c = a.replace('o', '-')
        d = c.replace('V', 'v')
        assert isinstance(a, lcg.Concatenation), a
        assert isinstance(b, lcg.TranslatableText), b
        assert isinstance(c, lcg.Concatenation), c
        assert isinstance(d, lcg.Concatenation), d
        ax = a.localize(lcg.Localizer())
        bx = b.localize(lcg.Localizer())
        cx = c.localize(lcg.Localizer())
        dx = d.localize(lcg.Localizer())
        assert str(a) == ax == 'Version xox-yoy', (a, ax)
        assert str(b) == bx == 'Versi-n x-x', (b, bx)
        assert str(c) == cx == 'Versi-n x-x-y-y', (c, cx)
        assert str(d) == dx == 'versi-n x-x-y-y', (d, dx)

    def test_transform(self):
        from xml.sax import saxutils
        a = _('His name is "%s"', _("Bob"))
        b = _("Bob") + ' + ' + _("Joe")
        c = a.transform(saxutils.quoteattr)
        d = b.transform(saxutils.quoteattr)
        e = "attr=" + d # Test transformed Concatenation nesting!
        f = lcg.concat('<tag ' + e + '>')
        assert isinstance(c, lcg.TranslatableText), c
        assert isinstance(d, lcg.Concatenation), d
        loc = lcg.Localizer('cs', translation_path=translation_path)
        ax = a.localize(loc)
        bx = b.localize(loc)
        cx = c.localize(loc)
        dx = d.localize(loc)
        ex = e.localize(loc)
        fx = f.localize(loc)
        assert str(a) == 'His name is "Bob"', str(a)
        assert str(b) == 'Bob + Joe', str(b)
        assert ax == 'Jmenuje se "Bobik"', ax
        assert bx == 'Bobik + Pepa', bx
        assert str(c) == '\'His name is "Bob"\'', str(c)
        assert str(d) == '"Bob + Joe"', str(d)
        assert str(e) == 'attr="Bob + Joe"', str(e)
        assert str(f) == '<tag attr="Bob + Joe">', str(f)
        assert cx == '\'Jmenuje se "Bobik"\'', cx
        assert dx == '"Bobik + Pepa"', dx
        assert ex == 'attr="Bobik + Pepa"', ex
        assert fx == '<tag attr="Bobik + Pepa">', fx

    def test_string_context(self):
        a = lcg.TranslatableText("Version %s", "1.0")
        assert a == "Version 1.0"
        b = lcg.TranslatableText("Info: %s", a)
        assert b == "Info: Version 1.0"
        c = lcg.concat("Info:", lcg.concat(a, '2006-08-14', separator=', '),
                       ('Mon', '10:32'), separator=' ')
        assert c == "Info: Version 1.0, 2006-08-14 Mon 10:32", c

tests.add(TranslatableText)


class TranslatablePluralForms(unittest.TestCase):
          
    def test_translation(self):
        loc = lcg.Localizer('cs', translation_path=translation_path)
        for n, translated in ((1, u"Mám 1 problém."),
                              (2, u"Mám 2 problémy."),
                              (5, u"Mám 5 problémů.")):
            a = _.ngettext("I have %d problem.", "I have %d problems.", n)
            b = a.localize(loc)
            assert b == translated, (b, translated)
        
    def test_interpolation(self):
        t = lcg.Localizer('cs', translation_path=translation_path)
        for n, translated in ((1, u"1 záznam nalezen v tabulce xy."),
                              (2, u"2 záznamy nalezeny v tabulce xy."),
                              (5, u"5 záznamů nalezeno v tabulce xy.")):
            a = _.ngettext("%(n)d record found in table %(name)s.",
                           "%(n)d records found in table %(name)s.", n=n, name='xy')
            b = a.localize(t)
            assert b == translated, (b, translated)
        
    def test_replace(self):
        loc = lcg.Localizer('cs', translation_path=translation_path)
        for n, ta, tb in ((1, u"Mám 1 problém.", u"1 záznam nalezen v tabulce xy."),
                          (2, u"Mám 2 problémy.", u"2 záznamy nalezeny v tabulce xy."),
                          (5, u"Mám 5 problémů.", u"5 záznamů nalezeno v tabulce xy.")):
            a = _.ngettext("I have %d problem.", "I have %d problems.", n)
            a1 = a.replace('5', '123')
            a2 = a1.localize(loc)
            ta1 = ta.replace('5', '123')
            assert a2 == ta1, (a2, ta1)
            b = _.ngettext("%(n)d record found in table %(name)s.",
                           "%(n)d records found in table %(name)s.", n=n, name='xy')
            b1 = b.replace('5', '123')
            b2 = b1.localize(loc)
            tb1 = tb.replace('5', '123')
            assert b2 == tb1, (b2, tb1)
            
tests.add(TranslatablePluralForms)


class SelfTranslatableText(unittest.TestCase):
          
    def test_interpolation(self):
        text = "%(person1)s is smarter than %(person2)s."
        translations = {'cs': u"%(person1)s je chytřejší než %(person2)s."}
        a = lcg.SelfTranslatableText(text, person1="Joe", person2="Ann", translations=translations)
        a2 = lcg.SelfTranslatableText(text, translations=translations)
        a3 = a2.interpolate(lambda key: '-' + key + '-')
        b = a.localize(lcg.Localizer())
        c = a.localize(lcg.Localizer('cs', translation_path=translation_path))
        assert b == "Joe is smarter than Ann.", b
        assert c == u"Joe je chytřejší než Ann.", c
        b2 = a3.localize(lcg.Localizer())
        c2 = a3.localize(lcg.Localizer('cs', translation_path=translation_path))
        assert b2 == "-person1- is smarter than -person2-.", b2
        assert c2 == u"-person1- je chytřejší než -person2-.", c2
        
tests.add(SelfTranslatableText)

class LocalizableDateTime(unittest.TestCase):
    class tzinfo(datetime.tzinfo):
        def __init__(self, offset):
            self._offset = offset
        def utcoffset(self, dt):
            return datetime.timedelta(minutes=self._offset)
        def tzname(self, dt):
            offset = self._offset
            sign = offset / abs(offset)
            div, mod = divmod(abs(offset), 60)
            if mod:
                return "GMT %+d:%d" % (div * sign, mod)
            else:
                return "GMT %+d" % div * sign
        def dst(self, dt):
            return datetime.timedelta(0)
    
    def test_localize(self):
        d1 = lcg.LocalizableDateTime("2006-12-21")
        d2 = lcg.LocalizableDateTime("2006-12-21 02:43", show_time=False)
        d3 = lcg.LocalizableDateTime("2006-12-21 02:43")
        d4 = lcg.LocalizableDateTime("2006-12-21 18:43:32", show_weekday=True)
        d5 = lcg.LocalizableDateTime("2006-01-30", leading_zeros=False)
        d6 = lcg.LocalizableDateTime("2006-12-21 18:43:32", utc=True)
        loc1 = lcg.Localizer('en', translation_path=translation_path)
        x1 = d1.localize(loc1)
        x2 = d2.localize(loc1)
        x3 = d3.localize(loc1)
        x4 = d4.localize(loc1)
        x5 = d5.localize(loc1)
        x6 = d6.localize(loc1)
        assert x1 == "21/12/2006", x1
        assert x2 == "21/12/2006", x2
        assert x3 == "21/12/2006 02:43 AM", x3
        assert x4 == "Thu 21/12/2006 06:43:32 PM", x4
        assert x5 == "30/1/2006", x5
        assert x6 == "21/12/2006 06:43:32 PM UTC", x6
        loc2 = lcg.Localizer('cs', translation_path=translation_path, timezone=self.tzinfo(-60))
        y1 = d1.localize(loc2)
        y2 = d2.localize(loc2)
        y3 = d3.localize(loc2)
        y4 = d4.localize(loc2)
        y5 = d5.localize(loc2)
        y6 = d6.localize(loc2)
        assert y1 == "21.12.2006", y1
        assert y2 == "21.12.2006", y2
        assert y3 == "21.12.2006 02:43", y3
        assert y4 == u"Čt 21.12.2006 18:43:32", y4
        assert y5 == "30.1.2006", y5
        assert y6 == u"21.12.2006 17:43:32", y6
        
    def test_concat(self):
        d = lcg.LocalizableDateTime("2006-01-30")
        c = "Date is: " + d
        t = c.localize(lcg.Localizer('en', translation_path=translation_path))
        assert t == "Date is: 30/01/2006", t
        t = c.localize(lcg.Localizer('cs', translation_path=translation_path))
        assert t == "Date is: 30.01.2006", t

    def test_replace(self):
        a = lcg.LocalizableDateTime("2006-01-30")
        b = a.replace('-', '+')
        c = a.replace('/', '|')
        d = a.replace('.', ':')
        loc1 = lcg.Localizer('en', translation_path=translation_path)
        loc2 = lcg.Localizer('cs', translation_path=translation_path)
        b1 = b.localize(loc1)
        b2 = b.localize(loc2)
        assert str(b) == "2006+01+30", str(b)
        assert b1 == "30/01/2006", b1
        assert b2 == "30.01.2006", b2
        c1 = c.localize(loc1)
        c2 = c.localize(loc2)
        assert str(c) == "2006-01-30", str(c)
        assert c1 == "30|01|2006", c1
        assert c2 == "30.01.2006", c2
        d1 = d.localize(loc1)
        d2 = d.localize(loc2)
        assert str(d) == "2006-01-30", str(d)
        assert d1 == "30/01/2006", d1
        assert d2 == "30:01:2006", d2

tests.add(LocalizableDateTime)

class LocalizableTime(unittest.TestCase):

    def test_format(self):
        t1 = lcg.LocalizableTime("02:43")
        t2 = lcg.LocalizableTime("18:43:32")
        t1cs = t1.localize(lcg.Localizer('cs', translation_path=translation_path))
        t2cs = t2.localize(lcg.Localizer('cs', translation_path=translation_path))
        t1no = t1.localize(lcg.Localizer('no', translation_path=translation_path))
        t2no = t2.localize(lcg.Localizer('no', translation_path=translation_path))
        assert t1cs == "02:43", t1cs
        assert t2cs == "18:43:32", t2cs
        assert t1no == "02.43", t1no
        assert t2no == "18.43.32", t2no

tests.add(LocalizableTime)


class TranslatableTextFactory(unittest.TestCase):

    def test_domain(self):
        a = _("%(name1)s is smarter than %(name2)s.", name1=_("Joe"), name2=_("Bob"))
        assert a.domain() == 'test'

tests.add(TranslatableTextFactory)

class Monetary(unittest.TestCase):

    def test_format(self):
        a = lcg.Monetary(8975.5)
        a1 = lcg.Localizer().localize(a)
        a2 = lcg.Localizer('cs').localize(a)
        a3 = lcg.Localizer('en').localize(a)
        assert a1 == '8975.50', a1
        assert a2 == u'8\xa0975,50', a2
        assert a3 == '8,975.50', a3
    
    def test_precision(self):
        a = lcg.Monetary(8975.5, precision=0)
        b = lcg.Monetary(8975.5, precision=3)
        a1 = lcg.Localizer().localize(a)
        b1 = lcg.Localizer().localize(b)
        assert a1 == '8976', a1
        assert b1 == '8975.500', b1

    def test_transform(self):
        a = lcg.Monetary(8975.5, precision=2)
        b = a.transform(lambda x: x.replace('.', ','))
        a1 = lcg.Localizer().localize(a)
        b1 = lcg.Localizer().localize(b)
        assert a1 == '8975.50', a1
        assert b1 == '8975,50', b1
        
tests.add(Monetary)


class GettextTranslator(unittest.TestCase):

    def test_translate(self):
        t = lcg.Localizer('cs', translation_path=translation_path).translator()
        a = "%(name1)s is smarter than %(name2)s."
        b = t.gettext(a, domain='test')
        assert b == u"%(name1)s je chytřejší než %(name2)s.", b

tests.add(GettextTranslator)


class ContentNode(unittest.TestCase):
    
    def test_misc(self):
        b = lcg.ContentNode('b', content=lcg.TextContent("B"))
        a = lcg.ContentNode('a', content=lcg.TextContent("A"), children=(b,))
        assert a.id() == 'a'
        assert a.root() == b.root() == a

tests.add(ContentNode)


class Resources(unittest.TestCase):
    
    def test_provider(self):
        warnings = []
        def warn(msg):
            warnings.append(msg)
        p = lcg.ResourceProvider(resources=(lcg.Audio('xxx.ogg'),))
        r = p.resource('xxx.xx', warn=warn)
        assert r is None, r
        assert len(warnings) == 1, warnings
        r = p.resource('xxx.mp3', warn=warn)
        assert r is None, r
        assert len(warnings) == 2, warnings
        r = p.resource('xxx.ogg')
        assert isinstance(r, lcg.Audio), r
        assert len(warnings) == 2, warnings
        r = p.resource('default.css')
        assert isinstance(r, lcg.Stylesheet), r
        assert len(warnings) == 2, warnings
        
    def test_dependencies(self):
        p = lcg.ResourceProvider(resources=(lcg.Audio('sound1.ogg'),
                                            lcg.Audio('sound2.ogg')))
        a = lcg.ContentNode('a', content=lcg.Content(), resource_provider=p)
        b = lcg.ContentNode('b', content=lcg.Content(), resource_provider=p)
        a.resource('default.css')
        b.resource('media.js')
        ar = [r.filename() for r in a.resources()]
        assert len(ar) == 3, ar
        assert 'default.css' in ar and 'sound1.ogg' in ar and 'sound2.ogg' in ar, ar
        br = [r.filename() for r in b.resources()]
        assert len(br) == 3, br
        assert 'media.js' in br and 'sound1.ogg' in br and 'sound2.ogg' in br, br

tests.add(Resources)


class Parser(unittest.TestCase):

    def setUp(self):
        self._parser = lcg.Parser()
        
    def test_simple_text(self):
        text = "Hallo, how are you?\n\n  * one\n  * two\n  * three\n"
        c = self._parser.parse(text)
        assert (len(c) == 2 and isinstance(c[0], lcg.Paragraph) and
                isinstance(c[1], lcg.ItemizedList)), c
        assert len(c[1].content()) == 3, c[1].content()
        assert c[1].order() is None, c[1].order()

    def test_sections(self):
        text = "= Main =\n== Sub1 ==\n== Sub2 ==\n=== SubSub1 ===\n== Sub3 =="
        c = self._parser.parse(text)
        assert len(c) == 1 and isinstance(c[0], lcg.Section), c
        s = c[0].sections(None)
        assert len(s) == 3 and isinstance(s[0], lcg.Section) and \
            len(s[0].sections(None)) == 0 and len(s[1].sections(None)) == 1 and \
            len(s[2].sections(None)) == 0, s

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
        assert 'page_header' in parameters, parameters
        assert 'page_footer' in parameters, parameters
        assert 'first_page_header' not in parameters, parameters
        header = parameters['page_header']
        assert header.content()[0].content()[0].content()[0].text() == 'hello', \
            header.content()[0].content()[0].content()[0].text()
        footer = parameters['page_footer']
        assert footer.content()[0].halign() == lcg.HorizontalAlignment.CENTER, \
            footer.content()[0].content().halign()

    def test_hrule(self):
        text = '''
blah blah

----

blah blah
'''
        c = self._parser.parse(text)
        assert len(c) == 3, c
        assert isinstance(c[1], lcg.HorizontalSeparator), c[1]

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
            assert len(c) == 3, c
            assert c[0].halign() is None, c[0].content()[0].content()[0].halign()
            assert c[1].halign() == constant, c[0].content()[0].content()[0].halign()
            assert c[2].halign() is None, c[0].content()[0].content()[0].halign()

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
        assert len(c) == 3, c
        assert all([isinstance(x, lcg.Table) for x in c]), c
        for i in range(3):
            rows = c[i].content()
            assert len(rows) == 2, rows
            assert all([isinstance(r, lcg.TableRow) for r in rows]), rows
            for cell in rows[0].content():
                assert isinstance(cell, lcg.TableHeading), rows[0]
            for cell in rows[1].content():
                assert isinstance(cell, lcg.TableCell), rows[1]
        row = c[2].content()[1]
        cells = row.content()
        assert cells[0].align() == lcg.TableCell.RIGHT, cells[0].align()
        assert cells[1].align() == lcg.TableCell.CENTER, cells[1].align()
        bars = c[2].bars()
        assert 1 in bars, bars
        assert 2 in bars, bars
        assert 0 not in bars, bars

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
        assert len(c) == 1, c
        assert isinstance(c[0], lcg.ItemizedList), c[0]
        assert c[0].order() is None, c[0].order()
        items = c[0].content()
        assert len(items) == 3, items
        # First item contents
        item_content = items[0].content()
        assert len(item_content) == 2, item_content
        assert isinstance(item_content[0], lcg.Paragraph), item_content[0]
        assert isinstance(item_content[1], lcg.ItemizedList), item_content[1]
        assert item_content[1].order() == lcg.ItemizedList.NUMERIC, item_content[1].order()
        assert len(item_content[1].content()) == 2, item_content[1].content()
        # Second item contents
        item_content = items[1].content()
        assert len(item_content) == 2, item_content
        assert isinstance(item_content[0], lcg.Paragraph), item_content[0]
        assert isinstance(item_content[1], lcg.ItemizedList), item_content[1]
        assert item_content[1].order() == lcg.ItemizedList.LOWER_ALPHA, item_content[1].order()
        assert len(item_content[1].content()) == 2, item_content[1].content()

    def test_paragraph_newline(self):
        c = self._parser.parse('hello\n\nworld')
        assert c[0].content()[0].content()[0].text()[-1] == 'o', "Extra newline after paragraph?"
                
tests.add(Parser)

class MacroParser(unittest.TestCase):

    def test_simple_condition(self):
        text = "@if x\nX\n@else\nY@endif\n"
        r = lcg.MacroParser(globals=dict(x=True)).parse(text)
        assert r == "X\n", repr(r)

    def test_condition(self):
        def check(contidion, expected_result, **globals):
            text = ("@if " + contidion + "\nTrue\n@else\nFalse\n@endif")
            parser = lcg.MacroParser(globals=globals)
            result = parser.parse(text).strip() == 'True'
            assert result == expected_result, (contidion, globals, result)
        # Some more complicated condition.
        c1 = "a in ('A', 'B', 'C') and b > 3 and b+5 <= c and c is not None"
        check(c1, True, a='A', b=5, c=55)
        check(c1, False, a='X', b=5, c=None)
        # Try using builtins.
        c2 = "ord(a) == b and chr(b) == a and sum((b,c,3)) >= 70 and any([True, False, a == b])"
        check(c2, True, a='A', b=65, c=2)
        check(c2, False, a='X', b=5, c=2)

    def test_exception(self):
        text = "A\n@if a/b == c\nX@else\nY\n@endif\n\nB\n\n"
        r = lcg.MacroParser(globals=dict(a=5, b=0, c=2)).parse(text)
        assert r == "A\nZeroDivisionError: integer division or modulo by zero\nB\n\n", repr(r)
        
    def test_condition_newlines(self):
        text = "A\n@if x\nX\n@endif\n\nB\n\n"
        r = lcg.MacroParser(globals=dict(x=True)).parse(text)
        assert r == "A\nX\n\nB\n\n", repr(r)

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
        assert r1 == join("A", "B", "E"), r1
        assert r2 == join("A", "C", "D", "E"), r2
        assert r3 == join("A", "D", "E"), r3

    def test_inclusion(self):
        text = "Foo\n@include bar\nBaz\n"
        r = lcg.MacroParser(globals=dict(bar='Bar')).parse(text)
        assert r == "Foo\nBar\nBaz\n", repr(r)

tests.add(MacroParser)


class HtmlImport(unittest.TestCase):

    def test_html(self):
        html = u''' <p>
         some text <span class="lcg-mathml" contenteditable="false" style="display: inline-block;"><math contenteditable="false" style="display:inline-block" xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mstyle displaystyle="true"><msup><mi>x</mi><mn>2</mn></msup><mo>+</mo><msup><mi>y</mi><mn>2</mn></msup></mstyle><annotation encoding="ASCII">x^2 + y^2</annotation></semantics></math></span></p>
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
         Písmo <strong>tučné</strong>, <em>zvýrazněné</em>, <u>podtržené</u>, <strike>škrtnuté</strike>, index<sub>dolní</sub> , index<sup>horní</sup>.</p>
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
         <a href="http://www.brailcom.org">Vložíme link na http://www.brailcom.org</a>, a uděláme <a name="kotva">kotvu</a>.</p>
 <p>
         Teď se odkážeme na tu <a href="#kotva">kotvu</a>. Budeme taky <a href="mailto:info@brailcom.org?subject=LCG%20testing">mailovat</a>.</p>
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
 Image link: <a href="http://www.freebsoft.org"><img src="http://www.freebsoft.org/img/logo.gif" /></a>
 Audio: <a class="lcg-audio" data-lcg-resource="my-song.mp3" href="/whatever/my-song.mp3">My Song</a>
 Video: <a class="lcg-video" data-lcg-resource="my-video.flv" href="/whatever/my-video.flv">My Video</a>

<div class="lcg-exercise" contenteditable="false" data-type="MultipleChoiceQuestions" style="display: inline-block;">
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
        
tests.add(HtmlImport)


class HtmlExport(unittest.TestCase):
    
    def test_generator(self):
        g = lcg.HtmlGenerator()
        localizer = lcg.Localizer('cs', translation_path=translation_path)
        for generated, html in (
                (g.a('X', href='x'),
                 '<a href="x">X</a>'),
                (g.button('X', disabled=True),
                 '<button disabled="disabled" type="button">X</button>'),
        ):
            result = localizer.localize(generated)
            assert result == html, "\n  - expected: %r\n  - got:      %r" % (html, result)
            
    def test_export(self):
        n = lcg.ContentNode('test', title='Test', content=lcg.Content(),
                            globals=dict(x='value of x'))
        context = lcg.HtmlExporter().context(n, None, sec_lang='es')
        for content, html in (
            (('a', ' ', lcg.strong('b ', lcg.em('c'), ' ', lcg.u('d')), ' ', lcg.code('e')),
             'a <strong>b <em>c</em> <u>d</u></strong> <code>e</code>'),
            (lcg.cite('x'),
             '<span lang="es" class="lcg-citation">x</span>'),
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
            (lcg.p('Kotva: ', lcg.Anchor('x', text='zde'), halign=lcg.HorizontalAlignment.RIGHT),
             '<p style="text-align: right;">Kotva: <span id="x">zde</span></p>'),
        ):
            result = lcg.coerce(content).export(context)
            assert result == html, "\n  - content:  %r\n  - expected: %r\n  - got:      %r" % \
                (content, html, result)
            
    def test_formatting(self):
        def check(result, expected_result):
            if isinstance(expected_result, basestring):
                ok = result == expected_result
            else:
                ok = expected_result.match(result)
                expected_result = expected_result.pattern
            assert ok, ("\n  - source text: %r"
                        "\n  - expected:    %r"
                        "\n  - got:         %r" % (text, expected_result, result))
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
        for text, html in (
            ('a *b /c/ _d_* =e=',
             'a <strong>b <em>c</em> <u>d</u></strong> <code>e</code>'),
            ('a */b', # Unfinished markup (we probably don't want that, but now it works so).
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
            # Video service links
            ('http://www.youtube.com/watch?v=xyz123',
             (u'<object type="application/x-shockwave-flash" title="Flash movie object" '
              u'data="http://www.youtube.com/v/xyz123?rel=0" width="500" height="300">'
              u'<param name="movie" value="http://www.youtube.com/v/xyz123?rel=0"/>'
              u'<param name="wmode" value="opaque"/></object>')),
            ('http://www.vimeo.com/xyz123',
             (u'<object type="application/x-shockwave-flash" title="Flash movie object" '
              u'data="http://vimeo.com/moogaloop.swf?clip_id=&amp;server=vimeo.com" '
              u'width="500" height="300">'
              u'<param name="movie" value="http://vimeo.com/moogaloop.swf?'
              u'clip_id=&amp;server=vimeo.com"/><param name="wmode" value="opaque"/></object>')),
            # Inline images
            ('[aa.jpg]',
             '<img src="images/aa.jpg" alt="" class="lcg-image image-aa"/>'),
            ('*[aa.jpg]*',
             '<strong><img src="images/aa.jpg" alt="" class="lcg-image image-aa"/></strong>'),
            ('[aa.jpg label]',
             '<img src="images/aa.jpg" alt="label" class="lcg-image image-aa"/>'),
            ('[aa.jpg:20x30 label]',
             ('<img src="images/aa.jpg" height="30" width="20" alt="label" '
              'class="lcg-image image-aa"/>')),
            ('[>aa.jpg]',
             ('<img src="images/aa.jpg" align="right" alt="" '
              'class="lcg-image right-aligned image-aa"/>')),
            ('[<aa.jpg]',
             ('<img src="images/aa.jpg" align="left" alt="" '
              'class="lcg-image left-aligned image-aa"/>')),
            ('[aa.jpg label | descr]',
             '<img src="images/aa.jpg" alt="label: descr" class="lcg-image image-aa"/>'),
            ('[http://www.freebsoft.org/img/logo.gif Free(b)soft logo]',
             ('<img src="http://www.freebsoft.org/img/logo.gif" alt="Free(b)soft logo" '
              'class="lcg-image image-logo"/>')),
            ('[cc.png]',
             '<img src="images/cc.png" alt="Image C: Nice picture" class="lcg-image image-cc"/>'),
            # Image links (links with an image instead of a label)
            ('[aa.jpg bb.jpg label | descr]',
             ('<a href="images/aa.jpg" title="descr">'
              '<img src="images/bb.jpg" alt="label" class="lcg-image image-bb"/></a>')),
            ('[aa.jpg bb.jpg | descr]',
             ('<a href="images/aa.jpg" title="descr">'
              '<img src="images/bb.jpg" alt="" class="lcg-image image-bb"/></a>')),
            ('[>aa.jpg bb.jpg label | descr]',
             ('<a href="images/aa.jpg" title="descr">'
              '<img src="images/bb.jpg" align="right" alt="label" '
              'class="lcg-image right-aligned image-bb"/></a>')),
            ('[test bb.jpg bb]',
             ('<a href="test" title="Some description">'
              '<img src="images/bb.jpg" alt="bb" class="lcg-image image-bb"/></a>')),
            ('[http://www.freebsoft.org /img/logo.gif]',
             ('<a href="http://www.freebsoft.org">'
              '<img src="/img/logo.gif" alt="" class="lcg-image image-logo"/></a>')),
            ('[http://www.freebsoft.org /img/logo.gif Free(b)soft website]',
             ('<a href="http://www.freebsoft.org">'
              '<img src="/img/logo.gif" alt="Free(b)soft website" '
              'class="lcg-image image-logo"/></a>')),
            (('[http://www.freebsoft.org /img/logo.gif Free(b)soft website | '
              'Go to Free(b)soft website]'),
             ('<a href="http://www.freebsoft.org" title="Go to Free(b)soft website">'
              '<img src="/img/logo.gif" alt="Free(b)soft website" '
              'class="lcg-image image-logo"/></a>')),
            # Absolute image links
            ('http://www.freebsoft.org/img/logo.gif',
             ('<img src="http://www.freebsoft.org/img/logo.gif" alt="" '
              'class="lcg-image image-logo"/>')),
            # Audio player links
            ('[xx.mp3]',
             re.compile(r'<a href="media/xx.mp3" id="[a-z0-9-]+" '
                        r'class="media-control-link">xx.mp3</a>')),
            ('[/somewhere/some.mp3]',
             re.compile(r'<a href="/somewhere/some.mp3" id="[a-z0-9-]+" '
                        r'class="media-control-link">/somewhere/some.mp3</a>')),
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
            parsed_result = content.export(context)
            check(parsed_result, html)

tests.add(HtmlExport)


class BrailleExport(unittest.TestCase):

    def _load_presentation(self):
        return lcg.export.braille_presentation(presentation_file='presentation-braille-test.py')

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
        elif isinstance(braille, (tuple, list,)):
            expected = [header + braille[0] +
                        '\n' * (page_lines - len(braille[0].split('\n')) - 2) + footer[0]]
            expected.extend([b + '\n' * (page_lines - len(b.split('\n'))) + f
                             for b, f in zip(braille, footer)[1:]])
        else:
            self.assertRaises(braille, exporter.export, context)
            return
        result = exporter.export(context).split('\f')[:-1]
        if result != expected:
            sys.stdout.write('*** Expected:\n')
            sys.stdout.write(string.join(expected, '\f').encode('utf-8') + '\n')
            sys.stdout.write('*** Got:\n')
            sys.stdout.write(string.join(result, '\f').encode('utf-8') + '\n')
        assert result == expected, \
            ("\n  - source text: %r\n  - expected:    %r\n  - got:         %r" %
             (text, expected, result,))

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
            self._test(text, braille, u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁',
                       presentation, 'cs')
        tests = ((u'abc', u'⠁⠃⠉',),
                 (u'a line to be hyphenated', u'⠁⠀⠇⠊⠝⠑⠀⠞⠕⠀⠃⠑⠀⠓⠽⠏⠓⠑⠝⠤\n⠁⠞⠑⠙',),
                 (u'*bold*', u'⠸⠃⠕⠇⠙',),
                 (u'/italic/', u'⠨⠊⠞⠁⠇⠊⠉',),
                 (u'_underlined_', u'⠥⠝⠙⠑⠗⠇⠊⠝⠑⠙',),)
        if False:
            # buggy in current liblouis
            tests += ((u'a a11a 1', u'⠁⠀⠁⠼⠁⠁⠐⠁⠀⠼⠁',),)
        for text, braille in tests:
            self._test(text, braille, u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁',
                       presentation, 'en')

    def test_languages(self):
        presentation = self._load_presentation()
        self._test(u'řwe >>world<< řwe', u'⠺⠷⠑⠀⠺⠕⠗⠇⠙⠀⠺⠷⠑', u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', 'en')

    def test_special_formatting(self):
        presentation = self._load_presentation()
        self._test(u'50 %, 12 ‰', u'⠼⠑⠚⠼⠏⠂⠀⠼⠁⠃⠼⠗', u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁',
                   presentation, 'cs')

    def test_tables(self):
        presentation = self._load_presentation()
        # Simple tables
        self._test(u'| first | line | x |\n| second | row | y |',
                   u'⠋⠊⠗⠎⠞⠀⠀⠀⠇⠊⠝⠑⠀⠀⠭\n⠎⠑⠉⠕⠝⠙⠀⠀⠗⠕⠷⠀⠀⠀⠽',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| *heading* | *h* | *h* |\n| first | line | x |\n| second | row | y |',
                   u'⠓⠑⠁⠙⠊⠝⠛⠀⠀⠓⠀⠀⠀⠀⠀⠓\n⠋⠊⠗⠎⠞⠀⠀⠀⠀⠇⠊⠝⠑⠀⠀⠭\n⠎⠑⠉⠕⠝⠙⠀⠀⠀⠗⠕⠷⠀⠀⠀⠽',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        # Compact wide tables
        self._test(u'| Narrow | Table |', u'⠠⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| Less Narrow | Table |', u'⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| Less Narrow | Table |\n| Less Narrow | Table |',
                   u'⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑\n⠇⠑⠎⠎⠀⠝⠁⠗⠗⠕⠷⠀⠀⠠⠞⠁⠃⠇⠑',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| *a* | *b* |\n| prefixed lines | table |\n| prefixed rows | cell |\n',
                   u'⠏⠗⠑⠋⠊⠭⠑⠙⠀⠁⠀⠀⠃⠀⠀⠀⠀\n⠇⠊⠝⠑⠎⠀⠀⠀⠀⠀⠀⠀⠞⠁⠃⠇⠑\n⠗⠕⠷⠎⠀⠀⠀⠀⠀⠀⠀⠀⠉⠑⠇⠇⠀',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        self._test(u'| *a* | *b* |\n| line & suffix | table |\n| row & suffix | cell |\n',
                   u'⠁⠀⠼⠯⠀⠎⠥⠋⠋⠊⠭⠀⠀⠃⠀⠀⠀⠀\n⠇⠊⠝⠑⠀⠀⠀⠀⠀⠀⠀⠀⠀⠞⠁⠃⠇⠑\n⠗⠕⠷⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠑⠇⠇⠀',
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
        # Double page tables
        self._test(u'| this is | a double page | table |\n| the | columns | are too wide |',
                   (u'⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    u'⠞⠓⠊⠎⠀⠊⠎⠀⠀⠁⠀⠙⠕⠥⠃⠇⠑⠀⠏⠁\n⠞⠓⠑⠀⠀⠀⠀⠀⠀⠉⠕⠇⠥⠍⠝⠎⠀⠀⠀⠀',
                    u'⠛⠑⠀⠀⠞⠁⠃⠇⠑⠀⠀⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠁⠗⠑⠀⠞⠕⠕⠀⠷⠊⠙⠑',),
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   (u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁',
                    u'⠼⠃⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑',
                    u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠉',),
                   presentation, 'cs', full_parse=True)
        self._test((u'some text\n\n'
                    u'| this is | a double page | table |\n| the | columns | are too wide |\n\n'
                    u'another text\n'),
                   (u'⠎⠕⠍⠑⠀⠞⠑⠭⠞\n\n⠞⠓⠑⠀⠞⠁⠃⠇⠑⠀⠊⠎⠀⠗⠑⠁⠙\n⠁⠉⠗⠕⠎⠎⠀⠋⠁⠉⠊⠝⠛⠀⠏⠁⠛⠑⠎⠄',
                    u'⠞⠓⠊⠎⠀⠊⠎⠀⠀⠁⠀⠙⠕⠥⠃⠇⠑⠀⠏⠁\n⠞⠓⠑⠀⠀⠀⠀⠀⠀⠉⠕⠇⠥⠍⠝⠎⠀⠀⠀⠀',
                    u'⠛⠑⠀⠀⠞⠁⠃⠇⠑⠀⠀⠀⠀⠀⠀⠀\n⠀⠀⠀⠀⠁⠗⠑⠀⠞⠕⠕⠀⠷⠊⠙⠑',
                    u'⠁⠝⠕⠞⠓⠑⠗⠀⠞⠑⠭⠞',),
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n',
                   (u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁',
                    u'⠼⠃⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑',
                    u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠉',
                    u'⠼⠙⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑',),
                   presentation, 'cs', full_parse=True)
        # Super wide tables
        self._test(u'| extremely wide table | very very wide table |\n| next | line |',
                   lcg.BrailleError,
                   u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠀⠀⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑⠀⠀⠀⠼⠁', presentation, 'cs', full_parse=True)
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
            result = exported.split('\n\n')[1]
            assert result == expected_result, (("\n  - source text: %r\n  - expected:    %r\n  - "
                                                "got:         %r") %
                                               (mathml, expected_result, result,))
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
        result = exported.split('\n\n')[1]
        assert result == u'''⠠⠞⠗⠕⠉⠓⠁⠀⠍⠁⠞⠑⠍⠁⠞⠊⠅⠽
⠦⠼⠁⠀⠲⠼⠁⠀⠶⠼⠃⠴
⠝⠑⠥⠱⠅⠕⠙⠌⠄''', repr(result)

    def test_mathml_nemeth(self):
        python_version = sys.version_info
        can_parse_entities = (python_version[0] >= 3 or
                             python_version[0] == 2 and python_version[1] >= 7)
        entity_regexp = re.compile('&[a-zA-Z]+;')
        def test(mathml, expected_result, lang='cs', page_width=None, pre=None, post=None):
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
            if page_width is not None:
                presentation.page_width = page_width
            presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
            n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                                content=content)
            exporter = lcg.BrailleExporter()
            context = exporter.context(n, lang=lang, presentation=presentation_set)
            exported = exporter.export(context)
            result = exported.split('\n\n')[1]
            if post == '.':
                result = result[:-2] + u'⠲'
            elif post == ',':
                result = result[:-2] + u'⠠'
            assert result == expected_result, (("\n  - source text: %r\n  - expected:    %r\n  - "
                                                "got:         %r") %
                                               (mathml, expected_result, result,))
        # §8
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3,76</mn></mrow>
</math>''', u'⠼⠒⠨⠶⠖', lang='cs') # decimal point
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', u'⠼⠒⠨⠶⠖', lang='cs') # decimal point
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>1,378</mn></mrow>
</math>''', u'⠼⠂⠠⠒⠶⠦', lang='en') # comma
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>3.76</mn></mrow>
</math>''', u'⠼⠒⠨⠶⠖', lang='en') # decimal point
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
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>sin</mi><mn>2</mn></msup><mo>&ApplyFunction;</mo><mn>2</mn><mi>x</mi></mrow>
</math>''', u'⠎⠊⠝⠘⠆⠀⠼⠆⠭')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mn>0.333</mn><mo>&hellip;</mo><mn>3</mn><mo>&hellip;</mo></mrow>
</math>''', u'⠼⠴⠨⠒⠒⠒⠀⠄⠄⠄⠀⠼⠒⠀⠄⠄⠄', lang='en')
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msub><mi>log</mi><mn>10</mn></msub><mo>&ApplyFunction;</mo><mn>2</mn></mrow>
</math>''', u'⠇⠕⠛⠂⠶⠀⠼⠆')
        if False:
            # Proper spacing not yet implemented
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
        if False:
            # Determinant: not yet implemented
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfenced open="|" close="|" separators=","><mtable>
 <mtr><mtd><mn>1</mn></mtd><mtd><mn>2</mn></mtd></mtr>
 <mtr><mtd><mi>-3</mi></mtd><mtd><mi>-4</mi></mtd></mtr>
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
        if False:
            # Closing parenthesis rendered incorrectly:
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
        if False:
            # Not yet supported
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
</math>''', u'⠼⠂⠴⠠⠴⠴⠴', lang='en') # comma
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
        if False:
            # Not yet supported
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
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>x</mi><mo>&prime;</mo></msup><mo>,</mo><msup><mi>x</mi><mo>&Prime;</mo></msup>
<mo>,</mo><msub><mi>x</mi><mn>1</mn></msub><mo>,</mo><msub><mi>x</mi><mi>a</mi></msub><mo>,</mo>
<msup><mi>x</mi><mn>2</mn></msup><mo>,</mo><mover accent="true"><mi>x</mi><mo>&macr;</mo></mover>
</mrow>
</math>''', u'⠭⠄⠠⠀⠭⠄⠄⠠⠀⠭⠂⠠⠀⠭⠰⠁⠠⠀⠭⠘⠰⠠⠀⠭⠱')
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
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><msup><mi>e</mi><mrow><mi>sin</mi><mo>&ApplyFunction;</mo><mi>x</mi></mrow></msup></mrow>
</math>''', u'⠑⠘⠎⠊⠝⠀⠭')
        if False:
            # Proper spacing not yet implemented
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&angle;</mo><mi>a</mi></mrow>
</math>''', u'⠫⠪⠀⠁')
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>&triangle;</mo><mi>a</mi><mi>c</mi><mi>r</mi></mrow>
</math>''', u'⠫⠞⠀⠁⠉⠗')
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>&#x25FD;</mo><mi>y</mi></mrow>
</math>''', u'⠭⠀⠫⠲⠀⠽')
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>|</mo><mtable><mtr><mtd><mi>a</mi></mtd><mtd><mi>b</mi></mtd><mtd><mi>c</mi></mtd></mtr>
<mtr><mtd><mi>d</mi></mtd><mtd><mi>e</mi></mtd><mtd><mi>f</mi></mtd></mtr>
<mtr><mtd><mi>g</mi></mtd><mtd><mi>h</mi></mtd></mtr></mtable><mo>|</mo></mrow>
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
        if False:
            # Proper spacing not yet implemented
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
</math>''', u'⠷⠚⠀⠨⠅⠀⠼⠂⠠⠀⠼⠆⠠⠀⠄⠄⠄⠠⠀⠰⠝⠾', page_width=lcg.USpace(40))
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mo>(</mo><mi>a</mi><mi>b</mi><mo>=</mo><mi>c</mi><mi>d</mi><mo>)</mo></mrow>
</math>''', u'⠷⠁⠃⠀⠨⠅⠀⠉⠙⠾')
        if False:
            # Not yet supported
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
<mrow><mo>&square;</mo><mo>+</mo><mo>&bigcirc;</mo><mo>=</mo><mo>&bigtriangleup;</mo></mrow>
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
</math>''', u'⠷⠤⠤⠤⠤⠠⠀⠲⠠⠀⠖⠠⠀⠦⠠⠀⠤⠤⠤⠤⠾', page_width=lcg.USpace(40))
        # §43
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mi>x</mi><mo>+</mo><mi>y</mi><mo>+</mo><mi>&hellip;</mi></mrow>
</math>''', u'⠭⠬⠽⠬⠀⠄⠄⠄⠸⠲', lang='en2', post='.')
        test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfenced open="" close="" separators=","><mn>1</mn><mn>3</mn><mn>5</mn><mo>&hellip;</mo>
<mn>15</mn></mfenced></mrow>
</math>''', u'⠼⠂⠠⠀⠼⠒⠠⠀⠼⠢⠠⠀⠄⠄⠄⠠⠀⠼⠂⠢⠸⠲', lang='en2', post='.', page_width=lcg.USpace(40))
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow>
<msup><msub><mi>p</mi><mn>1</mn></msub><msub><mi>&alpha;</mi><mn>1</mn></msub></msup>
<mo>&hellip;</mo>
<msup><msub><mi>p</mi><mi>r</mi></msub><msub><mi>&alpha;</mi><mi>r</mi></msub></msup>
</mrow>
</math>''', u'⠏⠂⠘⠨⠁⠘⠰⠂⠐⠄⠄⠄⠀⠏⠰⠗⠘⠨⠁⠘⠰⠗')
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
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mrow><mfrac><msup><mi>x</mi><mfrac><mn>1</mn><mn>2</mn></mfrac></msup><mn>2</mn></mfrac></mrow>
</math>''', u'⠹⠭⠘⠹⠂⠌⠆⠼⠆⠼') # fixed: there is an error in the specification example
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
        if False:
            # Not yet supported
            test(u'''<math display="inline" xmlns="http://www.w3.org/1998/Math/MathML">
<mfrac><mi>a</mi><msup><mi>b</mi>
<mfrac><mfrac><mn>3</mn><mn>4</mn></mfrac><mfrac><mn>5</mn><mn>6</mn></mfrac></mfrac></msup></mfrac>
</math>''', u'⠹⠁⠌⠃⠘⠠⠹⠹⠒⠌⠲⠼⠠⠌⠹⠢⠌⠖⠼⠠⠼⠐⠼')
            
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
            result = exported.split('\n\n')[1]
            assert result == expected_result, (("\n  - source text: %r\n  - expected:    %r\n  - "
                                                "got:         %r") %
                                               (mathml, expected_result, result,))
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

tests.add(BrailleExport)


class PDFExport(unittest.TestCase):

    def test_export(self):
        # Just test for crashes
        path = os.path.join(lcg_dir, 'doc/src')
        name = 'structured-text'
        reader = lcg.reader(path, name, ext='txt', recourse=False)
        node = reader.build()
        from lcg import pdf
        exporter = pdf.PDFExporter()
        context = exporter.context(node, 'cs')
        exporter.export(context)

tests.add(PDFExport)


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
                    assert value_1 == value_2, (attr, value_1, value_2,)

tests.add(Presentations)

        
def get_tests():
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='get_tests')
