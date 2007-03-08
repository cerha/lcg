# Author: Tomas Cerha <cerha@brailcom.org>
#
# Copyright (C) 2004, 2005, 2006, 2007 Brailcom, o.p.s.
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

"""Specific content elements for vocabulary lists in language courses."""

from lcg import *
from lcg.content import *

_ = TranslatableTextFactory('lcg-elearning')

class VocabItem(object):
    """One item of vocabulary listing."""

    ATTR_EXTENDED = 'ATTR_EXTENDED'
    """Special attribute indicating an extended vocabulary item."""
    ATTR_PHRASE = 'ATTR_PHRASE'
    """Special attribute indicating a phrase."""
    
    def __init__(self, media, word, note, translation, translation_language,
                 attr=None):
        """Initialize the instance.
        
        Arguments:
          word -- the actual piece of vocabulary as a string
          note -- notes in round brackets as a string.  Can contain multiple
            notes in brackets separated by spaces.  Typical notes are for
            example (v) for verb etc.
          translation -- the translation of the word into target language.
          translation_language -- the lowercase ISO 639-1 Alpha-2 language
            code.
          attr -- special attributte.  One of the classes ATTR_* constants or
            None.
          
        """
        assert isinstance(media, Media)
        assert isinstance(word, unicode)
        assert isinstance(note, unicode) or note is None
        assert isinstance(translation, unicode)
        assert isinstance(translation_language, str) and \
               len(translation_language) == 2
        assert attr in (None, self.ATTR_EXTENDED, self.ATTR_PHRASE)
        self._word = word
        self._note = note
        self._translation = translation
        self._translation_language = translation_language
        self._attr = attr
        self._media = media

    def word(self):
        return self._word

    def note(self):
        return self._note

    def media(self):
        return self._media

    def translation(self):
        return self._translation

    def translation_language(self):
        return self._translation_language

    def attr(self):
        return self._attr

        
class VocabList(Content):
    """Vocabulary listing consisting of multiple 'VocabItem' instances."""

    def __init__(self, items, reverse=False):
        """Initialize the instance.

        Arguments:

          items -- sequence of 'VocabItem' instances.
          reverse -- a boolean flag indicating, that the word pairs should be
            printed in reversed order - translation first.

        """
        super(VocabList, self).__init__()
        assert is_sequence_of(items, VocabItem)
        assert isinstance(reverse, bool)
        self._items = items
        self._reverse = reverse

    def export(self, exporter):
        g = exporter.generator()
        pairs = [(g.speaking_text(i.word(), i.media()) +
                  (i.note() and " "+i.note() or ""),
                  g.span(i.translation() or "???",
                         lang=i.translation_language()))
                 for i in self._items]
        if self._reverse:
            pairs = [(b, a) for a,b in pairs]
        t = [format('<table class="vocab-list" title="%s" summary="%s">',
                    _("Vocabulary Listing"),
                    _("The vocabulary is presented in a two-column table "
                      "with a term on the left and its translation on the "
                      "right in each row."))] + \
            [format('<tr><td scope="row">%s</td><td>%s</td></tr>', *pair)
             for pair in pairs] + \
            ["</table>\n"]
        return concat(t, separator='\n')

    
class VocabSection(Section):
    """Section of vocabulary listing.

    The section is automatically split into two subsections -- the Vocabulary
    and the Phrases.

    """
    def __init__(self, title, items, reverse=False):
        """Initialize the instance.

        Arguments:

          title -- The title of the section.
          items -- sequence of 'VocabItem' instances.
          reverse -- see the same constructor argument for `VocabList'.

        """
        assert isinstance(title, (str, unicode))
        assert is_sequence_of(items, VocabItem)
        assert isinstance(reverse, bool)
        subsections = [(t, i) for t, i in self._subsections(items) if i]
        if len(subsections) > 1:
            c = [Section(t, VocabList(i, reverse=reverse))
                 for t, i in subsections]
        else:
            c = VocabList(subsections[0][1])
        super(VocabSection, self).__init__(title, c)

    def _subsections(self, items):
        return ((_("Terms"),
                 [x for x in items if x.attr() is None]),
                (_("Phrases"),
                 [x for x in items if x.attr() is VocabItem.ATTR_PHRASE]),
                (_("Extended vocabulary"),
                 [x for x in items if x.attr() is VocabItem.ATTR_EXTENDED]))
    
        
class VocabIndexSection(VocabSection):
    def _subsections(self, items):
        return ((_("Terms"),
                 [x for x in items if x.attr() is not VocabItem.ATTR_PHRASE]),
                (_("Phrases"),
                 [x for x in items if x.attr() is VocabItem.ATTR_PHRASE]))

    

