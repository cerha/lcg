#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import unittest
import os
import string
import datetime
import lcg

_ = lcg.TranslatableTextFactory('test')

class TestSuite(unittest.TestSuite):
    def add(self, cls, prefix = 'test_'):
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
        c = c0.interpolate(lambda key: '-'+key+'-')
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
        assert str(b) == bx == 'Versi-n x-x',     (b, bx)
        assert str(c) == cx == 'Versi-n x-x-y-y', (c, cx)
        assert str(d) == dx == 'versi-n x-x-y-y', (d, dx)

    def test_transform(self):
        from xml.sax import saxutils
        a = _('His name is "%s"', _("Bob"))
        b = _("Bob") +' + '+ _("Joe")
        c = a.transform(saxutils.quoteattr)
        d = b.transform(saxutils.quoteattr)
        e = "attr=" + d # Test transformed Concatenation nesting!
        f = lcg.concat('<tag '+ e +'>')
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
        a3 = a2.interpolate(lambda key: '-'+key+'-')
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
            sign = offset/abs(offset)
            div, mod = divmod(abs(offset), 60)
            if mod:
                return "GMT %+d:%d" % (div*sign, mod)
            else:
                return "GMT %+d" % div*sign
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
        assert 'media.js' in br and 'sound1.ogg' in br and 'sound2.ogg' in br , br

tests.add(Resources)


class Parser(unittest.TestCase):

    def setUp(self):
        self._parser = lcg.Parser()
        
    def test_simple_text(self):
        text = "Hallo, how are you?\n\n  * one\n  * two\n  * three\n"
        c = self._parser.parse(text)
        assert len(c) == 2 and isinstance(c[0], lcg.Paragraph) and \
               isinstance(c[1], lcg.ItemizedList), c
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
        assert header.content()[0].content()[0].text() == 'hello', header.content()[0].content()[0].text()
        footer = parameters['page_footer']
        assert footer.content()[0].content()[0].text() == '@PAGE@', footer.content()[0].content()[0].text()
        assert footer.content()[0].halign() == lcg.HorizontalAlignment.CENTER, footer.content()[0].content().halign()

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
            assert c[0].halign() == None, c[0].content()[0].content()[0].halign()
            assert c[1].halign() == constant, c[0].content()[0].content()[0].halign()
            assert c[2].halign() == None, c[0].content()[0].content()[0].halign()

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
        assert all([isinstance (x, lcg.Table) for x in c]), c
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
                
tests.add(Parser)

class MacroParser(unittest.TestCase):

    def test_simple_condition(self):
        text = "@if x\nX\n@else\nY@endif\n"
        r = lcg.MacroParser(globals=dict(x=True)).parse(text)
        assert r == "X\n", repr(r)

    def test_condition(self):
        def check(contidion, expected_result, **globals):
            text = ("@if "+ contidion +"\nTrue\n@else\nFalse\n@endif")
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
            return "".join([line+"\n" for line in lines])
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


class HtmlExport(unittest.TestCase):
    
    def test_formatter(self):
        resources=(lcg.Media('xx.mp3'),
                   lcg.Image('aa.jpg'),
                   lcg.Image('bb.jpg'),
                   lcg.Image('cc.png', title="Image C", descr="Nice picture"))
        p = lcg.ResourceProvider(resources=resources)
        sec = lcg.Section("Section One", anchor='sec1', content=lcg.Content())
    	n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                            content=lcg.Container((sec,)), resource_provider=p)
        context = lcg.HtmlExporter().context(n, None)
        for text, html in (
            ('*x*',
             '<strong>x</strong>'),
            (' x ',
             ' x '),
            # Links
            ('[test]',
             '<a href="test" title="Some description">Test Node</a>'),
            ('[test#sec1]',
             '<a href="test#sec1">Section One</a>'),
            ('[#sec1]',
             '<a href="test#sec1">Section One</a>'),
            ('[http://www.freebsoft.org]',
             '<a href="http://www.freebsoft.org">http://www.freebsoft.org</a>'),
            ('[http://www.freebsoft.org Free(b)soft website]',
             '<a href="http://www.freebsoft.org">Free(b)soft website</a>'),
            ('[http://www.freebsoft.org label | descr]',
             '<a href="http://www.freebsoft.org" title="descr">label</a>'),
            ('[xx.mp3]',
             '<a href="media/xx.mp3">xx.mp3</a>'),
            # Absolute links
            ('https://www.freebsoft.org',
             '<a href="https://www.freebsoft.org">https://www.freebsoft.org</a>'),
            ('See http://www.freebsoft.org.',
             'See <a href="http://www.freebsoft.org">http://www.freebsoft.org</a>.'),
            ('(see http://www.freebsoft.org)',
             '(see <a href="http://www.freebsoft.org">http://www.freebsoft.org</a>)'),
            ('(see http://www.freebsoft.org).',
             '(see <a href="http://www.freebsoft.org">http://www.freebsoft.org</a>).'),
            # Inline images
            ('[aa.jpg]',
             '<img src="images/aa.jpg" alt="" border="0" class="aa">'),
            ('[aa.jpg label]',
             '<img src="images/aa.jpg" alt="label" border="0" class="aa">'),
            ('[aa.jpg:20x30 label]',
             '<img src="images/aa.jpg" alt="label" width="20" height="30" border="0" class="aa">'),
            ('[>aa.jpg]',
             '<img src="images/aa.jpg" alt="" align="right" border="0" class="aa">'),
            ('[<aa.jpg]',
             '<img src="images/aa.jpg" alt="" align="left" border="0" class="aa">'),
            ('[aa.jpg label | descr]',
             '<img src="images/aa.jpg" alt="label: descr" border="0" class="aa">'),
            ('[http://www.freebsoft.org/img/logo.gif Free(b)soft logo]',
             '<img src="http://www.freebsoft.org/img/logo.gif" alt="Free(b)soft logo" border="0" class="logo">'),
            ('[cc.png]',
             '<img src="images/cc.png" alt="Image C: Nice picture" border="0" class="cc">'),
            # Image links (links with an image instead of a label)
            ('[aa.jpg bb.jpg label | descr]',
             '<a href="images/aa.jpg" title="descr"><img src="images/bb.jpg" alt="label" border="0" class="bb"></a>'),
            ('[aa.jpg bb.jpg | descr]',
             '<a href="images/aa.jpg" title="descr"><img src="images/bb.jpg" alt="" border="0" class="bb"></a>'),
            ('[>aa.jpg bb.jpg label | descr]',
             '<a href="images/aa.jpg" title="descr"><img src="images/bb.jpg" alt="label" align="right" border="0" class="bb"></a>'),
            ('[test bb.jpg bb]',
             '<a href="test" title="Some description"><img src="images/bb.jpg" alt="bb" border="0" class="bb"></a>'),
            ('[http://www.freebsoft.org /img/logo.gif]',
             '<a href="http://www.freebsoft.org"><img src="/img/logo.gif" alt="" border="0" class="logo"></a>'),
            ('[http://www.freebsoft.org /img/logo.gif Free(b)soft website]',
             '<a href="http://www.freebsoft.org"><img src="/img/logo.gif" alt="Free(b)soft website" border="0" class="logo"></a>'),
            ('[http://www.freebsoft.org /img/logo.gif Free(b)soft website | Go to Free(b)soft website]',
             '<a href="http://www.freebsoft.org" title="Go to Free(b)soft website"><img src="/img/logo.gif" alt="Free(b)soft website" border="0" class="logo"></a>'),
            # Absolute image links
            ('http://www.freebsoft.org/img/logo.gif',
             '<img src="http://www.freebsoft.org/img/logo.gif" alt="" border="0" class="logo">'),
            # Escapes
            (r'\*one* \\*two* \\\*three* \\\\*four* \\\\\*five*',
             r'*one* \<strong>two</strong> \*three* \\<strong>four</strong> \\*five*'),
            # HTML special
            (r'<bla>',
             r'&lt;bla&gt;'),
            ):
            result = lcg.FormattedText(text).export(context)
            assert result == html, "\n  - source text: %r\n  - expected:    %r\n  - got:         %r" % \
                   (text, html, result)

    def test_export(self):
    	n = lcg.ContentNode('test', title='Test', content=lcg.Content(),
                            globals=dict(x='value of x'))
        context = lcg.HtmlExporter().context(n, None, sec_lang='es')
        for content, html in (
            (('a', ' ', lcg.strong('b ', lcg.em('c'), ' ', lcg.u('d')), ' ', lcg.code('e')),
             'a <strong>b <em>c</em> <u>d</u></strong> <code>e</code>'),
            (lcg.cite('x'),
             '<span lang="es" class="citation">x</span>'),
            (lcg.br(),
             '<br>'),
            (lcg.hr(),
             '<hr>'),
            (lcg.Substitution('x'),
             'value of x'),
            ):
            result = lcg.coerce(content).export(context)
            assert result == html, "\n  - content:  %r\n  - expected: %r\n  - got:      %r" % \
                (content, html, result)
            
tests.add(HtmlExport)


class BrailleExport(unittest.TestCase):
    
    def test_formatter(self):
        import imp
        presentation = lcg.Presentation()
        filename = os.path.join(lcg_dir, 'styles/presentation-braille-test.py')
        f = open(filename)
        confmodule = imp.load_module('_lcg_presentation', f, filename, ('.py', 'r', imp.PY_SOURCE))
        f.close()
        for o in dir(confmodule):
            if o[0] in string.lowercase and hasattr(presentation, o):
                setattr(presentation, o, confmodule.__dict__[o])
        page_height = presentation.page_height
        presentation_set = lcg.PresentationSet(((presentation, lcg.TopLevelMatcher(),),))
        def test(text, braille, header, footer, lang):
            #sec = lcg.Section("Section One", anchor='sec1', content=)
            n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                                content=lcg.Container((lcg.FormattedText(text),)))
            exporter = lcg.BrailleExporter()
            context = exporter.context(n, lang=lang, presentation=presentation_set)
            result = exporter.export(context)
            braille = header + braille
            n_lines = page_height.size() - len(braille.split('\n'))
            braille = braille + '\n' * n_lines + footer
            assert result == braille, \
                   ("\n  - source text: %r\n  - expected:    %r\n  - got:         %r" %
                    (text, braille, result,))
        for text, braille in (
            (u'abc', u'⠁⠃⠉',),
            (u'a a11a 1', u'⠁⠀⠁⠼⠁⠁⠐⠁⠀⠼⠁',),
            (u'*tučný*', u'⠔⠰⠞⠥⠩⠝⠯⠰⠔',),
            (u'/šikmý/', u'⠔⠨⠱⠊⠅⠍⠯⠨⠔',),
            (u'_podtržený_', u'⠸⠏⠕⠙⠞⠗⠮⠑⠝⠯',),
            (u'_hodně podtržený_', u'⠔⠸⠓⠕⠙⠝⠣⠀⠏⠕⠙⠞⠗⠮⠑⠝⠯⠸⠔',),
            ):
            result = test(text, braille, u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠼⠁⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑', 'cs')
        for text, braille in (
            (u'abc', u'⠁⠃⠉',),
            #(u'a a11a 1', u'⠁⠀⠁⠼⠁⠁⠐⠁⠀⠼⠁',), # buggy in current liblouis!
            (u'a line to be hyphenated', u'⠁⠀⠇⠊⠝⠑⠀⠞⠕⠀⠃⠑⠀⠓⠽⠏⠓⠑⠝⠤\n⠁⠞⠑⠙',),
            (u'*bold*', u'⠸⠃⠕⠇⠙',),
            (u'/italic/', u'⠨⠊⠞⠁⠇⠊⠉',),
            (u'_underlined_', u'⠥⠝⠙⠑⠗⠇⠊⠝⠑⠙',),
            ):
            result = test(text, braille, u'⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑\n\n', u'⠼⠁⠀⠠⠞⠑⠎⠞⠀⠠⠝⠕⠙⠑', 'en')

tests.add(BrailleExport)


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
