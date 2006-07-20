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

class TestSuite(unittest.TestSuite):
    def add(self, cls, prefix = 'check_'):
        tests = filter(lambda s: s[:len(prefix)] == prefix, dir(cls))
        self.addTest(unittest.TestSuite(map(cls, tests)))

tests = TestSuite()

class ContentNode(unittest.TestCase):
    def check_misc(self):
    	a = lcg.ContentNode(None, 'a', subdir='aaa')
        b = lcg.ContentNode(a, 'b', subdir='bbb')
        assert a.root() == b.root() == a
        assert a.src_dir() == 'aaa'
        assert b.src_dir() == os.path.join('aaa', 'bbb')
        assert b.id() != a.id()
        assert a.counter().next() == 1
        assert a.counter().next() == 2
        assert b.counter().next() == 1

    def check_media(self):
    	a = lcg.ContentNode(None, 'a', subdir='aaa')
        m1 = a.resource(lcg.Media, 'sound1.ogg')
        m2 = a.resource(lcg.Media, 'sound2.ogg')
        r = a.resources(lcg.Media)
        assert len(r) == 2 and m1 in r and m2 in r, r

tests.add(ContentNode)


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
