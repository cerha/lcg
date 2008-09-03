#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

class TranslatableText(unittest.TestCase):
          
    def check_interpolation(self):
        a = lcg.TranslatableText("Hi %s, say hello to %s.", "Joe", "Bob")
        b = lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.",
                                 person1="Joe", person2="Bob")
        c0 = lcg.TranslatableText("Hi %(person1)s, say hello to %(person2)s.")
        c = c0.interpolate(lambda key: '-'+key+'-')
        a1 = a.localize(lcg.NullTranslator())
        b1 = b.localize(lcg.NullTranslator())
        c1 = c.localize(lcg.NullTranslator())
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
        b = t.replace('o', '-')
        c = a.replace('o', '-')
        d = c.replace('V', 'v')
        assert isinstance(a, lcg.Concatenation), a
        assert isinstance(b, lcg.TranslatableText), b
        assert isinstance(c, lcg.Concatenation), c
        assert isinstance(d, lcg.Concatenation), d
        ax = a.localize(lcg.NullTranslator())
        bx = b.localize(lcg.NullTranslator())
        cx = c.localize(lcg.NullTranslator())
        dx = d.localize(lcg.NullTranslator())
        assert str(a) == ax == 'Version xox-yoy', (a, ax)
        assert str(b) == bx == 'Versi-n x-x',     (b, bx)
        assert str(c) == cx == 'Versi-n x-x-y-y', (c, cx)
        assert str(d) == dx == 'versi-n x-x-y-y', (d, dx)

    def check_transform(self):
        from xml.sax import saxutils
        a = _('His name is "%s"', _("Bob"))
        b = _("Bob") +' + '+ _("Joe")
        c = a.transform(saxutils.quoteattr)
        d = b.transform(saxutils.quoteattr)
        e = "attr=" + d # Test transformed Concatenation nesting!
        f = lcg.concat('<tag '+ e +'>')
        assert isinstance(c, lcg.TranslatableText), c
        assert isinstance(d, lcg.Concatenation), d
        t = lcg.GettextTranslator('cs')
        ax = a.localize(t)
        bx = b.localize(t)
        cx = c.localize(t)
        dx = d.localize(t)
        ex = e.localize(t)
        fx = f.localize(t)
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
        text = "%(person1)s is smarter than %(person2)s."
        translations = {'cs': u"%(person1)s je chytřejší než %(person2)s."}
        a = lcg.SelfTranslatableText(text, person1="Joe", person2="Ann", translations=translations)
        a2 = lcg.SelfTranslatableText(text, translations=translations)
        a3 = a2.interpolate(lambda key: '-'+key+'-')
        b = a.localize(lcg.NullTranslator())
        c = a.localize(lcg.GettextTranslator('cs'))
        assert b == "Joe is smarter than Ann.", b
        assert c == u"Joe je chytřejší než Ann.", c
        b2 = a3.localize(lcg.NullTranslator())
        c2 = a3.localize(lcg.GettextTranslator('cs'))
        assert b2 == "-person1- is smarter than -person2-.", b2
        assert c2 == u"-person1- je chytřejší než -person2-.", c2
        
tests.add(SelfTranslatableText)

class LocalizableDateTime(unittest.TestCase):

    def check_localize(self):
        d1 = lcg.LocalizableDateTime("2006-12-21")
        d2 = lcg.LocalizableDateTime("2006-12-21 02:43", show_time=False)
        d3 = lcg.LocalizableDateTime("2006-12-21 02:43")
        d4 = lcg.LocalizableDateTime("2006-12-21 18:43:32", show_weekday=True)
        d5 = lcg.LocalizableDateTime("2006-01-30", leading_zeros=False)
        t1 = lcg.GettextTranslator('en')
        x1 = d1.localize(t1)
        x2 = d2.localize(t1)
        x3 = d3.localize(t1)
        x4 = d4.localize(t1)
        x5 = d5.localize(t1)
        assert x1 == "12/21/2006", x1
        assert x2 == "12/21/2006", x2
        assert x3 == "12/21/2006 02:43 AM", x3
        assert x4 == "Thu 12/21/2006 06:43:32 PM", x4
        assert x5 == "1/30/2006", x5
        t2 = lcg.GettextTranslator('cs')
        y1 = d1.localize(t2)
        y2 = d2.localize(t2)
        y3 = d3.localize(t2)
        y4 = d4.localize(t2)
        y5 = d5.localize(t2)
        assert y1 == "21.12.2006", y1
        assert y2 == "21.12.2006", y2
        assert y3 == "21.12.2006 02:43", y3
        assert y4 == u"Čt 21.12.2006 18:43:32", y4
        assert y5 == "30.1.2006", y5
        
    def check_concat(self):
        d = lcg.LocalizableDateTime("2006-01-30")
        c = "Date is: " + d
        t = c.localize(lcg.GettextTranslator('en'))
        assert t == "Date is: 01/30/2006", t
        t = c.localize(lcg.GettextTranslator('cs'))
        assert t == "Date is: 30.01.2006", t

    def check_replace(self):
        a = lcg.LocalizableDateTime("2006-01-30")
        b = a.replace('-', '+')
        c = a.replace('/', '|')
        d = a.replace('.', ':')
        t1 = lcg.GettextTranslator('en')
        t2 = lcg.GettextTranslator('cs')
        b1 = b.localize(t1)
        b2 = b.localize(t2)
        assert str(b) == "2006+01+30", str(b)
        assert b1 == "01/30/2006", b1
        assert b2 == "30.01.2006", b2
        c1 = c.localize(t1)
        c2 = c.localize(t2)
        assert str(c) == "2006-01-30", str(c)
        assert c1 == "01|30|2006", c1
        assert c2 == "30.01.2006", c2
        d1 = d.localize(t1)
        d2 = d.localize(t2)
        assert str(d) == "2006-01-30", str(d)
        assert d1 == "01/30/2006", d1
        assert d2 == "30:01:2006", d2

tests.add(LocalizableDateTime)

class LocalizableTime(unittest.TestCase):

    def check_format(self):
        t1 = lcg.LocalizableTime("02:43")
        t2 = lcg.LocalizableTime("18:43:32")
        t1cs = t1.localize(lcg.GettextTranslator('cs'))
        t2cs = t2.localize(lcg.GettextTranslator('cs'))
        t1no = t1.localize(lcg.GettextTranslator('no'))
        t2no = t2.localize(lcg.GettextTranslator('no'))
        assert t1cs == "02:43", t1cs
        assert t2cs == "18:43:32", t2cs
        assert t1no == "02.43", t1no
        assert t2no == "18.43.32", t2no

tests.add(LocalizableTime)


class TranslatableTextFactory(unittest.TestCase):

    def check_domain(self):
        a = _("%(name1)s is smarter than %(name2)s.", name1=_("Joe"), name2=_("Bob"))
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
        a = _("%(name1)s is smarter than %(name2)s.", name1=_("Joe"), name2=_("Bob"))
        b = t.translate(a)
        assert b == u"Pepa je chytřejší než Bobik.", b
        c = a.localize(t)
        assert c == b, c

tests.add(GettextTranslator)


class ContentNode(unittest.TestCase):
    
    def check_misc(self):
        b = lcg.ContentNode('b', content=lcg.TextContent("B"))
    	a = lcg.ContentNode('a', content=lcg.TextContent("A"), children=(b,))
        assert a.id() == 'a'
        assert a.root() == b.root() == a

tests.add(ContentNode)


class Resources(unittest.TestCase):
    
    def check_provider(self):
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
        
    def check_dependencies(self):
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


class Export(unittest.TestCase):
    
    def check_formatter(self):
        resources=(lcg.Media('xx.mp3'),
                   lcg.Image('aa.jpg'),
                   lcg.Image('bb.jpg'),
                   lcg.Image('cc.png', title="Image C", descr="Nice picture"))
        p = lcg.ResourceProvider(resources=resources)
        content = lcg.SectionContainer((lcg.Section("Section One", anchor='sec1',
                                                    content=lcg.Content()),))
    	n = lcg.ContentNode('test', title='Test Node', descr="Some description",
                            content=content, resource_provider=p)
        context = lcg.HtmlExporter().context(n, None)
        for text, html in (
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
            # Inline images
            ('[aa.jpg]',
             '<img src="images/aa.jpg" alt="" border="0" class="aa">'),
            ('[aa.jpg label]',
             '<img src="images/aa.jpg" alt="label" border="0" class="aa">'),
            ('[>aa.jpg]',
             '<img src="images/aa.jpg" alt="" align="right" border="0" class="aa">'),
            ('[<aa.jpg]',
             '<img src="images/aa.jpg" alt="" align="left" border="0" class="aa">'),
            ('[aa.jpg label | descr]',
             '<img src="images/aa.jpg" alt="label" longdesc="descr" border="0" class="aa">'),
            ('[http://www.freebsoft.org/img/logo.gif Free(b)soft logo]',
             '<img src="http://www.freebsoft.org/img/logo.gif" alt="Free(b)soft logo" border="0" class="logo">'),
            ('[cc.png]',
             '<img src="images/cc.png" alt="Image C" longdesc="Nice picture" border="0" class="cc">'),
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
            ):
            result = lcg.FormattedText(text).export(context)
            assert result == html, "\n  * %s\n  - expected: %s\n  - got:      %s" % \
                   (text, html, result)
        
tests.add(Export)

        
def get_tests():
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='get_tests')
