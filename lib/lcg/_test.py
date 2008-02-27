#!/usr/bin/env python

# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007, 2008 Brailcom, o.p.s.
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
import lcg

_ = lcg.TranslatableTextFactory('test')


class TestSuite(unittest.TestSuite):
    
    def add(self, cls, prefix = 'check_'):
        tests = filter(lambda s: s[:len(prefix)] == prefix, dir(cls))
        self.addTest(unittest.TestSuite(map(cls, tests)))

tests = TestSuite()

class ContentNode(unittest.TestCase):
    
    def check_misc(self):
        b = lcg.ContentNode('b', content=lcg.TextContent("B"))
    	a = lcg.ContentNode('a', content=lcg.TextContent("A"), children=(b,))
        assert a.id() == 'a'
        assert a.root() == b.root() == a

    def check_media(self):
    	a = lcg.ContentNode('a', content=lcg.TextContent("A"))
        # TODO: This doesn.t work now.  Resources now only work with
        # file-based nodes.
        #m1 = a.resource(lcg.XMedia, 'sound1.ogg')
        #m2 = a.resource(lcg.XMedia, 'sound2.ogg')
        #r = a.resources(lcg.XMedia)
        #assert len(r) == 2 and m1 in r and m2 in r, r

tests.add(ContentNode)

class TranslatableText(unittest.TestCase):
          
    def check_interpolation(self):
        a = lcg.TranslatableText("Hi %s, say hello to %s.", "Joe", "Bob")
        b = lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.",
                                 person1="Joe", person2="Bob")
        c0 = lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.")
        c = c0.interpolate(lambda key: '-'+key+'-')
        a1 = a.translate(lcg.NullTranslator())
        b1 = b.translate(lcg.NullTranslator())
        c1 = c.translate(lcg.NullTranslator())
        assert a1 == "Hi Joe, say hello to Bob.", a1
        assert b1 == "Hi Joe, say hello to Bob.", b1
        assert c1 == "Hi -person1-, say hello to -person2-.", c1
        
    def check_addition(self):
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
        except TypeError, e:
            pass
        assert isinstance(e, TypeError), e
            
    def check_concat(self):
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
        
    def check_replace(self):
        t = lcg.TranslatableText("Version %s", "xox")
        a = t + '-yoy'
        b = a.replace('o', '-')
        c = b.replace('V', 'v')
        assert isinstance(a, lcg.Concatenation), a
        assert isinstance(b, lcg.Concatenation), b
        assert isinstance(c, lcg.Concatenation), c
        ax = a.translate(lcg.NullTranslator())
        bx = b.translate(lcg.NullTranslator())
        cx = c.translate(lcg.NullTranslator())
        assert ax == 'Version xox-yoy', ax
        assert bx == 'Versi-n x-x-y-y', bx
        assert cx == 'versi-n x-x-y-y', cx

    def check_string_context(self):
        a = lcg.TranslatableText("Version %s", "1.0")
        assert a == "Version 1.0"
        b = lcg.TranslatableText("Info: %s", a)
        assert b == "Info: Version 1.0"
        c = lcg.concat("Info:", lcg.concat(a, '2006-08-14', separator=', '),
                       ('Mon', '10:32'), separator=' ')
        assert c == "Info: Version 1.0, 2006-08-14 Mon 10:32", c

tests.add(TranslatableText)

class SelfTranslatableText(unittest.TestCase):
          
    def check_interpolation(self):
        text = "Hi %(person1)s, say hello to %(person2)s."
        translations = {'cs': "Ahoj %(person1)s, pozdravuj %(person2)s."}
        a = lcg.SelfTranslatableText(text, person1="Joe", person2="Ann", translations=translations)
        a2 = lcg.SelfTranslatableText(text, translations=translations)
        a3 = a2.interpolate(lambda key: '-'+key+'-')
        b = a.translate(lcg.NullTranslator())
        c = a.translate(lcg.GettextTranslator('cs'))
        assert b == "Hi Joe, say hello to Ann.", b
        assert c == "Ahoj Joe, pozdravuj Ann.", c
        b2 = a3.translate(lcg.NullTranslator())
        c2 = a3.translate(lcg.GettextTranslator('cs'))
        assert b2 == "Hi -person1-, say hello to -person2-.", b2
        assert c2 == "Ahoj -person1-, pozdravuj -person2-.", c2
        
tests.add(SelfTranslatableText)

class LocalizableDateTime(unittest.TestCase):

    def check_format(self):
        d1 = lcg.LocalizableDateTime("2006-12-21")
        d2 = lcg.LocalizableDateTime("2006-12-21 02:43", show_time=False)
        d3 = lcg.LocalizableDateTime("2006-12-21 02:43")
        d4 = lcg.LocalizableDateTime("2006-12-21 18:43:32", show_weekday=True)
        f = d1.format(lcg.GettextTranslator('cs').locale_data())
        assert f == "21.12.2006", f
        data = lcg.GettextTranslator('en').locale_data()
        f1 = d1.format(data)
        f2 = d2.format(data)
        f3 = d3.format(data)
        f4 = d4.format(data)
        assert f1 == "12/21/2006", f1
        assert f2 == "12/21/2006", f2
        assert f3 == "12/21/2006 02:43 AM", f3
        assert f4 == "Thu 12/21/2006 06:43:32 PM", f4
        
    def check_concat(self):
        d = lcg.LocalizableDateTime("2006-01-30")
        c = "Date is: " + d
        t = c.translate(lcg.GettextTranslator('en'))
        assert t == "Date is: 01/30/2006", t
        t = c.translate(lcg.GettextTranslator('cs'))
        assert t == "Date is: 30.01.2006", t

tests.add(LocalizableDateTime)

class TranslatableTextFactory(unittest.TestCase):

    def check_domain(self):
        a = _("Hi %(name1)s, say hello to %(name2)s.", name1=_("Joe"), name2=_("Bob"))
        assert a.domain() == 'test'

tests.add(TranslatableTextFactory)

class Monetary(unittest.TestCase):

    def check_format(self):
        a = lcg.Monetary(8975.5)
        a1 = lcg.Translator().translate(a)
        a2 = lcg.Translator('cs').translate(a)
        a3 = lcg.Translator('en').translate(a)
        assert a1 == '8975.50', a1
        assert a2 == u'8\xa0975,50', a2
        assert a3 == '8,975.50', a3
    
    def check_precision(self):
        a = lcg.Monetary(8975.5, precision=0)
        b = lcg.Monetary(8975.5, precision=3)
        a1 = lcg.Translator().translate(a)
        b1 = lcg.Translator().translate(b)
        assert a1 == '8976', a1
        assert b1 == '8975.500', b1
    
tests.add(Monetary)


class GettextTranslator(unittest.TestCase):

    def check_translate(self):
        t = lcg.GettextTranslator('cs')
        a = _("Hi %(name1)s, say hello to %(name2)s.", name1=_("Joe"), name2=_("Bob"))
        b = t.translate(a)
        assert b == "Ahoj Pepo, pozdravuj Bobika.", b
        c = a.translate(t)
        assert c == b, c

tests.add(GettextTranslator)


class HtmlExporter(unittest.TestCase):
    pass

tests.add(HtmlExporter)


class Parser(unittest.TestCase):
    SIMPLE_TEXT = "Hallo, how are you?\n\n  * one\n  * two\n  * three\n"
    SECTIONS = "= Main =\n== Sub1 ==\n== Sub2 ==\n=== SubSub1 ===\n== Sub3 =="
    
    def check_simple_text(self):
        p = lcg.Parser()
        c = p.parse(self.SIMPLE_TEXT)
        assert len(c) == 2 and isinstance(c[0], lcg.Paragraph) and \
               isinstance(c[1], lcg.ItemizedList), c

    def check_sections(self):
        p = lcg.Parser()
        c = p.parse(self.SECTIONS)
        assert len(c) == 1 and isinstance(c[0], lcg.Section), c
        s = c[0].sections(None)
        assert len(s) == 3 and isinstance(s[0], lcg.Section) and \
               len(s[0].sections(None)) == 0 and len(s[1].sections(None)) == 1 and \
               len(s[2].sections(None)) == 0, s
        
tests.add(Parser)

        


def get_tests():
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='get_tests')
