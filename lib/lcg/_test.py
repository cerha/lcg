#!/usr/bin/env python

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
    	a = lcg.ContentNode(None, 'a', content=lcg.TextContent("A"))
        b = lcg.ContentNode(a, 'b', content=lcg.TextContent("B"))
        assert a.id() == 'a'
        assert a.root() == b.root() == a

    def check_media(self):
    	a = lcg.ContentNode(None, 'a', content=lcg.TextContent("A"))
        # TODO: This doesn.t work now.  Resourcesa now only work with
        # file-based nodes.
        #m1 = a.resource(lcg.Media, 'sound1.ogg')
        #m2 = a.resource(lcg.Media, 'sound2.ogg')
        #r = a.resources(lcg.Media)
        #assert len(r) == 2 and m1 in r and m2 in r, r

tests.add(ContentNode)

class TranslatableText(unittest.TestCase):
          
    def check_interpolation(self):
        a = lcg.TranslatableText("Hi %s, say hello to %s.", "Joe", "Bob")
        b = lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.",
                                 person1="Joe", person2="Bob")
        c = a.translate(lcg.NullTranslator())
        d = b.translate(lcg.NullTranslator())
        assert c == "Hi Joe, say hello to Bob.", c
        assert d == "Hi Joe, say hello to Bob.", d
        
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


class TranslatableTextFactory(unittest.TestCase):

    def check_domain(self):
        a = _("Hi %s, say hello to %s.", _("Joe"), _("Bob"))
        assert a.domain() == 'test'

tests.add(TranslatableTextFactory)


class GettextTranslator(unittest.TestCase):

    def check_translate(self):
        t = lcg.GettextTranslator('cs')
        a = _("Hi %s, say hello to %s.", _("Joe"), _("Bob"))
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
        s = c[0].sections()
        assert len(s) == 3 and isinstance(s[0], lcg.Section) and \
               len(s[0].sections()) == 0 and len(s[1].sections()) == 1 and \
               len(s[2].sections()) == 0, s
        
tests.add(Parser)

        
class SplittableText(unittest.TestCase):
    def check_it(self):
        import lcg.feed
        def check(matcher, lines):
            piece = lcg.SplittableText("\n".join(lines))
            for p in piece.split(matcher):
                a = p.text().splitlines()[0] # first line of this part's text
                b = lines[p.firstline()-1] # the line from the source sequence
                assert a == b, (a, b)
        check(lcg.feed.ExerciseFeeder._EXERCISE_SPLITTER,
              ("bla"," ", "----","",
               "ehm","","","","","----","",
               "\t", "xxx","yyy", ""))
        check(lcg.feed.ExerciseFeeder._BLANK_LINE_SPLITTER,
              ("", "bla","", "", "\t \t","",
               "ehm"," ",
               "xxx","yyy", "\t"))
        
tests.add(SplittableText)


def get_tests():
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='get_tests')
